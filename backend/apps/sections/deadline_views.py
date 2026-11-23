"""Mustaqil topshiriq muddatlari API (I1-10; ACC-10). Begona guruh — 404, talaba — 403."""

from __future__ import annotations

import re
from typing import Any

from django.db import transaction
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsStudent
from apps.audit import record
from apps.audit.models import Action
from apps.sections.member_views import STAFF_OR_INSTRUCTOR
from apps.sections.models import IndependentDeadline, Membership
from apps.sections.views import _locked_visible_section, sections_for

_CODE_RE = re.compile(r"^A[0-9]{2}$")

DeadlineOut = inline_serializer(
    "IndependentDeadline",
    {"assignment": serializers.CharField(), "due_at": serializers.DateTimeField()},
)


def _rows(deadlines: Any) -> list[dict[str, Any]]:
    return [{"assignment": d.assignment, "due_at": d.due_at} for d in deadlines]


class DeadlineListView(APIView):
    permission_classes = STAFF_OR_INSTRUCTOR

    @extend_schema(
        responses={200: inline_serializer("DeadlineList", {"deadlines": DeadlineOut})},
        summary="Guruhning mustaqil topshiriq muddatlari",
    )
    def get(self, request: Request, section_id: int) -> Response:
        section = sections_for(request.user).filter(pk=section_id).first()  # type: ignore[arg-type]
        if section is None:
            raise NotFound
        deadlines = IndependentDeadline.objects.filter(section=section).order_by("assignment")
        return Response({"deadlines": _rows(deadlines)})


class DeadlinePutSerializer(serializers.Serializer[Any]):
    due_at = serializers.DateTimeField()


class DeadlineDetailView(APIView):
    permission_classes = STAFF_OR_INSTRUCTOR
    parser_classes = (JSONParser,)

    @staticmethod
    def _code(code: str) -> str:
        if not _CODE_RE.fullmatch(code):
            raise NotFound
        return code

    @extend_schema(request=DeadlinePutSerializer, responses={200: DeadlineOut}, summary="Muddat")
    def put(self, request: Request, section_id: int, code: str) -> Response:
        code = self._code(code)
        data = DeadlinePutSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        due_at = data.validated_data["due_at"]
        with transaction.atomic():
            section = _locked_visible_section(request.user, section_id)  # type: ignore[arg-type]
            deadline = IndependentDeadline.objects.filter(section=section, assignment=code).first()
            before = deadline.due_at.isoformat() if deadline else None
            if deadline is None:
                deadline = IndependentDeadline(section=section, assignment=code, due_at=due_at)
            deadline.due_at = due_at
            if before != due_at.isoformat():
                deadline.save()
                record(
                    Action.DEADLINE_CHANGED,
                    actor=request.user,  # type: ignore[arg-type]
                    target=deadline,
                    before={"due_at": before},
                    after={"due_at": due_at.isoformat()},
                )
        return Response({"assignment": deadline.assignment, "due_at": deadline.due_at})

    @extend_schema(request=None, responses={204: None}, summary="Muddatni olib tashlash")
    def delete(self, request: Request, section_id: int, code: str) -> Response:
        code = self._code(code)
        with transaction.atomic():
            section = _locked_visible_section(request.user, section_id)  # type: ignore[arg-type]
            deadline = IndependentDeadline.objects.filter(section=section, assignment=code).first()
            if deadline is not None:
                record(
                    Action.DEADLINE_CHANGED,
                    actor=request.user,  # type: ignore[arg-type]
                    target=deadline,
                    before={"due_at": deadline.due_at.isoformat()},
                    after={"due_at": None},
                )
                deadline.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyDeadlinesView(APIView):
    """Talaba: faqat tasdiqlangan guruhining muddatlari."""

    permission_classes = (IsStudent,)

    @extend_schema(
        responses={200: inline_serializer("MyDeadlines", {"deadlines": DeadlineOut})},
        summary="Mening mustaqil topshiriq muddatlarim",
    )
    def get(self, request: Request) -> Response:
        student = request.user
        assert isinstance(student, User)  # noqa: S101
        membership = Membership.objects.approved().filter(student=student).first()
        if membership is None:
            return Response({"deadlines": []})
        deadlines = IndependentDeadline.objects.filter(section_id=membership.section_id).order_by(
            "assignment"
        )
        return Response({"deadlines": _rows(deadlines)})
