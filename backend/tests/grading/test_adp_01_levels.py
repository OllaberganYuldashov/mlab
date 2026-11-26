"""ADP-01, ADP-02 (I3-10): moslashuvchan daraja — qoida, qotirish va o'qituvchi o'zgartirishi."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import Action, AuditLog
from apps.courses.content import ContentError, _parse_defaults
from apps.courses.models import QuizAttempt, Topic
from apps.grading import levels, variants
from apps.grading.models import (
    Assignment,
    Level,
    LevelSource,
    StudentAssignment,
    Submission,
    SubmissionPolicy,
    SubmissionStatus,
)
from apps.sections.models import Membership
from tests.accounts.factories import make_user
from tests.grading.test_agr_02_submit_api import _peer, _post, membership  # noqa: F401
from tests.grading.test_agr_07_assignment_import import content  # noqa: F401  (fixture)
from tests.labs.test_lab_05_autosave import _client
from tests.sections.factories import make_instructor

pytestmark = pytest.mark.django_db

D = Decimal


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


# --- Sof qoida ---


@pytest.mark.parametrize(
    ("quiz", "prior", "expected"),
    [
        (None, [], Level.BASIC),  # signal yo'q
        (D("59.99"), [], Level.BASIC),
        (D("60"), [], Level.MEDIUM),  # chegarada — yuqori daraja
        (D("84.99"), [], Level.MEDIUM),
        (D("85"), [], Level.ADVANCED),
        (None, [D("90"), D("80")], Level.ADVANCED),  # o'rtacha 85
        (D("100"), [D("30"), D("40")], Level.MEDIUM),  # (100 + 35) / 2 = 67.5
        (D("20"), [D("100")], Level.MEDIUM),  # 60
    ],
)
def test_adp_01_choose_level(quiz: Decimal | None, prior: list[Decimal], expected: Level) -> None:
    assert levels.choose_level(quiz, prior, 60, 85) == expected


def test_adp_01_thresholds_are_parameters() -> None:
    assert levels.choose_level(D("50"), [], 40, 90) == Level.MEDIUM
    assert levels.choose_level(D("50"), [], 50, 50) == Level.ADVANCED


def test_adp_01_course_defaults_validated() -> None:
    assert _parse_defaults({"level_medium_from": 50, "level_advanced_from": 70}, 1) == {
        "level_medium_from": 50,
        "level_advanced_from": 70,
    }
    for bad in (
        {"level_medium_from": 90},
        {"level_advanced_from": 101},
        {"level_medium_from": True},
    ):
        with pytest.raises(ContentError):
            _parse_defaults(bad, 1)


# --- Ma'lumotlardan qoida ---


def _quiz(student: User, topic: Topic, score: int, total: int = 10, number: int = 1) -> None:
    now = timezone.now()
    QuizAttempt.objects.create(
        student=student,
        topic=topic,
        number=number,
        deadline=now + timedelta(minutes=15),
        submitted_at=now,
        score=score,
        max_score=total,
    )


def _assignment() -> Assignment:
    return Assignment.objects.get(code="A01")


def test_adp_01_first_open_uses_quiz_and_level_is_frozen(membership: Membership) -> None:  # noqa: F811
    topic = Topic.objects.get(course=membership.section.course, code="M01")
    _quiz(membership.student, topic, 6)
    _quiz(membership.student, topic, 9, number=2)  # eng yaxshisi — 90%
    body = _client(membership.student).get("/api/labs/M01/assignment").json()
    assert body["level"] == "advanced"
    record = StudentAssignment.objects.get()
    assert (record.level, record.level_source) == (Level.ADVANCED, LevelSource.RULE)
    assert record.variant.level == Level.ADVANCED
    # Keyin natijalar o'zgarsa ham daraja qotirilgan.
    QuizAttempt.objects.update(score=1)
    assert _client(membership.student).get("/api/labs/M01/assignment").json()["level"] == "advanced"


def test_adp_01_unsubmitted_quiz_and_other_course_ignored(membership: Membership) -> None:  # noqa: F811
    topic = Topic.objects.get(course=membership.section.course, code="M01")
    QuizAttempt.objects.create(
        student=membership.student,
        topic=topic,
        number=1,
        deadline=timezone.now() + timedelta(minutes=15),
        max_score=10,
    )
    assert levels.quiz_percent(membership.student, _assignment()) is None
    assert variants.assign(membership.student, _assignment()).level == Level.BASIC


def _done(record: StudentAssignment, final: str, policy: str = SubmissionPolicy.ON_TIME) -> None:
    Submission.objects.create(
        student_assignment=record,
        code="x",
        status=SubmissionStatus.DONE,
        score=int(D(final)),
        final_score=D(final),
        result={"status": "ok", "tests": []},
        finished_at=timezone.now(),
        started_at=timezone.now(),
        policy=policy,
    )


def test_adp_01_prior_scores_best_official_per_assignment(membership: Membership) -> None:  # noqa: F811
    first = variants.assign(membership.student, _assignment(), Level.BASIC)
    _done(first, "50.00")
    _done(first, "70.00")
    _done(first, "100.00", policy=SubmissionPolicy.PRACTICE)  # mashq — hisobga kirmaydi
    later = Assignment.objects.create(
        course=membership.section.course, code="A02", title="T", topic_code="M02", statement="s"
    )
    assert levels.prior_scores(membership.student, later) == [D("70.00")]
    assert levels.prior_scores(membership.student, _assignment()) == []  # o'zidan oldingi yo'q
    peer = _peer(membership)
    assert levels.prior_scores(peer.student, later) == []  # boshqa talabaniki emas


# --- O'qituvchi o'zgartirishi (ADP-02) ---


def _url(membership: Membership, student_id: int | None = None) -> str:  # noqa: F811
    sid, student = membership.section.pk, student_id or membership.student.pk
    return f"/api/sections/{sid}/labs/M01/students/{student}/level"


def _put(client: Any, url: str, level: Any) -> Any:
    return client.put(url, {"level": level}, format="json")


def test_adp_02_instructor_changes_level_new_variant_and_audit(membership: Membership) -> None:  # noqa: F811
    record = variants.assign(membership.student, _assignment(), Level.BASIC)
    teacher = membership.section.instructor
    response = _put(_client(teacher), _url(membership), "medium")
    assert response.status_code == 200
    assert response.json() == {"level": "medium", "level_source": "instructor", "changed": True}
    record.refresh_from_db()
    assert (record.level, record.variant.level) == (Level.MEDIUM, Level.MEDIUM)
    expected = variants.pick_index(membership.student.pk, "A01", "medium", 5) + 1
    assert record.variant.number == expected
    log = AuditLog.objects.get(action=Action.LEVEL_CHANGED)
    assert log.actor_id == teacher.pk
    assert log.before["level"] == "basic"
    assert log.after == {"level": "medium", "variant": expected}
    # Talaba o'z sahifasida yangi darajani ko'radi.
    assert _client(membership.student).get("/api/labs/M01/assignment").json()["level"] == "medium"
    # Takror — o'zgarish yo'q, audit ham yo'q.
    again = _put(_client(teacher), _url(membership), "medium").json()
    assert again["changed"] is False
    assert AuditLog.objects.filter(action=Action.LEVEL_CHANGED).count() == 1


def test_adp_02_set_before_first_open_and_confirm_rule_level(membership: Membership) -> None:  # noqa: F811
    teacher = _client(membership.section.instructor)
    assert _put(teacher, _url(membership), "advanced").json()["changed"] is True
    record = StudentAssignment.objects.get()
    assert (record.level, record.level_source) == (Level.ADVANCED, LevelSource.INSTRUCTOR)
    assert AuditLog.objects.get(action=Action.LEVEL_CHANGED).before == {}
    peer = _peer(membership)
    variants.assign(peer.student, _assignment())  # qoida: basic
    confirmed = _put(teacher, _url(membership, peer.student.pk), "basic").json()
    assert confirmed == {"level": "basic", "level_source": "instructor", "changed": False}


def test_adp_02_open_submission_blocks_change(membership: Membership) -> None:  # noqa: F811
    _post(membership)  # navbatda
    response = _put(_client(membership.section.instructor), _url(membership), "advanced")
    assert (response.status_code, response.json()["code"]) == (409, "submission_pending")
    assert StudentAssignment.objects.get().level == Level.BASIC


def test_adp_02_permissions_and_validation(membership: Membership) -> None:  # noqa: F811
    assert _put(_client(make_instructor()), _url(membership), "medium").status_code == 404
    assert _put(_client(membership.student), _url(membership), "medium").status_code == 403
    teacher = _client(membership.section.instructor)
    assert _put(teacher, _url(membership, make_user().pk), "medium").status_code == 404
    assert _put(teacher, _url(membership), "expert").status_code == 400
    assert _put(teacher, _url(membership), None).status_code == 400
    assert StudentAssignment.objects.count() == 0
    assert not AuditLog.objects.filter(action=Action.LEVEL_CHANGED).exists()
