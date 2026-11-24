"""I1-15 `/hunt-n-plus-one`: ro'yxat endpoint'larida so'rovlar soni qatorlar soniga bog'liq emas.

Har endpoint kam va ko'p qator bilan chaqiriladi; so'rovlar soni bir xil bo'lishi kerak.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Topic
from apps.sections.models import AccessWindow, Membership, MembershipStatus, Section, WindowMode
from tests.accounts.factories import make_user
from tests.sections.factories import make_membership, make_section

pytestmark = pytest.mark.django_db


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _count(client: APIClient, url: str) -> int:
    with CaptureQueriesContext(connection) as ctx:
        assert client.get(url).status_code == 200
    return len(ctx.captured_queries)


def _approve(membership: Membership) -> None:
    membership.status = MembershipStatus.APPROVED
    membership.decided_at = timezone.now()
    membership.decided_by = membership.section.instructor
    membership.save()


def _grow(add: Callable[[int], None], client: APIClient, url: str) -> tuple[int, int]:
    add(1)
    few = _count(client, url)
    add(6)
    return few, _count(client, url)


@pytest.mark.parametrize("status", ["pending", "approved"])
def test_i1_members_list_query_count_is_constant(status: str) -> None:
    section = make_section()

    def add(n: int) -> None:
        for _ in range(n):
            m = make_membership(section=section, student=make_user())
            if status == "approved":
                _approve(m)

    few, many = _grow(
        add, _client(section.instructor), f"/api/sections/{section.pk}/members?status={status}"
    )
    assert few == many


def _topics(section: Section, start: int, n: int) -> list[Topic]:
    return [
        Topic.objects.create(course=section.course, code=f"M{i:02d}", title=f"T{i}", order=i)
        for i in range(start, start + n)
    ]


def test_i1_windows_list_query_count_is_constant() -> None:
    section = make_section()
    made: list[int] = [0]

    def add(n: int) -> None:
        for topic in _topics(section, made[0] + 1, n):
            now = timezone.now()
            AccessWindow.objects.create(
                section=section, topic=topic, mode=WindowMode.OPEN_NOW, opens_at=now
            )
        made[0] += n

    few, many = _grow(add, _client(section.instructor), f"/api/sections/{section.pk}/windows")
    assert few == many


def test_i1_student_next_window_query_count_is_constant() -> None:
    membership = make_membership()
    _approve(membership)
    section = membership.section
    made: list[int] = [0]
    soon = timezone.now() + timedelta(days=1)

    def add(n: int) -> None:
        for topic in _topics(section, made[0] + 1, n):
            AccessWindow.objects.create(
                section=section,
                topic=topic,
                mode=WindowMode.SCHEDULED,
                opens_at=soon + timedelta(hours=topic.order),
                closes_at=soon + timedelta(hours=topic.order, minutes=80),
            )
        made[0] += n

    few, many = _grow(add, _client(membership.student), "/api/me/next-window")
    assert few == many


def test_i1_sections_list_query_count_is_constant() -> None:
    first = make_section()
    instructor = first.instructor

    def add(n: int) -> None:
        for _ in range(n):
            section = make_section(instructor=instructor, course=first.course)
            _approve(make_membership(section=section, student=make_user()))

    few, many = _grow(add, _client(instructor), "/api/sections")
    assert few == many
