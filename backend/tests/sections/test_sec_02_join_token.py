"""SEC-02 (I1-03): qo'shilish tokeni — yangilash (eskisi bekor), o'chirish, faqat xesh saqlanadi."""

from __future__ import annotations

import hashlib

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.audit.models import Action, AuditLog
from apps.sections.models import Section
from apps.sections.tokens import find_section_by_token
from tests.accounts.factories import make_user
from tests.sections.factories import make_instructor, make_section

pytestmark = pytest.mark.django_db


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _url(section: Section) -> str:
    return f"/api/sections/{section.pk}/join-token"


def test_sec_02_rotate_returns_token_once_and_stores_only_hash() -> None:
    section = make_section()
    response = _client(section.instructor).post(_url(section))
    assert response.status_code == 201
    assert "no-store" in response["Cache-Control"]
    body = response.json()
    token = body["token"]
    assert len(token) >= 22  # >= 128 bit
    assert body["join_path"] == f"/join/{token}"
    section.refresh_from_db()
    assert section.join_token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in str(Section.objects.filter(pk=section.pk).values().get())
    assert find_section_by_token(token) == section


def test_sec_02_rotation_invalidates_previous_token() -> None:
    section = make_section()
    client = _client(section.instructor)
    old = client.post(_url(section)).json()["token"]
    new = client.post(_url(section)).json()["token"]
    assert old != new
    assert find_section_by_token(old) is None
    assert find_section_by_token(new) == section


def test_sec_02_disable_removes_token() -> None:
    section = make_section()
    client = _client(section.instructor)
    token = client.post(_url(section)).json()["token"]
    assert client.delete(_url(section)).status_code == 204
    assert find_section_by_token(token) is None
    section.refresh_from_db()
    assert section.join_token_hash is None


@pytest.mark.parametrize("token", ["", "x", "a" * 500, "../etc", "ok\x00"])
def test_sec_02_garbage_tokens_find_nothing(token: str) -> None:
    make_section()
    assert find_section_by_token(token) is None


def test_sec_02_foreign_instructor_gets_404() -> None:
    section = make_section()
    client = _client(make_instructor())
    assert client.post(_url(section)).status_code == 404
    assert client.delete(_url(section)).status_code == 404
    section.refresh_from_db()
    assert section.join_token_hash is None


def test_sec_02_student_forbidden() -> None:
    section = make_section()
    assert _client(make_user()).post(_url(section)).status_code == 403


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPER_ADMIN])
def test_sec_02_staff_can_rotate_any(role: Role) -> None:
    section = make_section()
    staff = make_user(role=role, direction=None, is_superuser=role == Role.SUPER_ADMIN)
    assert _client(staff).post(_url(section)).status_code == 201


def test_sec_02_audited_without_token() -> None:
    section = make_section()
    client = _client(section.instructor)
    token = client.post(_url(section)).json()["token"]
    client.delete(_url(section))
    rotated = AuditLog.objects.get(action=Action.JOIN_TOKEN_ROTATED)
    disabled = AuditLog.objects.get(action=Action.JOIN_TOKEN_DISABLED)
    for entry in (rotated, disabled):
        assert entry.actor == section.instructor
        assert token not in str(entry.before) + str(entry.after)


def test_sec_02_section_payload_shows_only_whether_link_exists() -> None:
    section = make_section()
    client = _client(section.instructor)
    assert client.get(f"/api/sections/{section.pk}").json()["has_join_token"] is False
    client.post(_url(section))
    body = client.get(f"/api/sections/{section.pk}").json()
    assert body["has_join_token"] is True
    assert "join_token_hash" not in body
