"""Mavzu testi API (I2-07; CNT-06). Faqat kursga a'zo talaba; boshqa talabaning urinishi — 404."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsStudent
from apps.courses.models import Course, Question, QuizAttempt, Topic
from apps.courses.quiz import QuizRefused, attempt_payload, start_attempt, submit_attempt
from apps.courses.views import _course_for

AttemptOut = inline_serializer(
    "QuizAttemptOut",
    {
        "id": serializers.IntegerField(),
        "number": serializers.IntegerField(),
        "deadline": serializers.DateTimeField(),
        "server_time": serializers.DateTimeField(),
        "submitted_at": serializers.DateTimeField(allow_null=True),
        "score": serializers.IntegerField(allow_null=True),
        "max_score": serializers.IntegerField(),
        "questions": inline_serializer(
            "QuizQuestionOut",
            {
                "position": serializers.IntegerField(),
                "text": serializers.CharField(),
                "options": serializers.ListField(child=serializers.CharField()),
                "chosen": serializers.IntegerField(required=False, allow_null=True),
                "answer": serializers.IntegerField(required=False),
                "correct": serializers.BooleanField(required=False),
            },
            many=True,
        ),
    },
)


def _student_topic(user: Any, code: str) -> tuple[User, Course, Topic]:
    course = _course_for(user)
    assert isinstance(user, User)  # noqa: S101 — IsStudent va _course_for kafolatlaydi
    topic = Topic.objects.filter(course=course, code=code).first()
    if topic is None:
        raise NotFound
    return user, course, topic


def _refused(exc: QuizRefused) -> Response:
    return Response({"code": exc.code, "detail": exc.detail}, status=status.HTTP_409_CONFLICT)


class QuizSummaryView(APIView):
    permission_classes = (IsStudent,)

    @extend_schema(
        responses={
            200: inline_serializer(
                "QuizSummary",
                {
                    "settings": inline_serializer(
                        "QuizSettings",
                        {
                            "questions": serializers.IntegerField(),
                            "minutes": serializers.IntegerField(),
                            "attempts": serializers.IntegerField(),
                        },
                    ),
                    "available_questions": serializers.IntegerField(),
                    "used_attempts": serializers.IntegerField(),
                    "active_attempt": serializers.IntegerField(allow_null=True),
                    "attempts": inline_serializer(
                        "QuizAttemptBrief",
                        {
                            "id": serializers.IntegerField(),
                            "number": serializers.IntegerField(),
                            "score": serializers.IntegerField(allow_null=True),
                            "max_score": serializers.IntegerField(),
                            "submitted_at": serializers.DateTimeField(allow_null=True),
                        },
                        many=True,
                    ),
                },
            )
        },
        summary="Mavzu testi: sozlamalar va mening urinishlarim",
    )
    def get(self, request: Request, code: str) -> Response:
        student, course, topic = _student_topic(request.user, code)
        attempts = list(QuizAttempt.objects.filter(student=student, topic=topic).order_by("number"))
        active = next((a.pk for a in attempts if a.submitted_at is None), None)
        return Response(
            {
                "settings": {
                    "questions": course.quiz_questions,
                    "minutes": course.quiz_minutes,
                    "attempts": course.quiz_attempts,
                },
                "available_questions": Question.objects.filter(topic=topic, is_active=True).count(),
                "used_attempts": len(attempts),
                "active_attempt": active,
                "attempts": [
                    {
                        "id": a.pk,
                        "number": a.number,
                        "score": a.score,
                        "max_score": a.max_score,
                        "submitted_at": a.submitted_at,
                    }
                    for a in attempts
                ],
            }
        )


class QuizStartView(APIView):
    permission_classes = (IsStudent,)

    @extend_schema(
        request=None, responses={200: AttemptOut, 201: AttemptOut}, summary="Testni boshlash"
    )
    def post(self, request: Request, code: str) -> Response:
        student, course, topic = _student_topic(request.user, code)
        try:
            attempt, created = start_attempt(student, course, topic)
        except QuizRefused as exc:
            return _refused(exc)
        return Response(
            attempt_payload(attempt),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


def _own_attempt(user: Any, attempt_id: int) -> QuizAttempt:
    if not isinstance(user, User):
        raise PermissionDenied
    attempt = QuizAttempt.objects.filter(pk=attempt_id, student=user).first()
    if attempt is None:
        raise NotFound
    return attempt


class QuizAttemptView(APIView):
    permission_classes = (IsStudent,)

    @extend_schema(
        responses={200: AttemptOut}, summary="Urinish (javoblar faqat topshirilgandan keyin)"
    )
    def get(self, request: Request, attempt_id: int) -> Response:
        return Response(attempt_payload(_own_attempt(request.user, attempt_id)))


class QuizSubmitView(APIView):
    permission_classes = (IsStudent,)
    parser_classes = (JSONParser,)

    @extend_schema(
        request=inline_serializer(
            "QuizSubmitIn", {"answers": serializers.DictField(child=serializers.IntegerField())}
        ),
        responses={200: AttemptOut},
        summary="Testni topshirish",
    )
    def post(self, request: Request, attempt_id: int) -> Response:
        attempt = _own_attempt(request.user, attempt_id)
        raw = request.data.get("answers") if isinstance(request.data, dict) else None
        if not isinstance(raw, dict):
            raise ValidationError({"answers": ["{tartib: variant} obyekti"]})
        answers: dict[int, int] = {}
        for key, value in raw.items():
            if not str(key).isdigit() or type(value) is not int:
                raise ValidationError(
                    {"answers": ["kalit — savol tartibi, qiymat — variant raqami"]}
                )
            answers[int(key)] = value
        try:
            done = submit_attempt(attempt.pk, attempt.student, answers)
        except QuizRefused as exc:
            return _refused(exc)
        except ValueError as exc:
            raise ValidationError({"answers": [str(exc)]}) from exc
        return Response(attempt_payload(done))
