"""ACC-06..08, ACC-10 (I1-10): topshirish siyosati va mustaqil topshiriq muddatlari."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.db import DataError, IntegrityError, transaction
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import Action, AuditLog
from apps.courses.models import Topic
from apps.sections.models import (
    AccessWindow,
    IndependentDeadline,
    Membership,
    MembershipStatus,
    Section,
    WindowMode,
)
from apps.sections.policy import (
    SubmissionStatus,
    apply_late_penalty,
    independent_policy,
    submission_policy,
)
from tests.accounts.factories import make_user
from tests.sections.factories import make_instructor, make_membership, make_section

pytestmark = pytest.mark.django_db
TZ = ZoneInfo("Asia/Tashkent")
OPEN = datetime(2026, 12, 1, 10, 0, tzinfo=TZ)
CLOSE = OPEN + timedelta(minutes=80)


def _setup(**section_fields: Any) -> tuple[Section, Topic]:
    section = make_section(**section_fields)
    topic = Topic.objects.create(course=section.course, code="M01", title="T", order=1)
    return section, topic


def _scheduled(section: Section, topic: Topic) -> AccessWindow:
    return AccessWindow.objects.create(
        section=section, topic=topic, mode=WindowMode.SCHEDULED, opens_at=OPEN, closes_at=CLOSE
    )


# --- submission_policy ---


def test_acc_02_no_window_is_closed() -> None:
    section, topic = _setup()
    assert submission_policy(section, topic, OPEN) == SubmissionStatus.CLOSED


def test_acc_06_on_time_inside_window_closed_at_end() -> None:
    section, topic = _setup()
    _scheduled(section, topic)
    assert submission_policy(section, topic, OPEN) == SubmissionStatus.ON_TIME
    assert (
        submission_policy(section, topic, CLOSE - timedelta(seconds=1)) == SubmissionStatus.ON_TIME
    )
    assert submission_policy(section, topic, CLOSE) == SubmissionStatus.CLOSED
    assert submission_policy(section, topic, OPEN - timedelta(seconds=1)) == SubmissionStatus.CLOSED


def test_acc_07_late_within_late_hours_boundaries() -> None:
    section, topic = _setup(late_hours=2)
    _scheduled(section, topic)
    assert submission_policy(section, topic, CLOSE) == SubmissionStatus.LATE
    edge = CLOSE + timedelta(hours=2)
    assert submission_policy(section, topic, edge - timedelta(seconds=1)) == SubmissionStatus.LATE
    assert submission_policy(section, topic, edge) == SubmissionStatus.CLOSED


def test_acc_08_practice_after_close_when_enabled() -> None:
    section, topic = _setup(practice_after_close=True, late_hours=1)
    _scheduled(section, topic)
    assert submission_policy(section, topic, CLOSE + timedelta(minutes=30)) == SubmissionStatus.LATE
    assert (
        submission_policy(section, topic, CLOSE + timedelta(hours=5)) == SubmissionStatus.PRACTICE
    )
    # Hali ochilmagan mavzuda mashq yo'q.
    assert submission_policy(section, topic, OPEN - timedelta(days=1)) == SubmissionStatus.CLOSED


def test_acc_08_never_opened_closed_window_has_no_practice() -> None:
    section, topic = _setup(practice_after_close=True)
    AccessWindow.objects.create(section=section, topic=topic, mode=WindowMode.CLOSED)
    assert submission_policy(section, topic, OPEN) == SubmissionStatus.CLOSED


def test_acc_07_manual_close_keeps_close_moment_for_late_and_practice() -> None:
    from django.utils import timezone

    section, topic = _setup(practice_after_close=True, late_hours=1)
    client = _client(section.instructor)
    client.post(f"/api/sections/{section.pk}/windows/M01/open-now", {}, format="json")
    client.post(f"/api/sections/{section.pk}/windows/M01/close")
    window = AccessWindow.objects.get()
    assert window.closes_at is not None
    now = timezone.now()
    assert submission_policy(section, topic, now) == SubmissionStatus.LATE
    assert submission_policy(section, topic, now + timedelta(hours=2)) == SubmissionStatus.PRACTICE


def test_acc_07_settings_come_from_course_when_not_overridden() -> None:
    section, topic = _setup()
    section.course.late_hours = 3
    section.course.save()
    _scheduled(section, topic)
    assert submission_policy(section, topic, CLOSE + timedelta(hours=2)) == SubmissionStatus.LATE


@pytest.mark.parametrize(
    ("points", "percent", "expected"),
    [
        ("100", 0, "100.00"),
        ("100", 10, "90.00"),
        ("7", 10, "6.30"),
        ("0.05", 50, "0.03"),  # 0.025 -> 0.03 (yarmi yuqoriga)
        ("8.35", 10, "7.52"),  # 7.515 -> 7.52
        ("0", 30, "0.00"),
        ("99", 100, "0.00"),
    ],
)
def test_acc_07_late_penalty_decimal_round_half_up(
    points: str, percent: int, expected: str
) -> None:
    from decimal import Decimal

    assert apply_late_penalty(Decimal(points), percent) == Decimal(expected)


@pytest.mark.parametrize(("points", "percent"), [(-1, 10), (10, 101), (10, -1)])
def test_acc_07_late_penalty_rejects_bad_input(points: int, percent: int) -> None:
    with pytest.raises(ValueError, match="noto'g'ri"):
        apply_late_penalty(points, percent)


# --- ACC-10: mustaqil topshiriq muddati ---


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_acc_10_independent_policy_with_late_hours() -> None:
    section, _ = _setup(late_hours=1)
    deadline = IndependentDeadline.objects.create(section=section, assignment="A01", due_at=CLOSE)
    assert (
        independent_policy(section, deadline, CLOSE - timedelta(seconds=1))
        == SubmissionStatus.ON_TIME
    )
    assert independent_policy(section, deadline, CLOSE) == SubmissionStatus.LATE
    assert (
        independent_policy(section, deadline, CLOSE + timedelta(hours=1)) == SubmissionStatus.CLOSED
    )
    assert independent_policy(section, None, CLOSE) == SubmissionStatus.ON_TIME  # muddat yo'q


@pytest.mark.parametrize("code", ["", "B01", "A1", "A100", "a01"])
def test_acc_10_assignment_code_format_at_db_level(code: str) -> None:
    section, _ = _setup()
    # A100 — uzunlik (DataError), qolganlari — format CHECK (IntegrityError).
    with pytest.raises((IntegrityError, DataError)), transaction.atomic():
        IndependentDeadline.objects.bulk_create(
            [IndependentDeadline(section=section, assignment=code, due_at=CLOSE)]
        )


def test_acc_10_instructor_sets_and_clears_deadline_audited() -> None:
    section, _ = _setup()
    client = _client(section.instructor)
    url = f"/api/sections/{section.pk}/deadlines/A01"
    response = client.put(url, {"due_at": "2026-12-01T11:20:00+05:00"}, format="json")
    assert response.status_code == 200, response.json()
    assert IndependentDeadline.objects.get().due_at == CLOSE
    listed = client.get(f"/api/sections/{section.pk}/deadlines").json()
    assert [d["assignment"] for d in listed["deadlines"]] == ["A01"]
    assert client.delete(url).status_code == 204
    assert not IndependentDeadline.objects.exists()
    entries = AuditLog.objects.filter(action=Action.DEADLINE_CHANGED).order_by("id")
    assert [e.after for e in entries] == [{"due_at": CLOSE.isoformat()}, {"due_at": None}]


def test_acc_10_invalid_code_404_and_bad_date_400() -> None:
    section, _ = _setup()
    client = _client(section.instructor)
    bad = client.put(
        f"/api/sections/{section.pk}/deadlines/X1",
        {"due_at": "2026-12-01T10:00:00Z"},
        format="json",
    )
    assert bad.status_code == 404
    bad_date = client.put(
        f"/api/sections/{section.pk}/deadlines/A01", {"due_at": "ertaga"}, format="json"
    )
    assert bad_date.status_code == 400


def test_acc_10_foreign_instructor_404_student_403() -> None:
    section, _ = _setup()
    url = f"/api/sections/{section.pk}/deadlines/A01"
    payload = {"due_at": "2026-12-01T10:00:00+05:00"}
    assert _client(make_instructor()).put(url, payload, format="json").status_code == 404
    assert _client(make_user()).put(url, payload, format="json").status_code == 403


def test_acc_10_student_sees_own_section_deadlines_only() -> None:
    section, _ = _setup()
    IndependentDeadline.objects.create(section=section, assignment="A02", due_at=CLOSE)
    other = make_section()
    IndependentDeadline.objects.create(section=other, assignment="A03", due_at=CLOSE)
    membership: Membership = make_membership(section=section)
    student_client = _client(membership.student)
    assert student_client.get("/api/me/deadlines").json() == {"deadlines": []}  # hali pending
    membership.status = MembershipStatus.APPROVED
    membership.decided_at = membership.requested_at
    membership.decided_by = section.instructor
    membership.save()
    body = student_client.get("/api/me/deadlines").json()
    assert [d["assignment"] for d in body["deadlines"]] == ["A02"]
