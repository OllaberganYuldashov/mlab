"""Kirish oynalari API (I1-08; ACC-02, ACC-03, ACC-09, ACC-11). Begona guruh — 404, talaba — 403."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
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
from apps.accounts.permissions import IsStudent
from apps.audit import record
from apps.audit.models import Action
from apps.courses.models import Topic
from apps.sections import realtime
from apps.sections.member_views import STAFF_OR_INSTRUCTOR
from apps.sections.models import AccessWindow, Membership, Section, WindowMode
from apps.sections.planning import MAX_SLOT_MINUTES, Slot, plan_slots
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
        # ACC-05: guruh talabalariga real vaqtda (JSON'ga tayyor qiymatlar).
        row = _row(topic, window)
        realtime.window_changed(
            section.pk,
            {
                "topic": topic.code,
                "mode": str(row["mode"]),
                "state": {
                    k: v.isoformat() if hasattr(v, "isoformat") else v
                    for k, v in row["state"].items()
                },
            },
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
    """Ochiq oyna yopilsa yopilish lahzasi saqlanadi (`closes_at=now`): kechikish va mashq shundan
    hisoblanadi (ACC-07/08). Hali ochilmagan oyna — `closed`; allaqachon yopilgani o'zgarmaydi."""

    @extend_schema(request=None, responses={200: WindowRow}, summary="Oynani yopish")
    def post(self, request: Request, section_id: int, code: str) -> Response:
        now = timezone.now()
        with transaction.atomic():
            section = _locked_visible_section(request.user, section_id)  # type: ignore[arg-type]
            topic = _topic_or_404(section, code)
            current = AccessWindow.objects.filter(section=section, topic=topic).first()
            status = window_state(current, now).status
            values: dict[str, Any]
            if status == "open" and current is not None and current.opens_at != now:
                values = {"closes_at": now}
            elif status == "closed" and current is not None and current.opens_at is not None:
                values = {}  # tarixiy yopilish lahzasi saqlanadi
            else:
                values = {"mode": WindowMode.CLOSED, "opens_at": None, "closes_at": None}
            window = change_window(request.user, section, topic, values)  # type: ignore[arg-type]
        return Response(_row(topic, window if window.pk else None))


class SlotSerializer(serializers.Serializer[Any]):
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    time = serializers.TimeField()
    minutes = serializers.IntegerField(min_value=1, max_value=MAX_SLOT_MINUTES)


class PlanSerializer(serializers.Serializer[Any]):
    slots = serializers.ListField(child=SlotSerializer(), min_length=1, max_length=14)
    start_date = serializers.DateField()
    topics = serializers.ListField(
        child=serializers.CharField(max_length=8), required=False, max_length=200
    )
    preview = serializers.BooleanField(default=True)
    overwrite = serializers.BooleanField(default=False)


class PlanView(APIView):
    """ACC-04: `preview: true` faqat ko'rsatadi; `false` bitta tranzaksiyada saqlaydi."""

    permission_classes = STAFF_OR_INSTRUCTOR
    parser_classes = (JSONParser,)

    @extend_schema(
        request=PlanSerializer,
        responses={
            200: inline_serializer(
                "WindowPlan",
                {
                    "plan": inline_serializer(
                        "WindowPlanItem",
                        {
                            "topic": serializers.CharField(),
                            "opens_at": serializers.DateTimeField(),
                            "closes_at": serializers.DateTimeField(),
                        },
                        many=True,
                    ),
                    "saved": serializers.BooleanField(),
                },
            )
        },
        summary="Haftalik slot bo'yicha oynalarni rejalashtirish",
    )
    def post(self, request: Request, section_id: int) -> Response:
        data = PlanSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        params = data.validated_data
        section = sections_for(request.user).filter(pk=section_id).first()  # type: ignore[arg-type]
        if section is None:
            raise NotFound
        topics = self._topics(section, params.get("topics"))
        slots = [Slot(s["weekday"], s["time"], s["minutes"]) for s in params["slots"]]
        try:
            moments = plan_slots(
                len(topics), slots, params["start_date"], ZoneInfo(settings.TIME_ZONE)
            )
        except ValueError as exc:
            raise serializers.ValidationError({"slots": [str(exc)]}) from exc
        plan = list(zip(topics, moments, strict=True))
        if not params["preview"]:
            with transaction.atomic():
                locked = _locked_visible_section(request.user, section_id)  # type: ignore[arg-type]
                busy = list(
                    AccessWindow.objects.filter(section=locked, topic__in=topics)
                    .exclude(mode=WindowMode.CLOSED)
                    .order_by("topic__order")
                    .values_list("topic__code", flat=True)
                )
                if busy and not params["overwrite"]:
                    return Response(
                        {
                            "code": "windows_exist",
                            "detail": "Bu mavzularda oyna bor. Almashtirish uchun overwrite.",
                            "topics": busy,
                        },
                        status=409,
                    )
                for topic, (opens, closes) in plan:
                    change_window(
                        request.user,  # type: ignore[arg-type]
                        locked,
                        topic,
                        {"mode": WindowMode.SCHEDULED, "opens_at": opens, "closes_at": closes},
                    )
        return Response(
            {
                "plan": [{"topic": t.code, "opens_at": o, "closes_at": c} for t, (o, c) in plan],
                "saved": not params["preview"],
            }
        )

    @staticmethod
    def _topics(section: Section, codes: list[str] | None) -> list[Topic]:
        all_topics = list(Topic.objects.filter(course_id=section.course_id).order_by("order"))
        if codes is None:
            return all_topics
        if len(set(codes)) != len(codes):
            raise serializers.ValidationError({"topics": ["Mavzu takrorlangan."]})
        by_code = {t.code: t for t in all_topics}
        missing = [c for c in codes if c not in by_code]
        if missing:
            raise serializers.ValidationError({"topics": [f"Noma'lum mavzu: {', '.join(missing)}"]})
        return [by_code[c] for c in codes]


class MyNextWindowView(APIView):
    """ACC-05: talaba ochiq laboratoriyalarni va keyingi ochiladigan mavzuni ko'radi.

    `server_time` bilan: mijoz soat farqini hisoblab, qolgan vaqtni o'zi sanaydi va ochilish
    lahzasida shu endpoint'ni qayta so'raydi (rejalashtirilgan ochilish push'i — I3, Celery beat).
    """

    permission_classes = (IsStudent,)

    @extend_schema(
        responses={
            200: inline_serializer(
                "MyNextWindow",
                {
                    "server_time": serializers.DateTimeField(),
                    "open": WindowRow,
                    "next": WindowRow,
                },
            )
        },
        summary="Mening ochiq va keyingi laboratoriyalarim",
    )
    def get(self, request: Request) -> Response:
        now = timezone.now()
        student = request.user
        assert isinstance(student, User)  # IsStudent kafolatlaydi  # noqa: S101
        membership = Membership.objects.approved().filter(student=student).first()
        if membership is None:
            return Response({"server_time": now, "open": [], "next": None})
        windows = (
            AccessWindow.objects.filter(section_id=membership.section_id)
            .exclude(mode=WindowMode.CLOSED)
            .select_related("topic")
            .order_by("opens_at", "topic__order")
        )
        open_rows, upcoming = [], []
        for window in windows:
            status = window_state(window, now).status
            if status == "open":
                open_rows.append(_row(window.topic, window))
            elif status == "upcoming":
                upcoming.append(_row(window.topic, window))
        return Response(
            {"server_time": now, "open": open_rows, "next": upcoming[0] if upcoming else None}
        )
