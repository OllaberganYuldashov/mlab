"""ACC-04 (I1-09): haftalik slot bo'yicha mavzularni ketma-ket oynalarga joylashtirish."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import Action, AuditLog
from apps.courses.models import Topic
from apps.sections.models import AccessWindow, Section, WindowMode
from apps.sections.planning import Slot, plan_slots
from tests.accounts.factories import make_user
from tests.sections.factories import make_instructor, make_section

TZ = ZoneInfo("Asia/Tashkent")
TUE, THU = 1, 3


def _dt(d: date, hh: int, mm: int = 0) -> datetime:
    return datetime.combine(d, time(hh, mm), tzinfo=TZ)


# --- plan_slots (sof funksiya) ---


def test_acc_04_weekly_slot_from_start_date_on_slot_day() -> None:
    start = date(2026, 12, 1)  # seshanba
    plan = plan_slots(3, [Slot(TUE, time(10, 0), 80)], start, TZ)
    assert plan == [
        (_dt(start, 10), _dt(start, 11, 20)),
        (_dt(start + timedelta(days=7), 10), _dt(start + timedelta(days=7), 11, 20)),
        (_dt(start + timedelta(days=14), 10), _dt(start + timedelta(days=14), 11, 20)),
    ]


def test_acc_04_two_slots_per_week_in_order() -> None:
    start = date(2026, 12, 2)  # chorshanba: birinchi slot payshanba
    plan = plan_slots(3, [Slot(TUE, time(10), 80), Slot(THU, time(14), 80)], start, TZ)
    assert [p[0] for p in plan] == [
        _dt(date(2026, 12, 3), 14),
        _dt(date(2026, 12, 8), 10),
        _dt(date(2026, 12, 10), 14),
    ]


def test_acc_04_crosses_year_boundary() -> None:
    plan = plan_slots(2, [Slot(TUE, time(10), 80)], date(2026, 12, 29), TZ)
    assert plan[1][0] == _dt(date(2027, 1, 5), 10)


def test_acc_04_zero_topics() -> None:
    assert plan_slots(0, [Slot(TUE, time(10), 80)], date(2026, 12, 1), TZ) == []


@pytest.mark.parametrize(
    "slots",
    [
        [],
        [Slot(7, time(10), 80)],
        [Slot(TUE, time(10), 0)],
        [Slot(TUE, time(10), 80), Slot(TUE, time(10), 80)],
        [Slot(TUE, time(10), 80), Slot(TUE, time(11), 80)],  # ustma-ust
    ],
)
def test_acc_04_invalid_slots_rejected(slots: list[Slot]) -> None:
    with pytest.raises(ValueError, match="slot"):
        plan_slots(1, slots, date(2026, 12, 1), TZ)


# --- API ---


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _section_with_topics(n: int) -> Section:
    section = make_section()
    for i in range(1, n + 1):
        Topic.objects.create(course=section.course, code=f"M{i:02d}", title=f"T{i}", order=i)
    return section


def _body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "slots": [{"weekday": TUE, "time": "10:00", "minutes": 80}],
        "start_date": "2026-12-01",
        "preview": True,
    }
    body.update(overrides)
    return body


@pytest.mark.django_db
def test_acc_04_preview_does_not_save() -> None:
    section = _section_with_topics(3)
    response = _client(section.instructor).post(
        f"/api/sections/{section.pk}/windows/plan", _body(), format="json"
    )
    assert response.status_code == 200, response.json()
    plan = response.json()["plan"]
    assert [p["topic"] for p in plan] == ["M01", "M02", "M03"]
    assert plan[0]["opens_at"].startswith("2026-12-01T10:00:00+05:00")
    assert not AccessWindow.objects.exists()


@pytest.mark.django_db
def test_acc_04_apply_saves_scheduled_windows_and_audits() -> None:
    section = _section_with_topics(2)
    response = _client(section.instructor).post(
        f"/api/sections/{section.pk}/windows/plan", _body(preview=False), format="json"
    )
    assert response.status_code == 200
    windows = list(AccessWindow.objects.order_by("opens_at"))
    assert [w.mode for w in windows] == [WindowMode.SCHEDULED] * 2
    assert windows[1].opens_at == _dt(date(2026, 12, 8), 10)
    assert AuditLog.objects.filter(action=Action.ACCESS_WINDOW_CHANGED).count() == 2


@pytest.mark.django_db
def test_acc_04_subset_of_topics_in_given_order() -> None:
    section = _section_with_topics(3)
    body = _body(topics=["M03", "M01"])
    plan = (
        _client(section.instructor)
        .post(f"/api/sections/{section.pk}/windows/plan", body, format="json")
        .json()["plan"]
    )
    assert [p["topic"] for p in plan] == ["M03", "M01"]


@pytest.mark.django_db
def test_acc_04_existing_windows_need_overwrite_flag() -> None:
    section = _section_with_topics(2)
    client = _client(section.instructor)
    client.post(f"/api/sections/{section.pk}/windows/M01/open-now", {}, format="json")
    url = f"/api/sections/{section.pk}/windows/plan"
    refused = client.post(url, _body(preview=False), format="json")
    assert refused.status_code == 409
    assert refused.json()["topics"] == ["M01"]
    assert AccessWindow.objects.get().mode == WindowMode.OPEN_NOW
    ok = client.post(url, _body(preview=False, overwrite=True), format="json")
    assert ok.status_code == 200
    assert set(AccessWindow.objects.values_list("mode", flat=True)) == {WindowMode.SCHEDULED}


@pytest.mark.django_db
def test_acc_04_shift_one_window_leaves_others() -> None:
    section = _section_with_topics(2)
    client = _client(section.instructor)
    client.post(f"/api/sections/{section.pk}/windows/plan", _body(preview=False), format="json")
    client.put(
        f"/api/sections/{section.pk}/windows/M01",
        {
            "mode": "scheduled",
            "opens_at": "2026-12-02T10:00:00+05:00",
            "closes_at": "2026-12-02T11:20:00+05:00",
        },
        format="json",
    )
    second = AccessWindow.objects.get(topic__code="M02")
    assert second.opens_at == _dt(date(2026, 12, 8), 10)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "overrides",
    [
        {"slots": []},
        {"slots": [{"weekday": 9, "time": "10:00", "minutes": 80}]},
        {"topics": ["M99"]},
        {"topics": ["M01", "M01"]},
        {"start_date": "bugun"},
    ],
)
def test_acc_04_invalid_requests_rejected(overrides: dict[str, Any]) -> None:
    section = _section_with_topics(2)
    response = _client(section.instructor).post(
        f"/api/sections/{section.pk}/windows/plan", _body(**overrides), format="json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_acc_04_foreign_instructor_404_student_403() -> None:
    section = _section_with_topics(1)
    url = f"/api/sections/{section.pk}/windows/plan"
    assert _client(make_instructor()).post(url, _body(), format="json").status_code == 404
    assert _client(make_user()).post(url, _body(), format="json").status_code == 403
