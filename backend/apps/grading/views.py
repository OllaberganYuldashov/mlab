"""Talabaning topshirig'i (I3-04; AGR-01, AGR-05, LAB-07).

`GET /api/labs/{mavzu}/assignment` — shart (variant parametrlari bilan), qadamlar va faqat
ko'rinadigan testlar. Yashirin testlar so'rovga umuman kirmaydi (AGR-05). Variant birinchi
ochilishda beriladi (`variants.assign`) va keyin o'zgarmaydi (AGR-08).
Laboratoriya yopiq bo'lsa — 403 `lab_closed` (variant ham berilmaydi).
"""

from __future__ import annotations

import string
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsStudent
from apps.courses.models import Topic
from apps.grading import results, service, variants
from apps.grading.models import (
    Assignment,
    AssignmentStep,
    Level,
    LevelSource,
    StudentAssignment,
    Submission,
    SubmissionPolicy,
    TestFile,
    TestKind,
    Understanding,
)
from apps.grading.models import SubmissionStatus as SubmissionState
from apps.labs.views import _student_context
from apps.sections.member_views import STAFF_OR_INSTRUCTOR, _visible_section_id
from apps.sections.models import Membership, Section
from apps.sections.policy import SubmissionStatus, submission_policy
from apps.sections.settings import effective_settings


class AssignmentStepOut(serializers.Serializer[dict[str, Any]]):
    key = serializers.CharField()
    title = serializers.CharField()
    points = serializers.IntegerField()
    visible_test = serializers.CharField(allow_null=True)


AssignmentOut = inline_serializer(
    "MyAssignmentOut",
    {
        "code": serializers.CharField(),
        "title": serializers.CharField(),
        "level": serializers.CharField(),
        "statement": serializers.CharField(),
        "params": serializers.JSONField(),
        "steps": AssignmentStepOut(many=True),
        "has_challenge": serializers.BooleanField(),
        "challenge": serializers.CharField(allow_null=True),
    },
)


def render_statement(template: str, params: dict[str, Any]) -> str:
    """`{nom}` o'rniga parametr qiymati. `{a.b}`, `{a[0]}`, `{a:fmt}` — o'zgarishsiz matn.

    `str.format` ishlatilmaydi: u atributlarga kirishga yo'l qo'yadi (`{x.__class__}`).
    Noma'lum maydon ham o'zgarishsiz qoladi; `{{` va `}}` — oddiy qavs.
    """
    out: list[str] = []
    for literal, field, spec, conversion in string.Formatter().parse(template):
        out.append(literal)
        if field is None:
            continue
        if field in params and not spec and conversion is None:
            out.append(str(params[field]))
        else:
            suffix = (f"!{conversion}" if conversion else "") + (f":{spec}" if spec else "")
            out.append("{" + field + suffix + "}")
    return "".join(out)


def _topic_assignment(section: Section, topic: Topic) -> Assignment | None:
    return (
        Assignment.objects.filter(course_id=section.course_id, topic_code=topic.code)
        .order_by("code")
        .first()
    )


def _no_assignment() -> Response:
    return Response(
        {"code": "no_assignment", "detail": "Bu mavzuda topshiriq yo'q."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _lab_closed() -> Response:
    return Response(
        {"code": "lab_closed", "detail": "Laboratoriya yopiq."},
        status=status.HTTP_403_FORBIDDEN,
    )


class MyAssignmentView(APIView):
    permission_classes = (IsStudent,)

    @extend_schema(responses={200: AssignmentOut}, summary="Mening topshirig'im (shart va testlar)")
    def get(self, request: Request, code: str) -> Response:
        student, section, topic = _student_context(request.user, code)
        if submission_policy(section, topic, timezone.now()) == SubmissionStatus.CLOSED:
            return _lab_closed()
        assignment = _topic_assignment(section, topic)
        if assignment is None:
            return _no_assignment()
        record = variants.assign(student, assignment)
        params = record.variant.params
        steps = AssignmentStep.objects.filter(assignment=assignment).prefetch_related(
            Prefetch(
                "tests",
                queryset=TestFile.objects.filter(kind=TestKind.VISIBLE),
                to_attr="visible",
            )
        )
        return Response(
            {
                "code": assignment.code,
                "title": assignment.title,
                "level": record.level,
                "statement": render_statement(assignment.statement, params),
                "params": params,
                "steps": [
                    {
                        "key": s.key,
                        "title": s.title,
                        "points": s.points,
                        "visible_test": s.visible[0].source if s.visible else None,
                    }
                    for s in steps
                ],
                # ADP-03: challenge faqat to'liq ball (o'z vaqtida) olingandan keyin ochiladi.
                "has_challenge": bool(assignment.challenge),
                "challenge": assignment.challenge
                if challenge_unlocked(record, assignment)
                else None,
            }
        )


def challenge_unlocked(record: StudentAssignment, assignment: Assignment) -> bool:
    """ADP-03: oyna ichida (o'z vaqtida, rasmiy) 100 ball olingan urinish bor; keyin ochiq qoladi.

    Challenge bali asosiy ballga ta'sir qilmaydi (GRD-01): u alohida, R1 da o'qituvchi ko'radi.
    """
    if not assignment.challenge:
        return False
    return Submission.objects.filter(
        student_assignment=record,
        status=SubmissionState.DONE,
        policy=SubmissionPolicy.ON_TIME,
        final_score__gte=100,
        understanding__in=[Understanding.NONE, Understanding.PASSED],
    ).exists()


# --- Topshirish (I3-07; AGR-02, AGR-04, ACC-06, ACC-07) ---

MAX_CODE = 200_000  # belgi: notebook kodi (runner kirishi 2 MB gacha — testlar bilan)

_POLICY = {
    SubmissionStatus.ON_TIME: SubmissionPolicy.ON_TIME,
    SubmissionStatus.LATE: SubmissionPolicy.LATE,
    SubmissionStatus.PRACTICE: SubmissionPolicy.PRACTICE,
}


class LabSubmitThrottle(SimpleRateThrottle):
    """Talaba bo'yicha (bir sinf bitta NAT ortida). Navbatni bitta talaba to'ldirib qo'ymasin."""

    scope = "lab-submit"

    def get_rate(self) -> str:
        return str(settings.LAB_SUBMIT_RATE)

    def allow_request(self, request: Request, view: APIView) -> bool:
        return request.method != "POST" or super().allow_request(request, view)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.pk)}


class _SubmitIn(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField(max_length=MAX_CODE, allow_blank=False, trim_whitespace=False)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        # CharField sonni satrga aylantiradi — kod faqat JSON satr bo'lsin.
        if isinstance(data, dict) and "code" in data and not isinstance(data["code"], str):
            raise serializers.ValidationError({"code": ["Kod satr bo'lishi kerak."]})
        value: dict[str, Any] = super().to_internal_value(data)
        return value


_SUBMISSION_FIELDS: dict[str, serializers.Field[Any, Any, Any, Any]] = {
    "id": serializers.IntegerField(),
    "status": serializers.ChoiceField(choices=SubmissionState.values),
    "position": serializers.IntegerField(),
    "policy": serializers.ChoiceField(choices=SubmissionPolicy.values),
    "score": serializers.IntegerField(allow_null=True),
    "final_score": serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True),
    "created_at": serializers.DateTimeField(),
    "finished_at": serializers.DateTimeField(allow_null=True),
    "understanding": serializers.ChoiceField(choices=Understanding.values),
}
SubmissionOut = inline_serializer("SubmissionOut", _SUBMISSION_FIELDS)
_TEST_FIELDS: dict[str, serializers.Field[Any, Any, Any, Any]] = {
    "name": serializers.CharField(),
    "visible": serializers.BooleanField(),
    "passed": serializers.BooleanField(),
    "message": serializers.CharField(),
}
_STEP_FIELDS: dict[str, serializers.Field[Any, Any, Any, Any]] = {
    "key": serializers.CharField(),
    "title": serializers.CharField(),
    "points": serializers.IntegerField(),
    "score": serializers.IntegerField(),
    "passed": serializers.IntegerField(),
    "total": serializers.IntegerField(),
    "tests": inline_serializer("ResultTest", _TEST_FIELDS, many=True),
}
ResultOut = inline_serializer(
    "SubmissionResult",
    {
        "code_error": serializers.CharField(allow_null=True),
        "steps": inline_serializer("ResultStep", _STEP_FIELDS, many=True),
    },
    allow_null=True,
)
_QUESTION_FIELDS: dict[str, serializers.Field[Any, Any, Any, Any]] = {
    "text": serializers.CharField(),
    "options": serializers.ListField(child=serializers.CharField()),
}
SubmissionDetailOut = inline_serializer(
    "SubmissionDetailOut",
    {
        **_SUBMISSION_FIELDS,
        "result": ResultOut,
        "questions": inline_serializer(
            "PendingQuestion", _QUESTION_FIELDS, many=True, allow_null=True
        ),
    },
)
_BEST = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
SubmissionListOut = inline_serializer(
    "SubmissionListOut",
    {
        "best_final_score": _BEST,
        "submissions": inline_serializer("SubmissionItem", _SUBMISSION_FIELDS, many=True),
    },
)
StudentSubmissionsOut = inline_serializer(
    "StudentSubmissionsOut",
    {
        "best_final_score": _BEST,
        "submissions": inline_serializer(
            "StudentSubmissionItem",
            {
                **_SUBMISSION_FIELDS,
                "code": serializers.CharField(),
                "result": ResultOut,
                "understanding_detail": inline_serializer(
                    "UnderstandingDetail",
                    {
                        **_QUESTION_FIELDS,
                        "answer": serializers.IntegerField(),
                        "chosen": serializers.IntegerField(allow_null=True),
                    },
                    many=True,
                    allow_null=True,
                ),
            },
            many=True,
        ),
    },
)


def _steps(assignment_id: int) -> list[tuple[str, str, int]]:
    return list(
        AssignmentStep.objects.filter(assignment_id=assignment_id)
        .order_by("order")
        .values_list("key", "title", "points")
    )


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _out(submission: Submission) -> dict[str, Any]:
    return {
        **service.status_payload(submission),
        "created_at": submission.created_at,
        "finished_at": submission.finished_at,
    }


class MySubmissionsView(APIView):
    permission_classes = (IsStudent,)
    parser_classes = (JSONParser,)
    throttle_classes = (LabSubmitThrottle,)

    @extend_schema(responses={200: SubmissionListOut}, summary="Mening urinishlarim (oxirgi 20)")
    def get(self, request: Request, code: str) -> Response:
        student, section, topic = _student_context(request.user, code)
        assignment = _topic_assignment(section, topic)
        if assignment is None:
            return _no_assignment()
        record = StudentAssignment.objects.filter(student=student, assignment=assignment).first()
        rows = (
            Submission.objects.filter(student_assignment=record).order_by("-created_at")[:20]
            if record
            else []
        )
        return Response(
            {
                "best_final_score": _decimal(results.best_score(record)),
                "submissions": [_out(s) for s in rows],
            }
        )

    @extend_schema(
        request=_SubmitIn,
        responses={202: SubmissionOut},
        summary="Topshirish: kod navbatga qo'yiladi (yashirin testlar sandbox'da)",
    )
    def post(self, request: Request, code: str) -> Response:
        student, section, topic = _student_context(request.user, code)
        data = _SubmitIn(data=request.data)
        data.is_valid(raise_exception=True)
        policy = submission_policy(section, topic, timezone.now())
        if policy == SubmissionStatus.CLOSED:
            return _lab_closed()
        assignment = _topic_assignment(section, topic)
        if assignment is None:
            return _no_assignment()
        record = variants.assign(student, assignment)
        try:
            submission = service.enqueue(
                record,
                data.validated_data["code"],
                policy=_POLICY[policy],
                penalty_percent=effective_settings(section).late_penalty_percent,
            )
        except service.SubmissionPending:
            return Response(
                {"code": "submission_pending", "detail": "Oldingi urinish hali tekshirilmoqda."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(_out(submission), status=status.HTTP_202_ACCEPTED)


class MySubmissionView(APIView):
    """Qayta ulanishda holat (AGR-04). Begona urinish — 404 (mavjudligi ham oshkor emas)."""

    permission_classes = (IsStudent,)

    @extend_schema(
        responses={200: SubmissionDetailOut}, summary="Urinish holati va natijasi (AGR-05)"
    )
    def get(self, request: Request, submission_id: int) -> Response:
        submission = (
            Submission.objects.filter(
                pk=submission_id, student_assignment__student_id=request.user.pk
            )
            .select_related("student_assignment__variant")
            .first()
        )
        if submission is None:
            raise NotFound
        steps = _steps(submission.student_assignment.assignment_id)
        return Response(
            {
                **_out(submission),
                "result": results.student_result(submission, steps),
                "questions": _pending_questions(submission),
            }
        )


def _pending_questions(submission: Submission) -> list[dict[str, Any]] | None:
    """INT-02: javob kutilayotgan savollar — matn va variantlar, to'g'ri javobsiz."""
    if submission.understanding != Understanding.PENDING:
        return None
    pool = submission.student_assignment.variant.questions
    return [
        {"text": pool[i]["text"], "options": pool[i]["options"]} for i in submission.questions or []
    ]


class _AnswersIn(serializers.Serializer[dict[str, Any]]):
    answers = serializers.ListField(child=serializers.IntegerField(min_value=0), max_length=10)


class SubmissionAnswersView(APIView):
    """INT-02: tushunish savollariga javob (bir marta); noto'g'ri bo'lsa ball 50 gacha."""

    permission_classes = (IsStudent,)
    parser_classes = (JSONParser,)

    @extend_schema(
        request=_AnswersIn, responses={200: SubmissionOut}, summary="Tushunish savollariga javob"
    )
    def post(self, request: Request, submission_id: int) -> Response:
        data = _AnswersIn(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            submission = service.answer(
                submission_id, int(request.user.pk or 0), data.validated_data["answers"]
            )
        except Submission.DoesNotExist as exc:
            raise NotFound from exc
        except service.NotAwaitingAnswers:
            return Response(
                {"code": "not_awaiting_answers", "detail": "Bu urinishga javob kutilmayapti."},
                status=status.HTTP_409_CONFLICT,
            )
        except ValueError:
            raise ValidationError({"answers": ["Har savolga bitta variant tanlang."]}) from None
        return Response(_out(submission))


def _understanding_detail(
    submission: Submission, record: StudentAssignment | None
) -> list[dict[str, Any]] | None:
    """O'qituvchiga: berilgan savollar, to'g'ri javob va talaba javobi (INT-02)."""
    if record is None or not submission.questions:
        return None
    pool = record.variant.questions
    answers = submission.answers or []
    return [
        {
            "text": pool[i]["text"],
            "options": pool[i]["options"],
            "answer": pool[i]["answer"],
            "chosen": answers[k] if k < len(answers) else None,
        }
        for k, i in enumerate(submission.questions)
        if i < len(pool)
    ]


def _section_student(
    user: Any, section_id: int, code: str, student_id: int
) -> tuple[Membership, Assignment]:
    """O'qituvchining o'z guruhidagi tasdiqlangan talaba va mavzu topshirig'i; aks holda 404."""
    _visible_section_id(user, section_id)
    membership = (
        Membership.objects.approved()
        .filter(section_id=section_id, student_id=student_id)
        .select_related("section", "student")
        .first()
    )
    topic = (
        Topic.objects.filter(course_id=membership.section.course_id, code=code).first()
        if membership
        else None
    )
    assignment = _topic_assignment(membership.section, topic) if membership and topic else None
    if membership is None or assignment is None:
        raise NotFound
    return membership, assignment


class StudentSubmissionsView(APIView):
    """O'qituvchi: o'z guruhidagi talabaning urinishlari, kodi va natijasi (AGR-06).

    Begona guruh yoki guruhda tasdiqlanmagan talaba — 404. Yashirin testlar bu yerda ham yashirin.
    """

    permission_classes = STAFF_OR_INSTRUCTOR

    @extend_schema(
        responses={200: StudentSubmissionsOut}, summary="Talabaning urinishlari (o'qituvchiga)"
    )
    def get(self, request: Request, section_id: int, code: str, student_id: int) -> Response:
        _, assignment = _section_student(request.user, section_id, code, student_id)
        record = (
            StudentAssignment.objects.filter(student_id=student_id, assignment=assignment)
            .select_related("variant")
            .first()
        )
        steps = _steps(assignment.pk)
        rows = (
            Submission.objects.filter(student_assignment=record).order_by("-created_at")[:50]
            if record
            else []
        )
        return Response(
            {
                "best_final_score": _decimal(results.best_score(record)),
                "submissions": [
                    {
                        **_out(s),
                        "code": s.code,
                        "result": results.student_result(s, steps),
                        "understanding_detail": _understanding_detail(s, record),
                    }
                    for s in rows
                ],
            }
        )


class _LevelIn(serializers.Serializer[dict[str, Any]]):
    level = serializers.ChoiceField(choices=Level.values)


LevelOut = inline_serializer(
    "StudentLevelOut",
    {
        "level": serializers.ChoiceField(choices=Level.values),
        "level_source": serializers.ChoiceField(choices=LevelSource.values),
        "changed": serializers.BooleanField(),
    },
)


class StudentLevelView(APIView):
    """ADP-02: o'qituvchi o'z guruhidagi talabaning topshiriq darajasini o'zgartiradi (audit bilan).

    Yangi daraja — yangi variant. Ochiq urinish bo'lsa 409 `submission_pending`.
    """

    permission_classes = STAFF_OR_INSTRUCTOR
    parser_classes = (JSONParser,)

    @extend_schema(
        request=_LevelIn, responses={200: LevelOut}, summary="Talaba darajasini o'zgartirish"
    )
    def put(self, request: Request, section_id: int, code: str, student_id: int) -> Response:
        membership, assignment = _section_student(request.user, section_id, code, student_id)
        data = _LevelIn(data=request.data)
        data.is_valid(raise_exception=True)
        assert isinstance(request.user, User)  # STAFF_OR_INSTRUCTOR kafolatlaydi  # noqa: S101
        try:
            record, changed = variants.set_level(
                membership.student, assignment, data.validated_data["level"], request.user
            )
        except variants.LevelLocked:
            return Response(
                {
                    "code": "submission_pending",
                    "detail": "Talabaning urinishi tekshirilmoqda — keyinroq o'zgartiring.",
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {"level": record.level, "level_source": record.level_source, "changed": changed}
        )
