"""AGR-02, AGR-04, ACC-06, ACC-07 (I3-07): "Topshirish" API, navbatdagi o'rin, real vaqt xabari."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from apps.courses.models import Topic
from apps.grading import service
from apps.grading.content import import_labs
from apps.grading.models import Assignment, Submission
from apps.grading.sandbox import fake
from apps.sections.models import AccessWindow, Membership, WindowMode
from tests.accounts.factories import make_user
from tests.grading.test_agr_07_assignment_import import content  # noqa: F401  (fixture)
from tests.labs.test_lab_05_autosave import _approved, _client

pytestmark = pytest.mark.django_db

URL = "/api/labs/M01/submissions"


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    cache.clear()
    fake.responses.clear()
    fake.calls.clear()
    yield
    cache.clear()


@pytest.fixture
def events(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, dict[str, Any]]]:
    sent: list[tuple[int, dict[str, Any]]] = []
    monkeypatch.setattr(service, "user_event", lambda uid, msg: sent.append((uid, msg)))
    return sent


@pytest.fixture
def membership(content: Path) -> Membership:  # noqa: F811
    membership = _approved()
    Topic.objects.create(course=membership.section.course, code="M02", title="T2", order=2)
    import_labs(content, membership.section.course)
    Assignment.objects.update(topic_code="M01")
    return membership


def _post(membership: Membership, code: str = "df = 1") -> Any:
    return _client(membership.student).post(URL, {"code": code}, format="json")


def _peer(membership: Membership) -> Membership:
    """Shu guruhdagi boshqa talaba (oyna ochiq)."""
    other = _approved(open_window=False, course=membership.section.course)
    other.section = membership.section
    other.save(update_fields=["section"])
    return other


def test_agr_02_submit_queues_with_position_and_policy(
    membership: Membership, django_capture_on_commit_callbacks: Any
) -> None:
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        response = _post(membership)
    assert response.status_code == 202
    body = response.json()
    assert (body["status"], body["position"], body["policy"]) == ("queued", 1, "on_time")
    assert body["score"] is None
    assert body["final_score"] is None
    submission = Submission.objects.get()
    assert submission.code == "df = 1"
    assert submission.student_assignment.student_id == membership.student.pk
    assert len(callbacks) >= 1  # Celery vazifasi faqat commit'dan keyin


def test_agr_02_second_submit_while_open_is_409(membership: Membership) -> None:
    assert _post(membership).status_code == 202
    second = _post(membership, "df = 2")
    assert (second.status_code, second.json()["code"]) == (409, "submission_pending")
    service.grade(Submission.objects.get().pk)
    assert _post(membership, "df = 3").status_code == 202  # oldingisi tugagach — mumkin
    assert Submission.objects.count() == 2


@pytest.mark.parametrize("payload", [{}, {"code": ""}, {"code": 5}, {"code": "x" * 200_001}])
def test_agr_02_invalid_code_is_400(membership: Membership, payload: dict[str, Any]) -> None:
    response = _client(membership.student).post(URL, payload, format="json")
    assert response.status_code == 400
    assert Submission.objects.count() == 0


def test_acc_06_closed_lab_and_missing_assignment(membership: Membership) -> None:
    AccessWindow.objects.all().delete()
    closed = _post(membership)
    assert (closed.status_code, closed.json()["code"]) == (403, "lab_closed")
    other = _approved(course=membership.section.course)
    Assignment.objects.update(topic_code="M02")
    missing = _post(other)
    assert (missing.status_code, missing.json()["code"]) == (404, "no_assignment")
    assert Submission.objects.count() == 0


def _close_window(membership: Membership, *, late_hours: int = 0, practice: bool = False) -> None:
    now = timezone.now()
    AccessWindow.objects.filter(section=membership.section).update(
        mode=WindowMode.SCHEDULED,
        opens_at=now - timedelta(hours=2),
        closes_at=now - timedelta(minutes=1),
    )
    section = membership.section
    section.late_hours = late_hours
    section.practice_after_close = practice
    section.save(update_fields=["late_hours", "practice_after_close"])


def test_acc_07_late_submission_gets_penalty_snapshot(membership: Membership) -> None:
    course = membership.section.course
    course.late_penalty_percent = 30
    course.save(update_fields=["late_penalty_percent"])
    _close_window(membership, late_hours=2)
    body = _post(membership).json()
    assert body["policy"] == "late"
    # Keyin kurs sozlamasi o'zgarsa ham topshirish paytidagi foiz ishlatiladi.
    course.late_penalty_percent = 90
    course.save(update_fields=["late_penalty_percent"])
    service.grade(body["id"])
    submission = Submission.objects.get()
    assert (submission.score, submission.penalty_percent) == (100, 30)
    assert submission.final_score == Decimal("70.00")
    assert (
        _client(membership.student).get(f"/api/submissions/{body['id']}").json()["final_score"]
        == "70.00"
    )


def test_acc_08_practice_after_close_is_not_official_and_no_penalty(
    membership: Membership,
) -> None:
    course = membership.section.course
    course.late_penalty_percent = 30
    course.save(update_fields=["late_penalty_percent"])
    _close_window(membership, late_hours=0, practice=True)
    body = _post(membership).json()
    assert body["policy"] == "practice"
    service.grade(body["id"])
    submission = Submission.objects.get()
    assert (submission.penalty_percent, submission.final_score) == (0, Decimal("100.00"))


def test_agr_04_position_moves_when_queue_advances(membership: Membership) -> None:
    first = _post(membership).json()
    peer = _peer(membership)
    second = _post(peer).json()
    assert second["position"] == 2
    service._claim(first["id"])  # birinchisi tekshirilmoqda
    again = _client(peer.student).get(f"/api/submissions/{second['id']}").json()
    assert (again["status"], again["position"]) == ("queued", 1)
    mine = _client(membership.student).get(f"/api/submissions/{first['id']}").json()
    assert (mine["status"], mine["position"]) == ("running", 0)


def test_agr_04_status_events_go_to_owner_only(
    membership: Membership,
    events: list[tuple[int, dict[str, Any]]],
) -> None:
    first = _post(membership).json()
    peer = _peer(membership)
    second = _post(peer).json()
    events.clear()
    service.grade(first["id"])
    owner = membership.student.pk
    mine = [m for uid, m in events if uid == owner]
    theirs = [m for uid, m in events if uid == peer.student.pk]
    assert [m["status"] for m in mine] == ["running", "done"]
    assert all(m["type"] == "submission.status" and m["id"] == first["id"] for m in mine)
    assert mine[-1]["final_score"] == "100.00"
    # Navbat siljidi — ikkinchi talabaga yangi o'rin; boshqa birovning bahosi unga bormaydi.
    assert theirs == [
        {
            "type": "submission.status",
            "id": second["id"],
            "status": "queued",
            "position": 1,
            "policy": "on_time",
            "score": None,
            "final_score": None,
        }
    ]
    assert all("result" not in m and "code" not in m for _, m in events)


def test_agr_04_retry_and_error_are_notified(
    membership: Membership, events: list[tuple[int, dict[str, Any]]]
) -> None:
    from apps.grading.sandbox import SandboxUnavailable

    fake.responses.extend(SandboxUnavailable("down") for _ in range(service.MAX_ATTEMPTS))
    sid = _post(membership).json()["id"]
    events.clear()
    for _ in range(service.MAX_ATTEMPTS - 1):
        with pytest.raises(service.RetryLater):
            service.grade(sid)
    service.grade(sid)
    assert [m["status"] for _, m in events] == ["running", "queued"] * 2 + ["running", "error"]


def test_agr_04_list_and_detail_are_own_only(membership: Membership) -> None:
    first = _post(membership).json()
    service.grade(first["id"])
    second = _post(membership).json()
    listing = _client(membership.student).get(URL).json()["submissions"]
    assert [s["id"] for s in listing] == [second["id"], first["id"]]  # yangisi birinchi
    assert listing[1]["status"] == "done"
    assert listing[1]["finished_at"] is not None
    # IDOR: boshqa talaba (shu guruhda ham) begona urinishni ko'rmaydi; o'qituvchi — 403.
    peer = _peer(membership)
    assert _client(peer.student).get(f"/api/submissions/{first['id']}").status_code == 404
    assert _client(peer.student).get(URL).json()["submissions"] == []
    assert _client(make_user()).get(URL).status_code == 403  # guruhsiz
    instructor = _client(membership.section.instructor)
    assert instructor.get(f"/api/submissions/{first['id']}").status_code == 403
    assert instructor.post(URL, {"code": "x"}, format="json").status_code == 403
    assert _client(membership.student).get("/api/submissions/999999").status_code == 404


@override_settings(LAB_SUBMIT_RATE="2/min")
def test_agr_02_submit_is_rate_limited_per_student(membership: Membership) -> None:
    assert _post(membership).status_code == 202
    assert _post(membership).status_code == 409
    assert _post(membership).status_code == 429
    # GET cheklanmaydi (qayta ulanishda holatni olish).
    assert _client(membership.student).get(URL).status_code == 200


def test_agr_04_realtime_send_failure_does_not_break_submit(
    membership: Membership,
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: Any,
) -> None:
    from apps.sections import realtime

    def boom(*_: Any) -> None:
        raise ConnectionError("redis yo'q")

    monkeypatch.setattr(realtime, "_send", boom)
    monkeypatch.setattr(service, "_dispatch", lambda _pk: None)
    with django_capture_on_commit_callbacks(execute=True):
        response = _post(membership)
    assert response.status_code == 202
