"""SEC-03, SEC-06, SEC-07 (I1-04): talaba havola orqali guruhni ko'radi va so'rov yuboradi."""

from __future__ import annotations

import threading

import pytest
from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.sections.models import Membership, MembershipStatus, Section
from apps.sections.tokens import new_token
from tests.accounts.factories import make_user
from tests.sections.factories import make_membership, make_section

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


def _with_token(section: Section) -> str:
    token, digest = new_token()
    section.join_token_hash = digest
    section.save()
    return token


def _client(user: User | None = None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def _approve(membership: Membership) -> None:
    membership.status = MembershipStatus.APPROVED
    membership.decided_at = timezone.now()
    membership.decided_by = membership.section.instructor
    membership.save()


# --- Ko'rish (preview) ---


def test_sec_03_preview_shows_only_section_name_and_instructor() -> None:
    section = make_section()
    token = _with_token(section)
    response = _client().get(f"/api/join/{token}")  # kirmagan foydalanuvchi ham ko'radi
    assert response.status_code == 200
    assert response.json() == {
        "section": section.name,
        "instructor": section.instructor.full_name,
        "join_enabled": True,
        "is_full": False,
    }


@pytest.mark.parametrize("token", ["yoq-token-1234567890", "x"])
def test_sec_03_unknown_token_404(token: str) -> None:
    make_section()
    assert _client().get(f"/api/join/{token}").status_code == 404


def test_sec_03_rotated_token_404() -> None:
    section = make_section()
    old = _with_token(section)
    _with_token(section)
    assert _client().get(f"/api/join/{old}").status_code == 404
    assert _client(make_user()).post(f"/api/join/{old}").status_code == 404


def test_sec_03_preview_throttled_per_ip() -> None:
    section = make_section()
    token = _with_token(section)
    with override_settings(SECTION_JOIN_RATE="2/minute"):
        codes = [_client().get(f"/api/join/{token}").status_code for _ in range(3)]
    assert codes == [200, 200, 429]


# --- So'rov yuborish ---


def test_sec_03_student_requests_membership() -> None:
    section = make_section()
    token = _with_token(section)
    student = make_user()
    response = _client(student).post(f"/api/join/{token}")
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    membership = Membership.objects.get(student=student)
    assert membership.section == section
    assert membership.status == MembershipStatus.PENDING


def test_sec_03_repeated_request_is_idempotent() -> None:
    section = make_section()
    token = _with_token(section)
    student = make_user()
    client = _client(student)
    first = client.post(f"/api/join/{token}")
    second = client.post(f"/api/join/{token}")
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]
    assert Membership.objects.filter(student=student).count() == 1


def test_sec_03_already_approved_in_same_section_returns_it() -> None:
    membership = make_membership()
    _approve(membership)
    token = _with_token(membership.section)
    response = _client(membership.student).post(f"/api/join/{token}")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


@pytest.mark.parametrize("role", [Role.INSTRUCTOR, Role.ADMIN])
def test_sec_03_only_students_can_request(role: Role) -> None:
    token = _with_token(make_section())
    user = make_user(role=role, direction=None)
    assert _client(user).post(f"/api/join/{token}").status_code == 403


def test_sec_03_anonymous_cannot_request() -> None:
    token = _with_token(make_section())
    assert _client().post(f"/api/join/{token}").status_code == 403


def test_sec_03_csrf_enforced_for_session_users() -> None:
    from django.test import Client

    token = _with_token(make_section())
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(make_user())
    assert browser.post(f"/api/join/{token}").status_code == 403
    assert not Membership.objects.exists()


def test_sec_06_full_section_rejects_new_request() -> None:
    section = make_section(capacity=1)
    _approve(make_membership(section=section))
    token = _with_token(section)
    response = _client(make_user()).post(f"/api/join/{token}")
    assert response.status_code == 409
    assert response.json()["code"] == "section_full"
    assert "to'lgan" in response.json()["detail"]
    preview = _client().get(f"/api/join/{token}").json()
    assert preview["is_full"] is True


def test_sec_06_join_disabled_rejects_request() -> None:
    section = make_section(join_enabled=False)
    token = _with_token(section)
    response = _client(make_user()).post(f"/api/join/{token}")
    assert response.status_code == 409
    assert response.json()["code"] == "join_disabled"


def test_sec_07_student_with_other_active_section_rejected() -> None:
    existing = make_membership()
    token = _with_token(make_section())
    response = _client(existing.student).post(f"/api/join/{token}")
    assert response.status_code == 409
    assert response.json()["code"] == "other_section"
    assert Membership.objects.filter(student=existing.student).count() == 1


def test_sec_07_rejected_student_can_request_again() -> None:
    membership = make_membership()
    membership.status = MembershipStatus.REJECTED
    membership.decided_at = timezone.now()
    membership.decided_by = membership.section.instructor
    membership.save()
    token = _with_token(membership.section)
    assert _client(membership.student).post(f"/api/join/{token}").status_code == 201


@pytest.mark.django_db(transaction=True)
def test_sec_07_parallel_requests_create_one_membership() -> None:
    section = make_section()
    token = _with_token(section)
    student = make_user()
    results: list[int] = []

    def hit() -> None:
        try:
            results.append(_client(student).post(f"/api/join/{token}").status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=hit) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert Membership.objects.filter(student=student).count() == 1
    assert sorted(results).count(201) == 1
    assert set(results) <= {200, 201}


# --- O'z holatini ko'rish ---


def test_sec_04_student_sees_own_latest_membership() -> None:
    student = make_user()
    client = _client(student)
    assert client.get("/api/me/membership").json() == {"membership": None}
    membership = make_membership(student=student)
    body = client.get("/api/me/membership").json()["membership"]
    assert body["status"] == "pending"
    assert body["section"] == membership.section.name
    assert body["instructor"] == membership.section.instructor.full_name


def test_sec_04_membership_endpoint_only_for_students() -> None:
    user = make_user(role=Role.INSTRUCTOR, direction=None)
    assert _client(user).get("/api/me/membership").status_code == 403
