"""Talabaning topshirig'i (I3-04; AGR-01, AGR-05, LAB-07).

`GET /api/labs/{mavzu}/assignment` — shart (variant parametrlari bilan), qadamlar va faqat
ko'rinadigan testlar. Yashirin testlar so'rovga umuman kirmaydi (AGR-05). Variant birinchi
ochilishda beriladi (`variants.assign`) va keyin o'zgarmaydi (AGR-08).
Laboratoriya yopiq bo'lsa — 403 `lab_closed` (variant ham berilmaydi).
"""

from __future__ import annotations

import string
from typing import Any

from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudent
from apps.courses.models import Topic
from apps.grading import service, variants
from apps.grading.models import (
    Assignment,
    AssignmentStep,
    Submission,
    SubmissionPolicy,
    TestFile,
    TestKind,
)
from apps.grading.models import SubmissionStatus as SubmissionState
from apps.labs.views import _student_context
from apps.sections.models import Section
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
            }
        )


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
}
SubmissionOut = inline_serializer("SubmissionOut", _SUBMISSION_FIELDS)
SubmissionListOut = inline_serializer(
    "SubmissionListOut",
    {"submissions": inline_serializer("SubmissionItem", _SUBMISSION_FIELDS, many=True)},
)


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
        rows = Submission.objects.filter(
            student_assignment__student=student, student_assignment__assignment=assignment
        ).order_by("-created_at")[:20]
        return Response({"submissions": [_out(s) for s in rows]})

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

    @extend_schema(responses={200: SubmissionOut}, summary="Urinish holati")
    def get(self, request: Request, submission_id: int) -> Response:
        submission = Submission.objects.filter(
            pk=submission_id, student_assignment__student_id=request.user.pk
        ).first()
        if submission is None:
            raise NotFound
        return Response(_out(submission))
