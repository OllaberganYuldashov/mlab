"""Shubhali holatlar (I3-14; INT-04, INT-05, ACC-09).

O'qituvchi: `GET /api/sections/{id}/labs/{code}/integrity` — o'z guruhidagi talabalar belgilari:
rad etilgan katta paste'lar, nazorat rejimida tab almashtirish, tushunish savollarida xato,
juda tez to'liq ball.
`PUT .../students/{student_id}/integrity-note` — izoh (bo'sh matn — o'chiradi).

Avtomatik jazo yo'q (INT-04): belgilar faqat o'qiladi, ball va holat o'zgarmaydi —
qarorni o'qituvchi qabul qiladi.
Begona guruh, guruhda tasdiqlanmagan talaba yoki noma'lum mavzu — 404.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Count, F, Q
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Topic
from apps.grading.models import Assignment, Submission, SubmissionStatus, Understanding
from apps.labs.models import NOTE_MAX_LENGTH, IntegrityNote, LabEvent, LabEventKind
from apps.sections.member_views import STAFF_OR_INSTRUCTOR, _visible_section_id
from apps.sections.models import Membership, Section

# Topshiriq berilganidan shu vaqt ichida to'liq ball — "juda tez" (faqat belgi, jazo emas).
FAST_FULL_SCORE = timedelta(minutes=10)


def _section_topic(user: Any, section_id: int, code: str) -> tuple[Section, Topic]:
    _visible_section_id(user, section_id)
    section = Section.objects.select_related("course").get(pk=section_id)
    topic = Topic.objects.filter(course_id=section.course_id, code=code).first()
    if topic is None:
        raise NotFound
    return section, topic


def _note_payload(note: IntegrityNote) -> dict[str, Any]:
    return {"text": note.text, "author": note.author.full_name, "updated_at": note.updated_at}


def integrity_rows(section: Section, topic: Topic) -> list[dict[str, Any]]:
    """Belgisi yoki izohi bor talabalar, FIO bo'yicha. So'rovlar soni talabalarga bog'liq emas."""
    members = {
        m.student_id: m.student
        for m in Membership.objects.approved().filter(section=section).select_related("student")
    }
    events = {
        row["student_id"]: row
        for row in LabEvent.objects.filter(section=section, topic=topic, student_id__in=members)
        .values("student_id")
        .annotate(
            paste_blocked=Count("id", filter=Q(kind=LabEventKind.PASTE_BLOCKED)),
            tab_hidden=Count("id", filter=Q(kind=LabEventKind.TAB_HIDDEN)),
        )
    }
    assignment = (
        Assignment.objects.filter(course_id=section.course_id, topic_code=topic.code)
        .order_by("code")
        .first()
    )
    failed: dict[int, int] = {}
    fast: set[int] = set()
    if assignment is not None:
        submissions = Submission.objects.filter(
            student_assignment__assignment=assignment, student_assignment__student_id__in=members
        )
        failed = dict(
            submissions.filter(understanding=Understanding.FAILED)
            .values_list("student_assignment__student_id")
            .annotate(n=Count("id"))
            .values_list("student_assignment__student_id", "n")
        )
        fast = set(
            submissions.filter(
                status=SubmissionStatus.DONE,
                score=100,
                created_at__lt=F("student_assignment__created_at") + FAST_FULL_SCORE,
            ).values_list("student_assignment__student_id", flat=True)
        )
    notes = {
        n.student_id: n
        for n in IntegrityNote.objects.filter(section=section, topic=topic).select_related("author")
    }
    rows = []
    for student_id, student in members.items():
        ev = events.get(student_id, {})
        row = {
            "student_id": student_id,
            "full_name": student.full_name,
            "paste_blocked": ev.get("paste_blocked", 0),
            "tab_hidden": ev.get("tab_hidden", 0),
            "understanding_failed": failed.get(student_id, 0),
            "fast_full_score": student_id in fast,
            "note": _note_payload(notes[student_id]) if student_id in notes else None,
        }
        flagged = (
            row["paste_blocked"]
            or row["tab_hidden"]
            or row["understanding_failed"]
            or row["fast_full_score"]
        )
        if flagged or row["note"] is not None:
            rows.append(row)
    rows.sort(key=lambda r: (r["full_name"], r["student_id"]))
    return rows


class IntegrityNoteOut(serializers.Serializer[dict[str, Any]]):
    text = serializers.CharField()
    author = serializers.CharField()
    updated_at = serializers.DateTimeField()


FlagsOut = inline_serializer(
    "IntegrityFlagsOut",
    {
        "students": inline_serializer(
            "IntegrityStudent",
            {
                "student_id": serializers.IntegerField(),
                "full_name": serializers.CharField(),
                "paste_blocked": serializers.IntegerField(),
                "tab_hidden": serializers.IntegerField(),
                "understanding_failed": serializers.IntegerField(),
                "fast_full_score": serializers.BooleanField(),
                "note": IntegrityNoteOut(allow_null=True),
            },
            many=True,
        )
    },
)


class _NoteIn(serializers.Serializer[dict[str, Any]]):
    text = serializers.CharField(max_length=NOTE_MAX_LENGTH, allow_blank=True, trim_whitespace=True)


class IntegrityFlagsView(APIView):
    """INT-04: o'qituvchi — guruh x mavzu bo'yicha shubhali holatlar (faqat o'qish)."""

    permission_classes = STAFF_OR_INSTRUCTOR

    @extend_schema(responses={200: FlagsOut}, summary="Shubhali holatlar")
    def get(self, request: Request, section_id: int, code: str) -> Response:
        section, topic = _section_topic(request.user, section_id, code)
        return Response({"students": integrity_rows(section, topic)})


class IntegrityNoteView(APIView):
    """INT-04: o'qituvchi izohi talaba x mavzu uchun. Bo'sh matn — izoh o'chiriladi (204)."""

    permission_classes = STAFF_OR_INSTRUCTOR
    parser_classes = (JSONParser,)

    @extend_schema(
        request=_NoteIn, responses={200: IntegrityNoteOut, 204: None}, summary="Halollik izohi"
    )
    def put(self, request: Request, section_id: int, code: str, student_id: int) -> Response:
        section, topic = _section_topic(request.user, section_id, code)
        if (
            not Membership.objects.approved()
            .filter(section=section, student_id=student_id)
            .exists()
        ):
            raise NotFound
        data = _NoteIn(data=request.data)
        data.is_valid(raise_exception=True)
        text = data.validated_data["text"]
        if not text:
            IntegrityNote.objects.filter(
                section=section, topic=topic, student_id=student_id
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        note, _ = IntegrityNote.objects.update_or_create(
            section=section,
            topic=topic,
            student_id=student_id,
            defaults={"text": text, "author": request.user},
        )
        return Response(_note_payload(note))
