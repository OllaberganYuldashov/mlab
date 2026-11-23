"""AUTH-05, SEC-08 (R0-09): admin o'qituvchi akkauntini yaratadi va talaba limitini belgilaydi."""

from __future__ import annotations

from typing import Any

import pytest
from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.accounts.limits import StudentLimitExceeded, ensure_capacity
from apps.accounts.models import Role, User
from apps.audit.models import Action, AuditLog
from tests.accounts.factories import make_user

pytestmark = pytest.mark.django_db

URL = "/api/instructors"


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


def _staff(role: Role) -> User:
    return make_user(role=role, direction=None, is_superuser=role == Role.SUPER_ADMIN)


def _client(user: User | None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def _payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "hemis_id": "777777777777",
        "full_name": "Oʻqituvchi Sinov",
        "student_limit": 60,
    }
    data.update(overrides)
    return data


# --- Yaratish ---


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPER_ADMIN])
def test_auth_05_staff_creates_instructor_with_temporary_password(role: Role) -> None:
    actor = _staff(role)
    response = _client(actor).post(URL, _payload(), format="json")
    assert response.status_code == 201
    assert "no-store" in response["Cache-Control"]
    body = response.json()
    temporary = body.pop("temporary_password")
    assert body == {
        "id": body["id"],
        "hemis_id": "777777777777",
        "full_name": "Oʻqituvchi Sinov",
        "student_limit": 60,
    }
    instructor = User.objects.get(hemis_id="777777777777")
    assert instructor.role == Role.INSTRUCTOR
    assert instructor.direction is None
    assert instructor.must_change_password
    assert instructor.check_password(temporary)
    entry = AuditLog.objects.get(action=Action.INSTRUCTOR_CREATED)
    assert entry.actor == actor
    assert entry.after == {"role": "instructor", "student_limit": 60}
    assert temporary not in str(entry.after)


@pytest.mark.parametrize("role", [Role.INSTRUCTOR, Role.STUDENT])
def test_auth_05_non_admin_forbidden(role: Role) -> None:
    actor = _staff(role) if role != Role.STUDENT else make_user()
    assert _client(actor).post(URL, _payload(), format="json").status_code == 403
    assert not User.objects.filter(hemis_id="777777777777").exists()


def test_auth_05_anonymous_forbidden() -> None:
    assert _client(None).post(URL, _payload(), format="json").status_code == 403


@pytest.mark.parametrize("limit", [0, -1, "abc", None])
def test_auth_05_invalid_limit_rejected(limit: Any) -> None:
    response = _client(_staff(Role.ADMIN)).post(URL, _payload(student_limit=limit), format="json")
    assert response.status_code == 400
    assert "student_limit" in response.json()


def test_auth_05_duplicate_hemis_id_rejected() -> None:
    make_user(hemis_id="777777777777")
    response = _client(_staff(Role.ADMIN)).post(URL, _payload(), format="json")
    assert response.status_code == 400
    assert "hemis_id" in response.json()


def test_auth_05_cannot_choose_role_via_api() -> None:
    response = _client(_staff(Role.ADMIN)).post(
        URL, _payload(role="super_admin", is_superuser=True), format="json"
    )
    assert response.status_code == 201
    assert User.objects.get(hemis_id="777777777777").role == Role.INSTRUCTOR


# --- Limitni o'zgartirish ---


def test_auth_05_admin_changes_limit_audited() -> None:
    admin_user = _staff(Role.ADMIN)
    instructor = make_user(role=Role.INSTRUCTOR, direction=None, student_limit=30)
    response = _client(admin_user).patch(
        f"{URL}/{instructor.pk}", {"student_limit": 45}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["student_limit"] == 45
    instructor.refresh_from_db()
    assert instructor.student_limit == 45
    entry = AuditLog.objects.get(action=Action.STUDENT_LIMIT_CHANGED)
    assert entry.before == {"student_limit": 30}
    assert entry.after == {"student_limit": 45}


def test_auth_05_limit_patch_only_for_instructors() -> None:
    student = make_user()
    response = _client(_staff(Role.ADMIN)).patch(
        f"{URL}/{student.pk}", {"student_limit": 5}, format="json"
    )
    assert response.status_code == 404


def test_auth_05_limit_patch_forbidden_for_instructor_self() -> None:
    instructor = make_user(role=Role.INSTRUCTOR, direction=None)
    response = _client(instructor).patch(
        f"{URL}/{instructor.pk}", {"student_limit": 500}, format="json"
    )
    assert response.status_code == 403


def test_auth_05_unchanged_limit_not_audited() -> None:
    instructor = make_user(role=Role.INSTRUCTOR, direction=None, student_limit=30)
    _client(_staff(Role.ADMIN)).patch(
        f"{URL}/{instructor.pk}", {"student_limit": 30}, format="json"
    )
    assert not AuditLog.objects.filter(action=Action.STUDENT_LIMIT_CHANGED).exists()


# --- DB cheklovi ---


def test_sec_08_student_limit_only_for_instructors_at_db_level() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [User(hemis_id="123456789012", full_name="X", role=Role.ADMIN, student_limit=10)]
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [User(hemis_id="123456789013", full_name="X", role=Role.INSTRUCTOR, student_limit=None)]
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [User(hemis_id="123456789014", full_name="X", role=Role.INSTRUCTOR, student_limit=0)]
        )


# --- Limitdan oshish (I1 dagi guruhlar chaqiradi) ---


def test_sec_08_ensure_capacity_allows_up_to_limit() -> None:
    instructor = make_user(role=Role.INSTRUCTOR, direction=None, student_limit=30)
    ensure_capacity(instructor, current_students=29)
    ensure_capacity(instructor, current_students=25, adding=5)


def test_sec_08_ensure_capacity_rejects_over_limit() -> None:
    instructor = make_user(role=Role.INSTRUCTOR, direction=None, student_limit=30)
    with pytest.raises(StudentLimitExceeded, match="30"):
        ensure_capacity(instructor, current_students=30)
    with pytest.raises(StudentLimitExceeded):
        ensure_capacity(instructor, current_students=28, adding=3)


@pytest.mark.parametrize(("current", "adding"), [(-1, 1), (0, 0)])
def test_sec_08_ensure_capacity_rejects_bad_numbers(current: int, adding: int) -> None:
    instructor = make_user(role=Role.INSTRUCTOR, direction=None)
    with pytest.raises(ValueError, match="son"):
        ensure_capacity(instructor, current_students=current, adding=adding)


def test_sec_08_ensure_capacity_only_for_instructors() -> None:
    with pytest.raises(ValueError, match="o'qituvchi"):
        ensure_capacity(make_user(), current_students=0)


# --- Admin forma ---


def test_sec_08_admin_promotion_requires_limit_and_demotion_clears_it() -> None:
    from django.test import Client

    browser = Client()
    browser.force_login(_staff(Role.SUPER_ADMIN))
    student = make_user()
    response = browser.post(
        f"/admin/accounts/user/{student.pk}/change/",
        {"full_name": student.full_name, "role": Role.INSTRUCTOR, "is_active": "on"},
    )
    assert response.status_code == 200  # forma xato bilan qaytadi (limit yo'q)
    assert "Talaba limiti" in response.content.decode()
    instructor = make_user(role=Role.INSTRUCTOR, direction=None, student_limit=30)
    browser.post(
        f"/admin/accounts/user/{instructor.pk}/change/",
        {
            "full_name": instructor.full_name,
            "role": Role.ADMIN,
            "student_limit": "30",
            "is_active": "on",
        },
    )
    instructor.refresh_from_db()
    assert instructor.role == Role.ADMIN
    assert instructor.student_limit is None
