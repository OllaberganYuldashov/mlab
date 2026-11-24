"""Ma'ruza API (I2-03; CNT-02, ACC-01, SEC-05).

Ma'ruzalar a'zoga doim ochiq (ACC-01) — kirish oynasi tekshirilmaydi, faqat kursga ruxsat
(`can_access_course`: tasdiqlangan talaba, kurs o'qituvchisi, admin). Begona — 403.
Savollar bankining to'g'ri javoblari bu yerda umuman qaytarilmaydi (faqat sonlari).
"""

from __future__ import annotations

import re
from typing import Any

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role, User
from apps.courses.models import LICENSES, Course, Dataset, LectureImage, LectureStep, Topic
from apps.sections.access import can_access_course
from apps.sections.models import AccessWindow, Membership
from apps.sections.windows import window_state

_SHA_RE = re.compile(r"^[0-9a-f]{64}\Z")
# `![alt](images/nom.png)` — importda tekshirilgan rasm nomlari; mavjud bo'lsa xesh URL'ga
# almashadi.
_IMAGE_REF_RE = re.compile(r"(!\[[^\]]*\]\()images/([A-Za-z0-9_-]+\.(?:png|jpg|jpeg|webp))\)")
IMAGE_CACHE = "private, max-age=31536000, immutable"  # URL'da xesh bor — mazmun o'zgarmaydi


def _course_for(user: Any) -> Course:
    course = Course.objects.order_by("id").first()
    if course is None:
        raise NotFound
    if not isinstance(user, User) or not can_access_course(user, course):
        raise PermissionDenied
    return course


def image_url(sha256: str) -> str:
    return f"/api/course/images/{sha256}"


def _with_image_urls(body: str, images: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        sha = images.get(match.group(2))
        return f"{match.group(1)}{image_url(sha)})" if sha else match.group(0)

    return _IMAGE_REF_RE.sub(replace, body)


_LabState = inline_serializer(
    "LabState",
    {
        "status": serializers.CharField(),
        "opens_at": serializers.DateTimeField(allow_null=True),
        "closes_at": serializers.DateTimeField(allow_null=True),
    },
    allow_null=True,
)


class TopicListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        responses={
            200: inline_serializer(
                "CourseTopics",
                {
                    "course": inline_serializer(
                        "CourseBrief",
                        {"slug": serializers.CharField(), "title": serializers.CharField()},
                    ),
                    "topics": inline_serializer(
                        "TopicBrief",
                        {
                            "code": serializers.CharField(),
                            "title": serializers.CharField(),
                            "order": serializers.IntegerField(),
                            "steps": serializers.IntegerField(),
                            "questions": serializers.IntegerField(),
                            "lab": _LabState,
                        },
                        many=True,
                    ),
                },
            )
        },
        summary="Kurs mavzulari (talabaga — laboratoriya holati bilan)",
    )
    def get(self, request: Request) -> Response:
        course = _course_for(request.user)
        topics = (
            Topic.objects.filter(course=course)
            .annotate(
                step_count=Count("lecture__steps", distinct=True),
                question_count=Count(
                    "questions", filter=Q(questions__is_active=True), distinct=True
                ),
            )
            .order_by("order")
        )
        windows: dict[int, AccessWindow] | None = None
        user = request.user
        if isinstance(user, User) and user.role == Role.STUDENT:
            membership = Membership.objects.approved().filter(student=user).first()
            windows = (
                {
                    w.topic_id: w
                    for w in AccessWindow.objects.filter(section_id=membership.section_id)
                }
                if membership
                else {}
            )
        now = timezone.now()

        def lab(topic: Topic) -> dict[str, Any] | None:
            if windows is None:
                return None
            state = window_state(windows.get(topic.pk), now)
            return {
                "status": state.status,
                "opens_at": state.opens_at,
                "closes_at": state.closes_at,
            }

        return Response(
            {
                "course": {"slug": course.slug, "title": course.title},
                "topics": [
                    {
                        "code": t.code,
                        "title": t.title,
                        "order": t.order,
                        "steps": t.step_count,
                        "questions": t.question_count,
                        "lab": lab(t),
                    }
                    for t in topics
                ],
            }
        )


class LectureView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        responses={
            200: inline_serializer(
                "LectureOut",
                {
                    "topic": inline_serializer(
                        "TopicRef",
                        {"code": serializers.CharField(), "title": serializers.CharField()},
                    ),
                    "title": serializers.CharField(),
                    "prev": serializers.CharField(allow_null=True),
                    "next": serializers.CharField(allow_null=True),
                    "steps": inline_serializer(
                        "LectureStepOut",
                        {
                            "order": serializers.IntegerField(),
                            "title": serializers.CharField(),
                            "body": serializers.CharField(),
                            "question": serializers.JSONField(allow_null=True),
                        },
                        many=True,
                    ),
                },
            )
        },
        summary="Ma'ruza qadamlari (rasm havolalari xesh URL bilan)",
    )
    def get(self, request: Request, code: str) -> Response:
        course = _course_for(request.user)
        topic = Topic.objects.filter(course=course, code=code).select_related("lecture").first()
        lecture = getattr(topic, "lecture", None) if topic else None
        if topic is None or lecture is None:
            raise NotFound
        images = dict(LectureImage.objects.filter(topic=topic).values_list("name", "sha256"))
        steps = LectureStep.objects.filter(lecture=lecture).order_by("order")
        siblings = Topic.objects.filter(course=course).order_by("order")
        prev = (
            siblings.filter(order__lt=topic.order)
            .order_by("-order")
            .values_list("code", flat=True)
            .first()
        )
        nxt = siblings.filter(order__gt=topic.order).values_list("code", flat=True).first()
        return Response(
            {
                "topic": {"code": topic.code, "title": topic.title},
                "title": lecture.title,
                "prev": prev,
                "next": nxt,
                "steps": [
                    {
                        "order": s.order,
                        "title": s.title,
                        "body": _with_image_urls(s.body, images),
                        "question": s.question,
                    }
                    for s in steps
                ],
            }
        )


class LectureImageView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        responses={(200, "image/*"): OpenApiTypes.BINARY},
        summary="Ma'ruza rasmi (xesh bo'yicha, abadiy kesh)",
    )
    def get(self, request: Request, sha256: str) -> HttpResponse:
        if not _SHA_RE.match(sha256):
            raise NotFound
        course = _course_for(request.user)
        image = (
            LectureImage.objects.filter(sha256=sha256, topic__course=course)
            .only("content_type", "data")
            .first()
        )
        if image is None:
            raise NotFound
        response = HttpResponse(bytes(image.data), content_type=image.content_type)
        response["Cache-Control"] = IMAGE_CACHE
        response["Content-Disposition"] = "inline"
        return response


DatasetOut = inline_serializer(
    "DatasetOut",
    {
        "name": serializers.CharField(),
        "title": serializers.CharField(),
        "description": serializers.CharField(),
        "source_url": serializers.URLField(),
        "license": serializers.CharField(),
        "license_url": serializers.URLField(),
        "rows": serializers.IntegerField(),
        "columns": serializers.ListField(child=serializers.CharField()),
        "size": serializers.IntegerField(),
    },
    many=True,
)


class DatasetListView(APIView):
    """DAT-02: datasetlar ro'yxati — manba havolasi va litsenziya bilan."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: DatasetOut}, summary="Kurs datasetlari (manba va litsenziya)")
    def get(self, request: Request) -> Response:
        course = _course_for(request.user)
        datasets = Dataset.objects.filter(course=course).defer("data").order_by("name")
        return Response(
            [
                {
                    "name": d.name,
                    "title": d.title,
                    "description": d.description,
                    "source_url": d.source_url,
                    "license": d.license,
                    "license_url": LICENSES.get(d.license, ""),
                    "rows": d.rows,
                    "columns": d.columns,
                    "size": d.size,
                }
                for d in datasets
            ]
        )


class DatasetFileView(APIView):
    """LAB-04: `mlab.load("nomi")` shu yerdan CSV oladi (Pyodide worker, o'z sessiyasi bilan)."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={(200, "text/csv"): OpenApiTypes.BINARY}, summary="Dataset CSV fayli")
    def get(self, request: Request, name: str) -> HttpResponse:
        course = _course_for(request.user)
        dataset = Dataset.objects.filter(course=course, name=name).only("name", "data").first()
        if dataset is None:
            raise NotFound
        response = HttpResponse(bytes(dataset.data), content_type="text/csv; charset=utf-8")
        response["Cache-Control"] = "private, max-age=300"
        response["Content-Disposition"] = f'inline; filename="{dataset.name}.csv"'
        return response
