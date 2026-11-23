"""AUTH-04, ADM-02 (R0-08): parolni tiklash, majburiy almashtirish, audit."""

from __future__ import annotations

import logging
import secrets
from typing import Any
from unittest import mock

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts import policies
from apps.accounts.models import Role, User
from apps.audit.models import Action, AuditLog
from tests.accounts.factories import make_user

pytestmark = pytest.mark.django_db

PASSWORD = secrets.token_urlsafe(12)
NEW_PASSWORD = secrets.token_urlsafe(12)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


def _staff(role: Role) -> User:
    return make_user(role=role, direction=None, is_superuser=role == Role.SUPER_ADMIN)


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _reset(actor: User, target: User) -> Any:
    return _client(actor).post(f"/api/users/{target.pk}/reset-password")


# --- Kim kimni tiklay oladi ---


@pytest.mark.parametrize(
    ("actor_role", "target_role", "expected"),
    [
        (Role.ADMIN, Role.STUDENT, 200),
        (Role.ADMIN, Role.INSTRUCTOR, 200),
        (Role.ADMIN, Role.ADMIN, 404),
        (Role.ADMIN, Role.SUPER_ADMIN, 404),
        (Role.SUPER_ADMIN, Role.ADMIN, 200),
        (Role.SUPER_ADMIN, Role.STUDENT, 200),
        (Role.SUPER_ADMIN, Role.SUPER_ADMIN, 404),
        (Role.INSTRUCTOR, Role.STUDENT, 404),  # guruh yo'q — o'z talabasi emas (IDOR)
        (Role.INSTRUCTOR, Role.INSTRUCTOR, 404),
        (Role.STUDENT, Role.STUDENT, 403),
    ],
)
def test_auth_04_reset_permission_matrix(
    actor_role: Role, target_role: Role, expected: int
) -> None:
    actor = _staff(actor_role) if actor_role != Role.STUDENT else make_user()
    target = _staff(target_role) if target_role != Role.STUDENT else make_user()
    assert _reset(actor, target).status_code == expected


def test_auth_04_instructor_resets_own_group_student() -> None:
    # I1 gacha "o'z guruhi" tekshiruvi `policies.instructor_teaches` orqali (hozir doim False).
    instructor = _staff(Role.INSTRUCTOR)
    student = make_user()
    with mock.patch.object(policies, "instructor_teaches", return_value=True) as teaches:
        assert _reset(instructor, student).status_code == 200
    teaches.assert_called_once_with(instructor, student)


def test_auth_04_instructor_check_fails_closed_until_sections_exist() -> None:
    assert policies.instructor_teaches(_staff(Role.INSTRUCTOR), make_user()) is False


def test_auth_04_cannot_reset_self() -> None:
    admin_user = _staff(Role.ADMIN)
    assert _reset(admin_user, admin_user).status_code == 404


def test_auth_04_unknown_user_is_404() -> None:
    response = _client(_staff(Role.ADMIN)).post("/api/users/999999/reset-password")
    assert response.status_code == 404


def test_auth_04_anonymous_denied() -> None:
    student = make_user()
    assert APIClient().post(f"/api/users/{student.pk}/reset-password").status_code == 403


# --- Natija ---


def test_auth_04_reset_returns_one_time_password_once() -> None:
    student = make_user(password=PASSWORD)
    response = _reset(_staff(Role.ADMIN), student)
    assert response.status_code == 200
    temporary = response.json()["temporary_password"]
    assert len(temporary) >= 12
    assert "no-store" in response["Cache-Control"]
    student.refresh_from_db()
    assert student.check_password(temporary)
    assert not student.check_password(PASSWORD)
    assert student.must_change_password
    # Ikkinchi tiklash — yangi parol, eskisi endi ishlamaydi.
    again = _reset(_staff(Role.ADMIN), student).json()["temporary_password"]
    student.refresh_from_db()
    assert again != temporary
    assert not student.check_password(temporary)


def test_auth_04_reset_is_audited_without_password(caplog: pytest.LogCaptureFixture) -> None:
    admin_user = _staff(Role.ADMIN)
    student = make_user()
    with caplog.at_level(logging.INFO):
        temporary = _reset(admin_user, student).json()["temporary_password"]
    entry = AuditLog.objects.get(action=Action.PASSWORD_RESET)
    assert entry.actor == admin_user
    assert entry.target_id == str(student.pk)
    assert temporary not in str(entry.before) + str(entry.after)
    assert temporary not in caplog.text


def test_auth_04_reset_kills_existing_sessions() -> None:
    from django.test import Client

    student = make_user(password=PASSWORD)
    browser = Client()
    browser.force_login(student)
    assert browser.get("/api/auth/me").status_code == 200
    _reset(_staff(Role.ADMIN), student)
    assert browser.get("/api/auth/me").status_code == 403


# --- must_change_password ---


def _must_change_user() -> User:
    user = make_user(password=PASSWORD)
    User.objects.filter(pk=user.pk).update(must_change_password=True)
    user.refresh_from_db()
    return user


def _session(user: User) -> Any:
    # Haqiqiy sessiya: tekshiruv middleware'da (barcha API va admin uchun, view'dan oldin).
    from django.test import Client

    browser = Client()
    browser.force_login(user)
    return browser


def test_auth_04_must_change_blocks_other_apis() -> None:
    client = _session(_must_change_user())
    response = client.get("/api/directions")
    # Ochiq endpoint ham — tizimga kirgan, parolni almashtirmagan foydalanuvchi uchun yopiq.
    assert response.status_code == 403
    assert response.json()["code"] == "password_change_required"


def test_auth_04_must_change_allows_me_logout_and_change() -> None:
    user = _must_change_user()
    client = _session(user)
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True
    response = client.post(
        "/api/auth/change-password",
        {"old_password": PASSWORD, "new_password": NEW_PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 204
    user.refresh_from_db()
    assert not user.must_change_password
    assert user.check_password(NEW_PASSWORD)
    assert client.get("/api/directions").status_code == 200


def test_auth_04_must_change_blocks_admin_site() -> None:
    from django.test import Client

    boss = make_user(role=Role.SUPER_ADMIN, direction=None, is_superuser=True, password=PASSWORD)
    User.objects.filter(pk=boss.pk).update(must_change_password=True)
    browser = Client()
    browser.force_login(boss)
    assert browser.get("/admin/").status_code == 403
    assert browser.get("/admin/password_change/").status_code == 200


def test_auth_04_admin_password_change_clears_flag_and_audits() -> None:
    from django.test import Client

    boss = make_user(role=Role.SUPER_ADMIN, direction=None, is_superuser=True, password=PASSWORD)
    User.objects.filter(pk=boss.pk).update(must_change_password=True)
    browser = Client()
    browser.force_login(boss)
    response = browser.post(
        "/admin/password_change/",
        {"old_password": PASSWORD, "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
    )
    assert response.status_code == 302
    boss.refresh_from_db()
    assert not boss.must_change_password
    assert AuditLog.objects.filter(action=Action.PASSWORD_CHANGED, target_id=str(boss.pk)).exists()


# --- change-password ---


def test_auth_04_change_password_wrong_old_rejected() -> None:
    user = make_user(password=PASSWORD)
    response = _client(user).post(
        "/api/auth/change-password",
        {"old_password": "xato", "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


@pytest.mark.parametrize("new", ["12345678", "qwerty123"])
def test_auth_04_change_password_validators(new: str) -> None:
    response = _client(make_user(password=PASSWORD)).post(
        "/api/auth/change-password", {"old_password": PASSWORD, "new_password": new}, format="json"
    )
    assert response.status_code == 400
    assert "new_password" in response.json()


def test_auth_04_change_password_same_as_old_rejected() -> None:
    response = _client(make_user(password=PASSWORD)).post(
        "/api/auth/change-password",
        {"old_password": PASSWORD, "new_password": PASSWORD},
        format="json",
    )
    assert response.status_code == 400


def test_auth_04_change_password_keeps_session_and_audits() -> None:
    from django.test import Client

    user = make_user(password=PASSWORD)
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(user)
    browser.get("/api/auth/csrf")
    token = browser.cookies["csrftoken"].value
    response = browser.post(
        "/api/auth/change-password",
        {"old_password": PASSWORD, "new_password": NEW_PASSWORD},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 204
    assert browser.get("/api/auth/me").status_code == 200  # sessiya saqlanadi
    entry = AuditLog.objects.get(action=Action.PASSWORD_CHANGED)
    assert entry.actor == user
    assert NEW_PASSWORD not in str(entry.after)


def test_auth_04_change_password_requires_csrf() -> None:
    from django.test import Client

    user = make_user(password=PASSWORD)
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(user)
    response = browser.post(
        "/api/auth/change-password",
        {"old_password": PASSWORD, "new_password": NEW_PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_auth_04_change_password_throttled() -> None:
    from django.test import override_settings

    client = _client(make_user(password=PASSWORD))
    with override_settings(AUTH_CHANGE_PASSWORD_RATE="2/hour"):
        codes = [
            client.post(
                "/api/auth/change-password",
                {"old_password": "xato", "new_password": NEW_PASSWORD},
                format="json",
            ).status_code
            for _ in range(3)
        ]
    assert codes == [400, 400, 429]


def test_auth_04_registration_does_not_audit_password_change() -> None:
    make_user(password=PASSWORD)
    assert not AuditLog.objects.filter(action=Action.PASSWORD_CHANGED).exists()


def test_auth_04_password_never_in_admin_change_page() -> None:
    from django.test import Client

    student = make_user()
    admin_user = _staff(Role.ADMIN)
    temporary = _reset(admin_user, student).json()["temporary_password"]
    browser = Client()
    browser.force_login(admin_user)
    body = browser.get(f"/admin/accounts/user/{student.pk}/change/").content.decode()
    assert temporary not in body
