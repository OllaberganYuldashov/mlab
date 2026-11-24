"""Laboratoriya ishi API (I2-16; LAB-05, ACC-06).

Talaba: `GET/PUT /api/labs/{code}/work` — faqat tasdiqlangan guruhi va o'z ishi. Saqlash faqat
`submission_policy` yopiq bo'lmaganda (oyna ochiq, kechikish yoki mashq rejimi);
yopiq — 403 `lab_closed`.
Optimistik qulf: mijoz o'zi ko'rgan `version` ni yuboradi; eskirgan bo'lsa 409 va serverdagi holat.
Bir xil saqlashni qayta yuborish (javob yo'qolgan) — o'sha natija (idempotent).
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
from apps.labs.models import LabWork
from apps.labs.notebook import NotebookError, validate_notebook
from apps.sections.member_views import STAFF_OR_INSTRUCTOR, _visible_section_id
from apps.sections.models import Membership, Section
from apps.sections.policy import SubmissionStatus, submission_policy


class LabSaveThrottle(SimpleRateThrottle):
    """Avtosaqlash — talaba bo'yicha (bir sinf bitta NAT ortida bo'lgani uchun IP emas)."""

    scope = "lab-save"

    def get_rate(self) -> str:
        return str(settings.LAB_SAVE_RATE)

    def allow_request(self, request: Request, view: APIView) -> bool:
        return request.method != "PUT" or super().allow_request(request, view)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.pk)}


WorkOut = inline_serializer(
    "LabWorkOut",
    {
        "version": serializers.IntegerField(),
        "notebook": serializers.JSONField(allow_null=True),
        "saved_at": serializers.DateTimeField(allow_null=True),
        "policy": serializers.ChoiceField(choices=[s.value for s in SubmissionStatus]),
    },
)
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
        Membership.objects.approved().filter(student=user).select_related("section").first()
    )
    if membership is None:
        raise PermissionDenied("Siz hali tasdiqlangan guruh a'zosi emassiz.")
    topic = Topic.objects.filter(course_id=membership.section.course_id, code=code).first()
    if topic is None:
        raise NotFound
    return user, membership.section, topic


def _work_payload(work: LabWork | None, policy: SubmissionStatus) -> dict[str, Any]:
    return {
        "version": work.version if work else 0,
        "notebook": work.notebook if work else None,
        "saved_at": work.saved_at if work else None,
        "policy": policy.value,
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
        return Response(_work_payload(work, submission_policy(section, topic, timezone.now())))

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
            .select_related("section", "topic")
            .first()
        )
        if work is None:
            raise NotFound
        return Response(
            _work_payload(work, submission_policy(work.section, work.topic, timezone.now()))
        )
