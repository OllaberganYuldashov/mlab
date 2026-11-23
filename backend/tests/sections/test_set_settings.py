"""SET-01..05 (I1-07): kurs default → guruh override; AI tutorni darhol o'chirish."""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.audit.models import Action, AuditLog
from apps.courses.models import AiMode
from apps.sections.models import Section
from apps.sections.settings import effective_ai_mode, effective_settings
from tests.accounts.factories import make_user
from tests.sections.factories import make_instructor, make_section

pytestmark = pytest.mark.django_db


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _url(section: Section, tail: str = "settings") -> str:
    return f"/api/sections/{section.pk}/{tail}"


# --- effective_settings ---


def test_set_effective_uses_course_defaults_when_not_overridden() -> None:
    section = make_section()
    course = section.course
    course.late_hours = 12
    course.save()
    eff = effective_settings(section)
    assert eff.late_hours == 12
    assert eff.ai_enabled is True
    assert eff.ai_max_mode == AiMode.EXPLAIN
    assert eff.chat_enabled is True


def test_set_section_override_wins_and_null_falls_back() -> None:
    section = make_section(late_hours=2, chat_enabled=False)
    eff = effective_settings(section)
    assert (eff.late_hours, eff.chat_enabled) == (2, False)
    section.late_hours = None
    section.save()
    assert effective_settings(section).late_hours == section.course.late_hours


@pytest.mark.parametrize(
    ("task_mode", "cap", "enabled", "expected"),
    [
        (AiMode.FULL, AiMode.EXPLAIN, True, AiMode.EXPLAIN),  # SET-01: chegara amal qiladi
        (AiMode.GUIDE, AiMode.FULL, True, AiMode.GUIDE),
        (AiMode.FULL, AiMode.FULL, False, AiMode.OFF),  # o'chirilgan
        (AiMode.OFF, AiMode.FULL, True, AiMode.OFF),
    ],
)
def test_set_01_task_mode_capped_by_section(
    task_mode: AiMode, cap: AiMode, enabled: bool, expected: AiMode
) -> None:
    section = make_section(ai_max_mode=cap, ai_enabled=enabled)
    assert effective_ai_mode(section, task_mode) == expected


# --- API ---


def test_set_get_settings_shows_defaults_overrides_effective() -> None:
    section = make_section(late_hours=5)
    body = _client(section.instructor).get(_url(section)).json()
    assert body["overrides"]["late_hours"] == 5
    assert body["overrides"]["chat_enabled"] is None
    assert body["course_defaults"]["late_hours"] == 0
    assert body["effective"]["late_hours"] == 5
    assert body["effective"]["chat_enabled"] is True


def test_set_patch_override_and_clear_audited() -> None:
    section = make_section()
    client = _client(section.instructor)
    response = client.patch(
        _url(section), {"ai_max_mode": "guide", "practice_after_close": True}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["effective"]["ai_max_mode"] == "guide"
    entry = AuditLog.objects.get(action=Action.SECTION_SETTINGS_CHANGED)
    assert entry.before == {"ai_max_mode": None, "practice_after_close": None}
    assert entry.after == {"ai_max_mode": "guide", "practice_after_close": True}
    cleared = client.patch(_url(section), {"ai_max_mode": None}, format="json").json()
    assert cleared["overrides"]["ai_max_mode"] is None
    assert cleared["effective"]["ai_max_mode"] == "explain"


@pytest.mark.parametrize(
    "payload",
    [{"ai_max_mode": "magic"}, {"late_hours": 500}, {"late_hours": -1}, {"chat_enabled": "x"}],
)
def test_set_invalid_values_rejected(payload: dict[str, Any]) -> None:
    section = make_section()
    assert (
        _client(section.instructor).patch(_url(section), payload, format="json").status_code == 400
    )


def test_set_late_penalty_is_course_level_only() -> None:
    section = make_section()
    _client(section.instructor).patch(_url(section), {"late_penalty_percent": 50}, format="json")
    body = _client(section.instructor).get(_url(section)).json()
    assert "late_penalty_percent" not in body["overrides"]
    assert body["effective"]["late_penalty_percent"] == 0


def test_set_foreign_instructor_404_student_403() -> None:
    section = make_section()
    stranger = _client(make_instructor())
    assert stranger.get(_url(section)).status_code == 404
    assert stranger.patch(_url(section), {"chat_enabled": False}, format="json").status_code == 404
    assert stranger.post(_url(section, "ai/disable")).status_code == 404
    assert _client(make_user()).get(_url(section)).status_code == 403


# --- SET-02: bir tugma ---


def test_set_02_ai_disable_and_enable_immediately() -> None:
    section = make_section()
    client = _client(section.instructor)
    response = client.post(_url(section, "ai/disable"))
    assert response.status_code == 200
    assert response.json()["effective"]["ai_enabled"] is False
    section.refresh_from_db()
    assert effective_ai_mode(section, AiMode.FULL) == AiMode.OFF
    client.post(_url(section, "ai/enable"))
    section.refresh_from_db()
    assert effective_settings(section).ai_enabled is True
    actions = list(
        AuditLog.objects.filter(action=Action.SECTION_SETTINGS_CHANGED).values_list(
            "after", flat=True
        )
    )
    assert actions == [{"ai_enabled": False}, {"ai_enabled": True}]


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPER_ADMIN])
def test_set_02_staff_can_disable_ai(role: Role) -> None:
    section = make_section()
    staff = make_user(role=role, direction=None, is_superuser=role == Role.SUPER_ADMIN)
    assert _client(staff).post(_url(section, "ai/disable")).status_code == 200
