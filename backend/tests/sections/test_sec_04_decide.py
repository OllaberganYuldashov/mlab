"""SEC-04, SEC-05, SEC-06, SEC-08 (I1-05): so'rovlarni tasdiqlash va rad etish, kursga kirish."""

from __future__ import annotations

import threading
from typing import Any

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.audit.models import Action, AuditLog
from apps.sections.access import can_access_course
from apps.sections.models import Membership, MembershipStatus, Section
from tests.accounts.factories import make_user
from tests.sections.factories import make_instructor, make_membership, make_section

pytestmark = pytest.mark.django_db


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _decide(user: User, section: Section, ids: list[int], decision: str) -> Any:
    return _client(user).post(
        f"/api/sections/{section.pk}/members/decide",
        {"ids": ids, "decision": decision},
        format="json",
    )


def _pending(section: Section, n: int) -> list[Membership]:
    return [make_membership(section=section) for _ in range(n)]


def _approve(membership: Membership) -> Membership:
    membership.status = MembershipStatus.APPROVED
    membership.decided_at = timezone.now()
    membership.decided_by = membership.section.instructor
    membership.save()
    return membership


# --- Ro'yxat ---


def test_sec_04_list_pending_members_with_student_info() -> None:
    section = make_section()
    first, second = _pending(section, 2)
    _approve(make_membership(section=section))
    make_membership()  # boshqa guruh
    body = _client(section.instructor).get(f"/api/sections/{section.pk}/members").json()
    assert [m["id"] for m in body["results"]] == [first.pk, second.pk]
    row = body["results"][0]
    assert row["status"] == "pending"
    assert row["student"] == {
        "id": first.student_id,
        "hemis_id": first.student.hemis_id,
        "full_name": first.student.full_name,
    }


def test_sec_04_list_approved_filter() -> None:
    section = make_section()
    _pending(section, 1)
    approved = _approve(make_membership(section=section))
    url = f"/api/sections/{section.pk}/members?status=approved"
    body = _client(section.instructor).get(url).json()
    assert [m["id"] for m in body["results"]] == [approved.pk]


def test_sec_04_invalid_status_filter_rejected() -> None:
    section = make_section()
    url = f"/api/sections/{section.pk}/members?status=banned"
    assert _client(section.instructor).get(url).status_code == 400


def test_sec_04_foreign_instructor_cannot_list_or_decide() -> None:
    section = make_section()
    (membership,) = _pending(section, 1)
    stranger = make_instructor()
    assert _client(stranger).get(f"/api/sections/{section.pk}/members").status_code == 404
    assert _decide(stranger, section, [membership.pk], "approve").status_code == 404
    membership.refresh_from_db()
    assert membership.status == MembershipStatus.PENDING


def test_sec_04_student_cannot_list() -> None:
    membership = _approve(make_membership())
    url = f"/api/sections/{membership.section_id}/members"
    assert _client(membership.student).get(url).status_code == 403


# --- Qaror ---


def test_sec_04_bulk_approve_audited() -> None:
    section = make_section()
    members = _pending(section, 3)
    response = _decide(section.instructor, section, [m.pk for m in members], "approve")
    assert response.status_code == 200
    body = response.json()
    assert sorted(body["approved"]) == sorted(m.pk for m in members)
    assert body["skipped"] == []
    for m in members:
        m.refresh_from_db()
        assert m.status == MembershipStatus.APPROVED
        assert m.decided_by == section.instructor
        assert m.decided_at is not None
    assert AuditLog.objects.filter(action=Action.MEMBERSHIP_APPROVED).count() == 3


def test_sec_04_reject_single() -> None:
    section = make_section()
    (membership,) = _pending(section, 1)
    response = _decide(section.instructor, section, [membership.pk], "reject")
    assert response.json()["rejected"] == [membership.pk]
    membership.refresh_from_db()
    assert membership.status == MembershipStatus.REJECTED
    entry = AuditLog.objects.get(action=Action.MEMBERSHIP_REJECTED)
    assert entry.before == {"status": "pending"}
    assert entry.after == {"status": "rejected"}


def test_sec_04_foreign_and_stale_ids_are_skipped_without_effect() -> None:
    section = make_section()
    (mine,) = _pending(section, 1)
    already = _approve(make_membership(section=section))
    foreign = make_membership()
    ids = [mine.pk, already.pk, foreign.pk, 999_999]
    body = _decide(section.instructor, section, ids, "reject").json()
    assert body["rejected"] == [mine.pk]
    assert sorted(body["skipped"]) == sorted([already.pk, foreign.pk, 999_999])
    foreign.refresh_from_db()
    already.refresh_from_db()
    assert foreign.status == MembershipStatus.PENDING
    assert already.status == MembershipStatus.APPROVED


@pytest.mark.parametrize(
    "payload",
    [{"ids": [], "decision": "approve"}, {"ids": [1], "decision": "maybe"}, {"ids": "x"}, {}],
)
def test_sec_04_invalid_payload_rejected(payload: dict[str, object]) -> None:
    section = make_section()
    response = _client(section.instructor).post(
        f"/api/sections/{section.pk}/members/decide", payload, format="json"
    )
    assert response.status_code == 400


def test_sec_04_too_many_ids_rejected() -> None:
    section = make_section()
    response = _decide(section.instructor, section, list(range(1, 502)), "approve")
    assert response.status_code == 400


def test_sec_06_approval_over_capacity_approves_nobody() -> None:
    section = make_section(capacity=2)
    _approve(make_membership(section=section))
    members = _pending(section, 2)
    response = _decide(section.instructor, section, [m.pk for m in members], "approve")
    assert response.status_code == 409
    assert response.json()["code"] == "section_full"
    assert Membership.objects.approved().filter(section=section).count() == 1


def test_sec_08_instructor_total_limit_across_sections() -> None:
    instructor = make_instructor(student_limit=2)
    first = make_section(instructor=instructor)
    second = make_section(instructor=instructor)
    _approve(make_membership(section=first))
    _approve(make_membership(section=first))
    (waiting,) = _pending(second, 1)
    response = _decide(instructor, second, [waiting.pk], "approve")
    assert response.status_code == 409
    assert response.json()["code"] == "instructor_limit"
    waiting.refresh_from_db()
    assert waiting.status == MembershipStatus.PENDING


def test_sec_06_reject_ignores_capacity() -> None:
    section = make_section(capacity=1)
    _approve(make_membership(section=section))
    (waiting,) = _pending(section, 1)
    assert _decide(section.instructor, section, [waiting.pk], "reject").status_code == 200


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPER_ADMIN])
def test_sec_04_staff_can_decide(role: Role) -> None:
    section = make_section()
    (membership,) = _pending(section, 1)
    staff = make_user(role=role, direction=None, is_superuser=role == Role.SUPER_ADMIN)
    assert _decide(staff, section, [membership.pk], "approve").status_code == 200
    membership.refresh_from_db()
    assert membership.decided_by == staff


@pytest.mark.django_db(transaction=True)
def test_sec_06_parallel_approvals_and_capacity_drop_never_exceed_capacity() -> None:
    section = make_section(capacity=3)
    members = _pending(section, 3)
    instructor = section.instructor

    def approve(m: Membership) -> None:
        try:
            _decide(instructor, section, [m.pk], "approve")
        finally:
            connection.close()

    def shrink() -> None:
        try:
            _client(instructor).patch(f"/api/sections/{section.pk}", {"capacity": 1}, format="json")
        finally:
            connection.close()

    threads = [threading.Thread(target=approve, args=(m,)) for m in members]
    threads.append(threading.Thread(target=shrink))
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    section.refresh_from_db()
    assert Membership.objects.approved().filter(section=section).count() <= section.capacity


# --- SEC-05: kursga kirish ---


def test_sec_05_approved_member_accesses_course_others_not() -> None:
    section = make_section()
    (membership,) = _pending(section, 1)
    course = section.course
    assert can_access_course(membership.student, course) is False  # hali tasdiqlanmagan
    _approve(membership)
    assert can_access_course(membership.student, course) is True
    assert can_access_course(make_user(), course) is False
    assert can_access_course(section.instructor, course) is True
    assert can_access_course(make_instructor(), course) is False
    admin_user = make_user(role=Role.ADMIN, direction=None)
    assert can_access_course(admin_user, course) is True
