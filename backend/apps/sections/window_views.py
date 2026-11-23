"""Kirish oynalari API (I1-08; ACC-02, ACC-03, ACC-09, ACC-11). Begona guruh — 404, talaba — 403."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone
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
from apps.courses.models import Topic
from apps.sections.member_views import STAFF_OR_INSTRUCTOR
from apps.sections.models import AccessWindow, Section, WindowMode
from apps.sections.views import _locked_visible_section, sections_for
from apps.sections.windows import window_state

MAX_OPEN_MINUTES = 7 * 24 * 60


def _snapshot(window: AccessWindow | None) -> dict[str, Any]:
    if window is None:
        return {
            "mode": WindowMode.CLOSED.value,
            "opens_at": None,
            "closes_at": None,
            "proctored": False,
        }
    return {
        "mode": window.mode,
        "opens_at": window.opens_at.isoformat() if window.opens_at else None,
        "closes_at": window.closes_at.isoformat() if window.closes_at else None,
        "proctored": window.proctored,
    }


def _state_payload(window: AccessWindow | None) -> dict[str, Any]:
    state = window_state(window, timezone.now())
    return {
        "status": state.status,
        "opens_at": state.opens_at,
        "closes_at": state.closes_at,
        "seconds_left": state.seconds_left,
        "seconds_until_open": state.seconds_until_open,
    }


def _row(topic: Topic, window: AccessWindow | None) -> dict[str, Any]:
    return {
        "topic": {"code": topic.code, "title": topic.title, "order": topic.order},
        "mode": window.mode if window else WindowMode.CLOSED,
        "proctored": window.proctored if window else False,
        "state": _state_payload(window),
    }


def _topic_or_404(section: Section, code: str) -> Topic:
    topic = Topic.objects.filter(course_id=section.course_id, code=code).first()
    if topic is None:
        raise NotFound
    return topic


def change_window(
    actor: User, section: Section, topic: Topic, values: dict[str, Any]
) -> AccessWindow:
    """Yagona yozish yo'li (ACC-11: har o'zgarish audit). Chaqiruvchi guruh qatorini qulflagan."""
    window = AccessWindow.objects.select_for_update().filter(section=section, topic=topic).first()
    before = _snapshot(window)
    if window is None:
        window = AccessWindow(section=section, topic=topic)
    for name, value in values.items():
        setattr(window, name, value)
    after = _snapshot(window)
    if before != after:
        window.save()
        record(
            Action.ACCESS_WINDOW_CHANGED,
            actor=actor,
            target=window,
            before=before,
            after=after,
        )
    return window


WindowRow = inline_serializer(
    "AccessWindowRow",
    {
        "topic": serializers.DictField(),
        "mode": serializers.CharField(),
        "proctored": serializers.BooleanField(),
        "state": serializers.DictField(),
    },
)


class WindowListView(APIView):
    permission_classes = STAFF_OR_INSTRUCTOR

    @extend_schema(
        responses={
            200: inline_serializer(
                "AccessWindowList",
                {"server_time": serializers.DateTimeField(), "windows": WindowRow},
            )
        },
        summary="Guruh mavzulari bo'yicha kirish oynalari",
    )
    def get(self, request: Request, section_id: int) -> Response:
        section = sections_for(request.user).filter(pk=section_id).first()  # type: ignore[arg-type]
        if section is None:
            raise NotFound
        windows = {w.topic_id: w for w in AccessWindow.objects.filter(section=section)}
        topics = Topic.objects.filter(course_id=section.course_id).order_by("order")
        return Response(
            {
                "server_time": timezone.now(),
                "windows": [_row(t, windows.get(t.pk)) for t in topics],
            }
        )


class WindowPutSerializer(serializers.Serializer[Any]):
    mode = serializers.ChoiceField(choices=WindowMode.choices)
    opens_at = serializers.DateTimeField(required=False, allow_null=True)
    closes_at = serializers.DateTimeField(required=False, allow_null=True)
    proctored = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        mode, opens, closes = attrs["mode"], attrs.get("opens_at"), attrs.get("closes_at")
        if mode == WindowMode.CLOSED:
            attrs["opens_at"] = attrs["closes_at"] = None
        elif mode == WindowMode.SCHEDULED:
            if opens is None or closes is None:
                raise serializers.ValidationError("Jadval uchun ochilish va yopilish vaqti kerak.")
        elif opens is None:
            attrs["opens_at"] = timezone.now()
        opens, closes = attrs.get("opens_at"), attrs.get("closes_at")
        if opens is not None and closes is not None and closes <= opens:
            raise serializers.ValidationError("Yopilish vaqti ochilishdan keyin bo'lishi kerak.")
        attrs.setdefault("closes_at", None)
        return attrs


class OpenNowSerializer(serializers.Serializer[Any]):
    minutes = serializers.IntegerField(min_value=1, max_value=MAX_OPEN_MINUTES, required=False)


class _WindowAction(APIView):
    permission_classes = STAFF_OR_INSTRUCTOR
    parser_classes = (JSONParser,)

    def _change(
        self, request: Request, section_id: int, code: str, values: dict[str, Any]
    ) -> Response:
        with transaction.atomic():
            section = _locked_visible_section(request.user, section_id)  # type: ignore[arg-type]
            topic = _topic_or_404(section, code)
            window = change_window(request.user, section, topic, values)  # type: ignore[arg-type]
        return Response(_row(topic, window if window.pk else None))


class WindowDetailView(_WindowAction):
    @extend_schema(
        request=WindowPutSerializer, responses={200: WindowRow}, summary="Oynani belgilash"
    )
    def put(self, request: Request, section_id: int, code: str) -> Response:
        data = WindowPutSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return self._change(request, section_id, code, dict(data.validated_data))


class OpenNowView(_WindowAction):
    @extend_schema(request=OpenNowSerializer, responses={200: WindowRow}, summary="Hozir ochish")
    def post(self, request: Request, section_id: int, code: str) -> Response:
        data = OpenNowSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        now = timezone.now()
        minutes = data.validated_data.get("minutes")
        closes = now + timedelta(minutes=minutes) if minutes else None
        return self._change(
            request,
            section_id,
            code,
            {"mode": WindowMode.OPEN_NOW, "opens_at": now, "closes_at": closes},
        )


class CloseView(_WindowAction):
    @extend_schema(request=None, responses={200: WindowRow}, summary="Oynani yopish")
    def post(self, request: Request, section_id: int, code: str) -> Response:
        return self._change(
            request,
            section_id,
            code,
            {"mode": WindowMode.CLOSED, "opens_at": None, "closes_at": None},
        )
