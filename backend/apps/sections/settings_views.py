"""Guruh sozlamalari API (I1-07; SET-01..05). Begona guruh — 404, talaba — 403."""

from __future__ import annotations

from typing import Any

from django.db import transaction
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.audit import record
from apps.audit.models import Action
from apps.courses.models import MAX_LATE_HOURS, AiMode
from apps.sections.member_views import STAFF_OR_INSTRUCTOR
from apps.sections.models import Section
from apps.sections.settings import OVERRIDABLE, course_defaults, effective_settings, overrides
from apps.sections.views import _locked_visible_section, sections_for


class OverridesSerializer(serializers.Serializer[Any]):
    ai_enabled = serializers.BooleanField(allow_null=True, required=False)
    ai_max_mode = serializers.ChoiceField(choices=AiMode.choices, allow_null=True, required=False)
    practice_after_close = serializers.BooleanField(allow_null=True, required=False)
    late_hours = serializers.IntegerField(
        min_value=0, max_value=MAX_LATE_HOURS, allow_null=True, required=False
    )
    chat_enabled = serializers.BooleanField(allow_null=True, required=False)


SettingsOut = inline_serializer(
    "SectionSettings",
    {
        "course_defaults": serializers.DictField(),
        "overrides": serializers.DictField(),
        "effective": serializers.DictField(),
    },
)


def _payload(section: Section) -> dict[str, Any]:
    return {
        "course_defaults": course_defaults(section),
        "overrides": overrides(section),
        "effective": effective_settings(section).as_dict(),
    }


def _apply(actor: User, section: Section, changes: dict[str, Any]) -> None:
    before = overrides(section)
    changed = {k: v for k, v in changes.items() if before[k] != v}
    if not changed:
        return
    for name, value in changed.items():
        setattr(section, name, value)
    section.save(update_fields=[*changed, "updated_at"])
    record(
        Action.SECTION_SETTINGS_CHANGED,
        actor=actor,
        target=section,
        before={k: before[k] for k in changed},
        after=changed,
    )


class SectionSettingsView(APIView):
    permission_classes = STAFF_OR_INSTRUCTOR
    parser_classes = (JSONParser,)

    def _visible(self, request: Request, section_id: int) -> Section:
        visible = sections_for(request.user)  # type: ignore[arg-type]
        section = visible.select_related("course").filter(pk=section_id).first()
        if section is None:
            raise NotFound
        return section

    @extend_schema(responses={200: SettingsOut}, summary="Guruh sozlamalari")
    def get(self, request: Request, section_id: int) -> Response:
        return Response(_payload(self._visible(request, section_id)))

    @extend_schema(
        request=OverridesSerializer,
        responses={200: SettingsOut},
        summary="Guruh override'larini o'zgartirish (null — kurs qiymati)",
    )
    def patch(self, request: Request, section_id: int) -> Response:
        data = OverridesSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            section = _locked_visible_section(request.user, section_id)  # type: ignore[arg-type]
            changes = {k: v for k, v in data.validated_data.items() if k in OVERRIDABLE}
            _apply(request.user, section, changes)  # type: ignore[arg-type]
        return Response(_payload(section))


class AiSwitchView(APIView):
    """SET-02: AI tutorni bir tugma bilan darhol o'chirish yoki yoqish (tasdiq so'ralmaydi)."""

    permission_classes = STAFF_OR_INSTRUCTOR
    enable = False

    @extend_schema(request=None, responses={200: SettingsOut})
    def post(self, request: Request, section_id: int) -> Response:
        with transaction.atomic():
            section = _locked_visible_section(request.user, section_id)  # type: ignore[arg-type]
            _apply(request.user, section, {"ai_enabled": self.enable})  # type: ignore[arg-type]
        return Response(_payload(section))
