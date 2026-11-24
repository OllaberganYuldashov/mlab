"""I2-21 `/hunt-n-plus-one`: I2 ro'yxatlarida so'rovlar soni qatorlar soniga bog'liq emas."""

from __future__ import annotations

import hashlib

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Course, Dataset, Question, Topic
from apps.sections.models import MembershipStatus
from tests.accounts.factories import make_user
from tests.sections.factories import make_course, make_membership, make_section

pytestmark = pytest.mark.django_db


def _student(course: Course) -> User:
    m = make_membership(section=make_section(course=course), student=make_user())
    m.status = MembershipStatus.APPROVED
    m.decided_at = timezone.now()
    m.decided_by = m.section.instructor
    m.save()
    return m.student


def _count(client: APIClient, method: str, url: str) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = getattr(client, method)(url)
        assert response.status_code in (200, 201), response.content
    return len(ctx.captured_queries)


def _questions(topic: Topic, start: int, n: int) -> None:
    for i in range(start, start + n):
        Question.objects.create(
            topic=topic, key=f"{i:064x}", text=f"S{i}", options=["a", "b"], answer=0, position=i + 1
        )


def test_i2_quiz_attempt_payload_constant() -> None:
    course = make_course()
    topic = Topic.objects.create(course=course, code="M01", title="T", order=1)
    _questions(topic, 0, 8)
    counts = []
    for n in (2, 8):
        course.quiz_questions = n
        course.save()
        client = APIClient()
        client.force_authenticate(_student(course))
        attempt = client.post("/api/course/topics/M01/quiz/attempts").json()
        assert len(attempt["questions"]) == n
        counts.append(_count(client, "get", f"/api/course/quiz/attempts/{attempt['id']}"))
    assert counts[0] == counts[1]


def test_i2_datasets_list_constant() -> None:
    course = make_course()
    client = APIClient()
    client.force_authenticate(_student(course))

    def add(n: int, start: int) -> None:
        for i in range(start, start + n):
            data = f"x\n{i}\n".encode()
            Dataset.objects.create(
                course=course,
                name=f"d{i}",
                title="T",
                description="D",
                source_url="https://example.org",
                license="CC0-1.0",
                sha256=hashlib.sha256(data).hexdigest(),
                size=len(data),
                rows=1,
                columns=["x"],
                data=data,
            )

    add(1, 0)
    few = _count(client, "get", "/api/datasets")
    add(6, 1)
    assert _count(client, "get", "/api/datasets") == few


def test_i2_quiz_summary_constant() -> None:
    course = make_course()
    course.quiz_questions, course.quiz_attempts = 1, 10
    course.save()
    topic = Topic.objects.create(course=course, code="M01", title="T", order=1)
    _questions(topic, 0, 3)
    client = APIClient()
    client.force_authenticate(_student(course))

    def attempt_once() -> None:
        a = client.post("/api/course/topics/M01/quiz/attempts").json()
        client.post(f"/api/course/quiz/attempts/{a['id']}/submit", {"answers": {}}, format="json")

    attempt_once()
    few = _count(client, "get", "/api/course/topics/M01/quiz")
    for _ in range(4):
        attempt_once()
    assert _count(client, "get", "/api/course/topics/M01/quiz") == few
