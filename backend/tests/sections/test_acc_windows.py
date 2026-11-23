"""ACC-01..03, ACC-09, ACC-11 (I1-08): kirish oynalari — model, holat va o'qituvchi API."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import Action, AuditLog
from apps.courses.models import Topic
from apps.sections.models import AccessWindow, Section, WindowMode
from apps.sections.windows import MaterialKind, material_always_open, window_state
from tests.accounts.factories import make_user
from tests.sections.factories import make_instructor, make_section

pytestmark = pytest.mark.django_db
TZ = ZoneInfo("Asia/Tashkent")
T0 = datetime(2026, 12, 1, 10, 0, tzinfo=TZ)


def _topic(section: Section, code: str = "M01", order: int = 1) -> Topic:
    return Topic.objects.create(
        course=section.course, code=code, title=f"Mavzu {code}", order=order
    )


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _window(section: Section, topic: Topic, **fields: Any) -> AccessWindow:
    return AccessWindow.objects.create(section=section, topic=topic, **fields)


# --- ACC-01, ACC-02 ---


@pytest.mark.parametrize(
    "kind", [MaterialKind.LECTURE, MaterialKind.QUIZ, MaterialKind.INDEPENDENT]
)
def test_acc_01_lectures_quizzes_independent_always_open(kind: MaterialKind) -> None:
    assert material_always_open(kind) is True


def test_acc_01_lab_is_not_always_open() -> None:
    assert material_always_open(MaterialKind.LAB) is False


def test_acc_02_no_window_means_closed() -> None:
    assert window_state(None, T0).status == "closed"


# --- window_state (sof funksiya, chegaralar) ---


def _w(mode: WindowMode, opens: datetime | None = None, closes: datetime | None = None) -> Any:
    return AccessWindow(mode=mode, opens_at=opens, closes_at=closes)


def test_acc_03_closed_mode() -> None:
    assert window_state(_w(WindowMode.CLOSED), T0).status == "closed"


def test_acc_03_open_now_without_end_stays_open() -> None:
    state = window_state(_w(WindowMode.OPEN_NOW, opens=T0), T0 + timedelta(days=30))
    assert state.status == "open"
    assert state.seconds_left is None


def test_acc_03_open_now_with_minutes_closes_exactly_at_end() -> None:
    w = _w(WindowMode.OPEN_NOW, opens=T0, closes=T0 + timedelta(minutes=80))
    assert window_state(w, T0 + timedelta(minutes=79, seconds=59)).status == "open"
    assert window_state(w, T0 + timedelta(minutes=80)).status == "closed"


def test_acc_03_scheduled_upcoming_open_closed_boundaries() -> None:
    w = _w(WindowMode.SCHEDULED, opens=T0, closes=T0 + timedelta(minutes=80))
    before = window_state(w, T0 - timedelta(seconds=1))
    assert before.status == "upcoming"
    assert before.seconds_until_open == 1
    at_open = window_state(w, T0)
    assert at_open.status == "open"
    assert at_open.seconds_left == 80 * 60
    assert window_state(w, T0 + timedelta(minutes=80)).status == "closed"


def test_acc_03_state_is_timezone_independent() -> None:
    w = _w(WindowMode.SCHEDULED, opens=T0, closes=T0 + timedelta(hours=1))
    utc_moment = T0.astimezone(ZoneInfo("UTC"))
    assert window_state(w, utc_moment).status == "open"


# --- DB invariantlari ---


@pytest.mark.parametrize(
    "fields",
    [
        {"mode": WindowMode.SCHEDULED, "opens_at": T0, "closes_at": None},
        {"mode": WindowMode.SCHEDULED, "opens_at": T0, "closes_at": T0},
        {"mode": WindowMode.SCHEDULED, "opens_at": T0, "closes_at": T0 - timedelta(minutes=1)},
        {"mode": WindowMode.OPEN_NOW, "opens_at": None},
        {"mode": WindowMode.CLOSED, "opens_at": T0},
        {"mode": "maybe"},
    ],
)
def test_acc_03_invalid_windows_rejected_at_db_level(fields: dict[str, Any]) -> None:
    section = make_section()
    topic = _topic(section)
    with pytest.raises(IntegrityError), transaction.atomic():
        AccessWindow.objects.bulk_create([AccessWindow(section=section, topic=topic, **fields)])


def test_acc_02_one_window_per_section_topic() -> None:
    section = make_section()
    topic = _topic(section)
    _window(section, topic)
    with pytest.raises(IntegrityError), transaction.atomic():
        _window(section, topic)


def test_acc_02_topic_with_windows_cannot_be_deleted_by_import(tmp_path: Any) -> None:
    from apps.courses.content import ContentError, import_content

    root = tmp_path / "content"
    (root / "topics" / "M01-a").mkdir(parents=True)
    (root / "course.yaml").write_text('slug: k\ntitle: K\nversion: "1"\n', encoding="utf-8")
    (root / "topics" / "M01-a" / "meta.yaml").write_text("code: M01\ntitle: A\norder: 1\n")
    (root / "topics" / "M01-a" / "lecture.md").write_text("# A\n\n## Q\n\nMatn.\n")
    import_content(root)
    section = make_section(course=Topic.objects.get().course)
    _window(section, Topic.objects.get())
    (root / "topics" / "M01-a" / "meta.yaml").unlink()
    (root / "topics" / "M01-a" / "lecture.md").unlink()
    (root / "topics" / "M01-a").rmdir()
    with pytest.raises(ContentError, match="M01"):
        import_content(root)
    assert Topic.objects.filter(code="M01").exists()


# --- API ---


def _url(section: Section, tail: str = "") -> str:
    return f"/api/sections/{section.pk}/windows{tail}"


def test_acc_02_list_shows_every_topic_closed_by_default() -> None:
    section = make_section()
    _topic(section, "M01", 1)
    _topic(section, "M02", 2)
    body = _client(section.instructor).get(_url(section)).json()
    assert [w["topic"]["code"] for w in body["windows"]] == ["M01", "M02"]
    assert {w["state"]["status"] for w in body["windows"]} == {"closed"}
    assert "server_time" in body


def test_acc_03_put_schedule_and_audit() -> None:
    section = make_section()
    _topic(section)
    response = _client(section.instructor).put(
        _url(section, "/M01"),
        {
            "mode": "scheduled",
            "opens_at": "2026-12-01T10:00:00+05:00",
            "closes_at": "2026-12-01T11:20:00+05:00",
            "proctored": True,
        },
        format="json",
    )
    assert response.status_code == 200, response.json()
    window = AccessWindow.objects.get()
    assert window.opens_at == T0
    assert window.proctored is True
    entry = AuditLog.objects.get(action=Action.ACCESS_WINDOW_CHANGED)
    assert entry.before == {
        "mode": "closed",
        "opens_at": None,
        "closes_at": None,
        "proctored": False,
    }
    assert entry.after["mode"] == "scheduled"
    assert entry.after["opens_at"] == T0.isoformat()


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "scheduled", "opens_at": "2026-12-01T10:00:00+05:00"},
        {
            "mode": "scheduled",
            "opens_at": "2026-12-01T11:00:00+05:00",
            "closes_at": "2026-12-01T10:00:00+05:00",
        },
        {"mode": "magic"},
    ],
)
def test_acc_03_invalid_put_rejected(payload: dict[str, Any]) -> None:
    section = make_section()
    _topic(section)
    response = _client(section.instructor).put(_url(section, "/M01"), payload, format="json")
    assert response.status_code == 400
    assert not AccessWindow.objects.exists()


def test_acc_03_open_now_for_minutes_then_close() -> None:
    section = make_section()
    _topic(section)
    client = _client(section.instructor)
    response = client.post(_url(section, "/M01/open-now"), {"minutes": 80}, format="json")
    assert response.status_code == 200
    window = AccessWindow.objects.get()
    assert window.mode == WindowMode.OPEN_NOW
    assert window.closes_at is not None
    assert window.opens_at is not None
    assert abs((window.closes_at - window.opens_at) - timedelta(minutes=80)) < timedelta(seconds=1)
    assert window_state(window, timezone.now()).status == "open"
    client.post(_url(section, "/M01/close"))
    window.refresh_from_db()
    # Ochiq oyna yopilganda yopilish lahzasi saqlanadi (ACC-07 kechikish va ACC-08 mashq uchun).
    assert window.mode == WindowMode.OPEN_NOW
    assert window.closes_at is not None
    assert window.closes_at <= timezone.now()
    assert window_state(window, timezone.now()).status == "closed"
    assert AuditLog.objects.filter(action=Action.ACCESS_WINDOW_CHANGED).count() == 2


def test_acc_03_open_now_without_minutes_is_manual() -> None:
    section = make_section()
    _topic(section)
    _client(section.instructor).post(_url(section, "/M01/open-now"), {}, format="json")
    assert AccessWindow.objects.get().closes_at is None


@pytest.mark.parametrize("minutes", [0, -5, 100000])
def test_acc_03_open_now_invalid_minutes(minutes: int) -> None:
    section = make_section()
    _topic(section)
    response = _client(section.instructor).post(
        _url(section, "/M01/open-now"), {"minutes": minutes}, format="json"
    )
    assert response.status_code == 400


def test_acc_03_unknown_topic_404() -> None:
    section = make_section()
    response = _client(section.instructor).post(_url(section, "/M99/open-now"), {}, format="json")
    assert response.status_code == 404


def test_acc_11_foreign_instructor_404_student_403() -> None:
    section = make_section()
    _topic(section)
    stranger = _client(make_instructor())
    assert stranger.get(_url(section)).status_code == 404
    assert stranger.post(_url(section, "/M01/open-now"), {}, format="json").status_code == 404
    assert _client(make_user()).get(_url(section)).status_code == 403
    assert not AccessWindow.objects.exists()


def test_acc_11_unchanged_close_not_audited() -> None:
    section = make_section()
    _topic(section)
    _client(section.instructor).post(_url(section, "/M01/close"))
    assert not AuditLog.objects.filter(action=Action.ACCESS_WINDOW_CHANGED).exists()


def test_acc_03_closing_upcoming_window_resets_to_closed() -> None:
    section = make_section()
    topic = _topic(section)
    _window(
        section,
        topic,
        mode=WindowMode.SCHEDULED,
        opens_at=timezone.now() + timedelta(days=1),
        closes_at=timezone.now() + timedelta(days=1, hours=1),
    )
    _client(section.instructor).post(_url(section, "/M01/close"))
    assert AccessWindow.objects.get().mode == WindowMode.CLOSED
