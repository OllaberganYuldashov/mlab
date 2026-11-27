"""Laboratoriya ishi API (I2-16; LAB-05, ACC-06).

Talaba: `GET/PUT /api/labs/{code}/work` — faqat tasdiqlangan guruhi va o'z ishi. Saqlash faqat
`submission_policy` yopiq bo'lmaganda (oyna ochiq, kechikish yoki mashq rejimi);
yopiq — 403 `lab_closed`.
Optimistik qulf: mijoz o'zi ko'rgan `version` ni yuboradi; eskirgan bo'lsa 409 va serverdagi holat.
Bir xil saqlashni qayta yuborish (javob yo'qolgan) — o'sha natija (idempotent).
INT-01: `GET work` paste qoidalarini ham beradi (`paste_limit`, `proctored`);
`POST /api/labs/{code}/events` — har paste qaydi (faqat hajm va katak, matn emas). Rad etilganmi —
server o'zi hal qiladi (mijozga ishonilmaydi).
INT-05: `kind: tab_hidden` — sahifa yashirildi; faqat nazorat rejimida yoziladi (`recorded`).
O'qituvchi: `GET /api/sections/{id}/labs/{code}/works/{student_id}` — faqat o'z guruhi
(begona — 404).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsStudent
from apps.courses.models import Topic
from apps.labs.models import LabEvent, LabEventKind, LabWork
from apps.labs.notebook import NotebookError, validate_notebook
from apps.sections.member_views import STAFF_OR_INSTRUCTOR, _visible_section_id
from apps.sections.models import AccessWindow, Membership, Section
from apps.sections.policy import SubmissionStatus, submission_policy

# Bufer hajmi juda katta bo'lsa ham son sifatida yoziladi; undan kattasi — yolg'on qiymat.
MAX_PASTE_SIZE = 10_000_000


class LabSaveThrottle(SimpleRateThrottle):
    """Avtosaqlash — talaba bo'yicha (bir sinf bitta NAT ortida bo'lgani uchun IP emas)."""

    scope = "lab-save"

    def get_rate(self) -> str:
        return str(settings.LAB_SAVE_RATE)

    def allow_request(self, request: Request, view: APIView) -> bool:
        return request.method != "PUT" or super().allow_request(request, view)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.pk)}


class LabEventThrottle(LabSaveThrottle):
    scope = "lab-event"

    def get_rate(self) -> str:
        return str(settings.LAB_EVENT_RATE)

    def allow_request(self, request: Request, view: APIView) -> bool:
        return SimpleRateThrottle.allow_request(self, request, view)


WorkOut = inline_serializer(
    "LabWorkOut",
    {
        "version": serializers.IntegerField(),
        "notebook": serializers.JSONField(allow_null=True),
        "saved_at": serializers.DateTimeField(allow_null=True),
        "policy": serializers.ChoiceField(choices=[s.value for s in SubmissionStatus]),
        "paste_limit": serializers.IntegerField(),
        "proctored": serializers.BooleanField(),
    },
)
EventOut = inline_serializer(
    "LabEventOut", {"blocked": serializers.BooleanField(), "recorded": serializers.BooleanField()}
)


class _EventIn(serializers.Serializer[dict[str, Any]]):
    kind = serializers.ChoiceField(choices=["paste", "tab_hidden"])
    size = serializers.IntegerField(min_value=0, max_value=MAX_PASTE_SIZE, required=False)
    cell = serializers.RegexField(r"^[A-Za-z0-9_-]{1,64}\Z", required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["kind"] == "paste":
            missing = {f: "Paste uchun majburiy." for f in ("size", "cell") if f not in attrs}
            if missing:
                raise ValidationError(missing)
        return attrs


def paste_rules(section: Section, topic: Topic) -> tuple[int, bool]:
    """INT-01, ACC-09: (chegara, nazorat rejimi). Nazorat rejimida paste umuman taqiq."""
    window = AccessWindow.objects.filter(section=section, topic=topic).only("proctored").first()
    return section.course.paste_limit, bool(window and window.proctored)


SaveOut = inline_serializer(
    "LabSaveOut",
    {
        "version": serializers.IntegerField(),
        "saved_at": serializers.DateTimeField(),
        "policy": serializers.ChoiceField(choices=[s.value for s in SubmissionStatus]),
    },
)
SaveIn = inline_serializer(
    "LabSaveIn",
    {"version": serializers.IntegerField(min_value=0), "notebook": serializers.JSONField()},
)


def _student_context(user: Any, code: str) -> tuple[User, Section, Topic]:
    assert isinstance(user, User)  # IsStudent kafolatlaydi  # noqa: S101
    membership = (
        Membership.objects.approved().filter(student=user).select_related("section__course").first()
    )
    if membership is None:
        raise PermissionDenied("Siz hali tasdiqlangan guruh a'zosi emassiz.")
    topic = Topic.objects.filter(course_id=membership.section.course_id, code=code).first()
    if topic is None:
        raise NotFound
    return user, membership.section, topic


def _work_payload(
    work: LabWork | None, policy: SubmissionStatus, section: Section, topic: Topic
) -> dict[str, Any]:
    limit, proctored = paste_rules(section, topic)
    return {
        "version": work.version if work else 0,
        "notebook": work.notebook if work else None,
        "saved_at": work.saved_at if work else None,
        "policy": policy.value,
        "paste_limit": limit,
        "proctored": proctored,
    }


def _conflict(work: LabWork | None) -> Response:
    return Response(
        {
            "code": "version_conflict",
            "detail": "Ish boshqa oynada yangilangan.",
            "current_version": work.version if work else 0,
            "notebook": work.notebook if work else None,
        },
        status=status.HTTP_409_CONFLICT,
    )


class MyLabWorkView(APIView):
    permission_classes = (IsStudent,)
    parser_classes = (JSONParser,)
    throttle_classes = (LabSaveThrottle,)

    @extend_schema(responses={200: WorkOut}, summary="Mening laboratoriya ishim")
    def get(self, request: Request, code: str) -> Response:
        student, section, topic = _student_context(request.user, code)
        work = LabWork.objects.filter(student=student, section=section, topic=topic).first()
        policy = submission_policy(section, topic, timezone.now())
        return Response(_work_payload(work, policy, section, topic))

    @extend_schema(
        request=SaveIn,
        responses={200: SaveOut},
        summary="Avtosaqlash (optimistik versiya bilan)",
    )
    def put(self, request: Request, code: str) -> Response:
        student, section, topic = _student_context(request.user, code)
        data = request.data if isinstance(request.data, dict) else {}
        version = data.get("version")
        if type(version) is not int or version < 0:
            raise ValidationError({"version": ["0 yoki musbat butun son"]})
        try:
            notebook = validate_notebook(data.get("notebook"))
        except NotebookError as exc:
            raise ValidationError({"notebook": [str(exc)]}) from exc
        policy = submission_policy(section, topic, timezone.now())
        if policy == SubmissionStatus.CLOSED:
            return Response(
                {"code": "lab_closed", "detail": "Laboratoriya yopiq — saqlab bo'lmaydi."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            with transaction.atomic():
                work = (
                    LabWork.objects.select_for_update()
                    .filter(student=student, section=section, topic=topic)
                    .first()
                )
                if work is None:
                    if version != 0:
                        return _conflict(None)
                    work = LabWork.objects.create(
                        student=student, section=section, topic=topic, notebook=notebook
                    )
                elif version == work.version:
                    work.notebook = notebook
                    work.version += 1
                    work.save(update_fields=["notebook", "version", "saved_at"])
                elif not (version == work.version - 1 and notebook == work.notebook):
                    return _conflict(work)
                # aks holda: o'sha saqlashning takrori — o'zgarishsiz o'sha javob
        except IntegrityError:  # ikki tab bir vaqtda birinchi marta saqladi
            return _conflict(
                LabWork.objects.filter(student=student, section=section, topic=topic).first()
            )
        return Response(
            {"version": work.version, "saved_at": work.saved_at, "policy": policy.value}
        )


class StudentLabWorkView(APIView):
    permission_classes = STAFF_OR_INSTRUCTOR

    @extend_schema(responses={200: WorkOut}, summary="Talabaning laboratoriya ishi (o'qituvchiga)")
    def get(self, request: Request, section_id: int, code: str, student_id: int) -> Response:
        _visible_section_id(request.user, section_id)
        work = (
            LabWork.objects.filter(section_id=section_id, topic__code=code, student_id=student_id)
            .select_related("section__course", "topic")
            .first()
        )
        if work is None:
            raise NotFound
        policy = submission_policy(work.section, work.topic, timezone.now())
        return Response(_work_payload(work, policy, work.section, work.topic))


class MyLabEventView(APIView):
    """INT-01: paste qaydi. Rad etish chegarasi serverda qayta hisoblanadi."""

    permission_classes = (IsStudent,)
    parser_classes = (JSONParser,)
    throttle_classes = (LabEventThrottle,)

    @extend_schema(request=_EventIn, responses={201: EventOut}, summary="Laboratoriya hodisasi")
    def post(self, request: Request, code: str) -> Response:
        student, section, topic = _student_context(request.user, code)
        data = _EventIn(data=request.data)
        data.is_valid(raise_exception=True)
        limit, proctored = paste_rules(section, topic)
        if data.validated_data["kind"] == "tab_hidden":
            # INT-05: faqat nazorat rejimida; oddiy rejimda tab almashtirish talabaning ishi.
            if proctored:
                LabEvent.objects.create(
                    student=student,
                    section=section,
                    topic=topic,
                    kind=LabEventKind.TAB_HIDDEN,
                    size=0,
                    cell="",
                )
            return Response(
                {"blocked": False, "recorded": proctored}, status=status.HTTP_201_CREATED
            )
        size = data.validated_data["size"]
        blocked = proctored or size > limit
        LabEvent.objects.create(
            student=student,
            section=section,
            topic=topic,
            kind=LabEventKind.PASTE_BLOCKED if blocked else LabEventKind.PASTE,
            size=size,
            cell=data.validated_data["cell"],
        )
        return Response({"blocked": blocked, "recorded": True}, status=status.HTTP_201_CREATED)
