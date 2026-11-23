"""SEC-01, SEC-08, SET-03 (I1-02): o'qituvchi guruh API — yaratish, ro'yxat, tahrirlash; IDOR."""

from __future__ import annotations

from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import policies
from apps.accounts.models import Role, User
from apps.audit.models import Action, AuditLog
from apps.sections.models import Membership, MembershipStatus, Section
from tests.accounts.factories import make_direction, make_user
from tests.sections.factories import make_course, make_instructor, make_membership, make_section

pytestmark = pytest.mark.django_db

URL = "/api/sections"


def _client(user: User | None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def _approve(membership: Membership) -> Membership:
    membership.status = MembershipStatus.APPROVED
    membership.decided_at = timezone.now()
    membership.decided_by = membership.section.instructor
    membership.save()
    return membership


def _staff(role: Role) -> User:
    return make_user(role=role, direction=None, is_superuser=role == Role.SUPER_ADMIN)


# --- Yaratish ---


def test_sec_01_instructor_creates_section_with_defaults() -> None:
    course = make_course()
    direction = make_direction()
    instructor = make_instructor()
    response = _client(instructor).post(
        URL, {"name": "  ML-21  ", "direction": direction.pk}, format="json"
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["name"] == "ML-21"
    assert body["capacity"] == 30
    assert body["join_enabled"] is True
    assert body["approved_count"] == 0
    assert body["course"] == course.pk
    assert body["instructor"] == {"id": instructor.pk, "full_name": instructor.full_name}
    section = Section.objects.get(pk=body["id"])
    assert section.instructor == instructor
    entry = AuditLog.objects.get(action=Action.SECTION_CREATED)
    assert entry.actor == instructor
    assert entry.after == {"name": "ML-21", "capacity": 30, "join_enabled": True}


def test_sec_01_cannot_create_for_another_instructor() -> None:
    make_course()
    other = make_instructor()
    instructor = make_instructor()
    response = _client(instructor).post(
        URL,
        {"name": "G", "direction": make_direction().pk, "instructor": other.pk},
        format="json",
    )
    assert response.status_code == 201
    assert Section.objects.get().instructor == instructor


@pytest.mark.parametrize("capacity", [0, 501, "x"])
def test_sec_01_invalid_capacity_rejected(capacity: Any) -> None:
    make_course()
    response = _client(make_instructor()).post(
        URL, {"name": "G", "direction": make_direction().pk, "capacity": capacity}, format="json"
    )
    assert response.status_code == 400
    assert "capacity" in response.json()


def test_sec_01_blank_name_rejected() -> None:
    make_course()
    response = _client(make_instructor()).post(
        URL, {"name": "   ", "direction": make_direction().pk}, format="json"
    )
    assert response.status_code == 400
    assert "name" in response.json()


def test_sec_01_create_without_imported_course_is_clear_error() -> None:
    response = _client(make_instructor()).post(
        URL, {"name": "G", "direction": make_direction().pk}, format="json"
    )
    assert response.status_code == 400
    assert "course" in response.json()


@pytest.mark.parametrize("role", [Role.STUDENT, Role.ADMIN, Role.SUPER_ADMIN])
def test_sec_01_only_instructor_creates(role: Role) -> None:
    make_course()
    user = make_user() if role == Role.STUDENT else _staff(role)
    response = _client(user).post(URL, {"name": "G", "direction": make_direction().pk})
    assert response.status_code == 403


def test_sec_01_anonymous_forbidden() -> None:
    assert _client(None).get(URL).status_code == 403


# --- Ro'yxat ---


def test_sec_01_instructor_lists_only_own_sections_newest_first() -> None:
    instructor = make_instructor()
    older = make_section(instructor=instructor)
    newer = make_section(instructor=instructor)
    make_section()  # begona
    body = _client(instructor).get(URL).json()
    assert [s["id"] for s in body["results"]] == [newer.pk, older.pk]


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPER_ADMIN])
def test_sec_01_staff_lists_all_sections(role: Role) -> None:
    make_section()
    make_section()
    body = _client(_staff(role)).get(URL).json()
    assert len(body["results"]) == 2


def test_sec_01_student_cannot_list() -> None:
    assert _client(make_user()).get(URL).status_code == 403


def test_sec_01_list_is_cursor_paginated() -> None:
    instructor = make_instructor()
    for _ in range(3):
        make_section(instructor=instructor)
    first = _client(instructor).get(URL, {"page_size": 2}).json()
    assert len(first["results"]) == 2
    assert first["next"]
    second = _client(instructor).get(first["next"]).json()
    assert len(second["results"]) == 1
    ids = [s["id"] for s in first["results"] + second["results"]]
    assert len(set(ids)) == 3


def test_sec_01_approved_count_without_n_plus_one(django_assert_max_num_queries: Any) -> None:
    instructor = make_instructor()
    for _ in range(5):
        section = make_section(instructor=instructor)
        _approve(make_membership(section=section))
        make_membership(section=section)  # pending — hisoblanmaydi
    client = _client(instructor)
    with django_assert_max_num_queries(3):
        body = client.get(URL).json()
    assert {s["approved_count"] for s in body["results"]} == {1}


# --- Bitta guruh va tahrirlash ---


def test_sec_01_foreign_instructor_gets_404() -> None:
    section = make_section()
    client = _client(make_instructor())
    assert client.get(f"{URL}/{section.pk}").status_code == 404
    assert client.patch(f"{URL}/{section.pk}", {"capacity": 5}, format="json").status_code == 404
    section.refresh_from_db()
    assert section.capacity == 30


def test_sec_01_student_member_cannot_view_or_edit() -> None:
    membership = _approve(make_membership())
    client = _client(membership.student)
    assert client.get(f"{URL}/{membership.section_id}").status_code == 403
    response = client.patch(f"{URL}/{membership.section_id}", {"capacity": 1}, format="json")
    assert response.status_code == 403


def test_set_03_instructor_updates_capacity_and_join_flag_audited() -> None:
    section = make_section()
    response = _client(section.instructor).patch(
        f"{URL}/{section.pk}", {"capacity": 40, "join_enabled": False}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["capacity"] == 40
    section.refresh_from_db()
    assert (section.capacity, section.join_enabled) == (40, False)
    entry = AuditLog.objects.get(action=Action.SECTION_UPDATED)
    assert entry.before == {"capacity": 30, "join_enabled": True}
    assert entry.after == {"capacity": 40, "join_enabled": False}


def test_set_03_unchanged_patch_not_audited() -> None:
    section = make_section()
    _client(section.instructor).patch(f"{URL}/{section.pk}", {"capacity": 30}, format="json")
    assert not AuditLog.objects.filter(action=Action.SECTION_UPDATED).exists()


def test_set_03_capacity_cannot_go_below_approved_members() -> None:
    section = make_section(capacity=3)
    for _ in range(2):
        _approve(make_membership(section=section))
    response = _client(section.instructor).patch(
        f"{URL}/{section.pk}", {"capacity": 1}, format="json"
    )
    assert response.status_code == 400
    assert "capacity" in response.json()
    ok = _client(section.instructor).patch(f"{URL}/{section.pk}", {"capacity": 2}, format="json")
    assert ok.status_code == 200


def test_sec_01_course_and_instructor_not_editable() -> None:
    section = make_section()
    other = make_instructor()
    _client(section.instructor).patch(
        f"{URL}/{section.pk}",
        {"instructor": other.pk, "course": make_course().pk},
        format="json",
    )
    section.refresh_from_db()
    assert section.instructor_id != other.pk


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPER_ADMIN])
def test_sec_08_staff_can_view_and_edit_any_section(role: Role) -> None:
    section = make_section()
    client = _client(_staff(role))
    assert client.get(f"{URL}/{section.pk}").status_code == 200
    assert client.patch(f"{URL}/{section.pk}", {"capacity": 50}, format="json").status_code == 200


# --- instructor_teaches (R0-08 parol tiklash bilan bog'liq) ---


def test_sec_01_instructor_teaches_only_approved_members() -> None:
    membership = make_membership()
    instructor = membership.section.instructor
    assert policies.instructor_teaches(instructor, membership.student) is False  # pending
    _approve(membership)
    assert policies.instructor_teaches(instructor, membership.student) is True
    assert policies.instructor_teaches(make_instructor(), membership.student) is False


def test_sec_01_instructor_resets_password_of_own_student_only() -> None:
    membership = _approve(make_membership())
    instructor = membership.section.instructor
    client = _client(instructor)
    assert client.post(f"/api/users/{membership.student_id}/reset-password").status_code == 200
    stranger = make_user()
    assert client.post(f"/api/users/{stranger.pk}/reset-password").status_code == 404
