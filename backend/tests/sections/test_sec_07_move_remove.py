"""SEC-07 (I1-06): talabani o'z boshqa guruhiga o'tkazish yoki chiqarish; tarix saqlanadi."""

from __future__ import annotations

from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import Action, AuditLog
from apps.sections.models import Membership, MembershipStatus
from tests.sections.factories import make_instructor, make_membership, make_section

pytestmark = pytest.mark.django_db


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _approved(**fields: Any) -> Membership:
    membership = make_membership(**fields)
    membership.status = MembershipStatus.APPROVED
    membership.decided_at = timezone.now()
    membership.decided_by = membership.section.instructor
    membership.save()
    return membership


def _move(user: User, membership: Membership, target: int) -> Any:
    return _client(user).post(
        f"/api/sections/{membership.section_id}/members/{membership.pk}/move",
        {"target_section": target},
        format="json",
    )


def _remove(user: User, membership: Membership) -> Any:
    return _client(user).post(
        f"/api/sections/{membership.section_id}/members/{membership.pk}/remove"
    )


def test_sec_07_move_to_own_other_section_keeps_history() -> None:
    membership = _approved()
    instructor = membership.section.instructor
    target = make_section(instructor=instructor)
    response = _move(instructor, membership, target.pk)
    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.status == MembershipStatus.REMOVED
    new = Membership.objects.get(student=membership.student, status=MembershipStatus.APPROVED)
    assert new.section == target
    assert response.json()["id"] == new.pk
    assert Membership.objects.filter(student=membership.student).count() == 2
    entry = AuditLog.objects.get(action=Action.MEMBERSHIP_MOVED)
    assert entry.before == {"section": membership.section_id}
    assert entry.after == {"section": target.pk}


def test_sec_07_cannot_move_to_foreign_section() -> None:
    membership = _approved()
    foreign = make_section()
    response = _move(membership.section.instructor, membership, foreign.pk)
    assert response.status_code == 404
    membership.refresh_from_db()
    assert membership.status == MembershipStatus.APPROVED


def test_sec_07_move_respects_target_capacity() -> None:
    membership = _approved()
    target = make_section(instructor=membership.section.instructor, capacity=1)
    _approved(section=target)
    response = _move(membership.section.instructor, membership, target.pk)
    assert response.status_code == 409
    assert response.json()["code"] == "section_full"
    membership.refresh_from_db()
    assert membership.status == MembershipStatus.APPROVED


def test_sec_07_move_to_same_section_rejected() -> None:
    membership = _approved()
    response = _move(membership.section.instructor, membership, membership.section_id)
    assert response.status_code == 400


def test_sec_07_only_approved_can_be_moved() -> None:
    membership = make_membership()  # pending
    target = make_section(instructor=membership.section.instructor)
    assert _move(membership.section.instructor, membership, target.pk).status_code == 404


def test_sec_07_remove_marks_removed_and_audits() -> None:
    membership = _approved()
    response = _remove(membership.section.instructor, membership)
    assert response.status_code == 204
    membership.refresh_from_db()
    assert membership.status == MembershipStatus.REMOVED
    assert membership.decided_by == membership.section.instructor
    entry = AuditLog.objects.get(action=Action.MEMBERSHIP_REMOVED)
    assert entry.before == {"status": "approved"}
    assert entry.after == {"status": "removed"}


def test_sec_07_foreign_instructor_cannot_move_or_remove() -> None:
    membership = _approved()
    stranger = make_instructor()
    own = make_section(instructor=stranger)
    assert _move(stranger, membership, own.pk).status_code == 404
    assert _remove(stranger, membership).status_code == 404
    membership.refresh_from_db()
    assert membership.status == MembershipStatus.APPROVED


def test_sec_07_membership_id_must_belong_to_url_section() -> None:
    membership = _approved()
    instructor = membership.section.instructor
    other_own = make_section(instructor=instructor)
    response = _client(instructor).post(
        f"/api/sections/{other_own.pk}/members/{membership.pk}/remove"
    )
    assert response.status_code == 404


def test_sec_07_student_cannot_move_self() -> None:
    membership = _approved()
    target = make_section(instructor=membership.section.instructor)
    assert _move(membership.student, membership, target.pk).status_code == 403
