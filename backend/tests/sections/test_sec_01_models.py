"""SEC-01, SEC-07, SET-03 (I1-01): guruh va a'zolik invariantlari — DB darajasida."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Role
from apps.sections.models import Membership, MembershipStatus, Section
from tests.accounts.factories import make_direction, make_user
from tests.sections.factories import make_course, make_instructor, make_membership, make_section

pytestmark = pytest.mark.django_db


def _bulk_section(**overrides: Any) -> None:
    fields: dict[str, Any] = {
        "course": make_course(),
        "instructor": make_instructor(),
        "direction": make_direction(),
        "name": "Guruh",
    }
    fields.update(overrides)
    with transaction.atomic():
        Section.objects.bulk_create([Section(**fields)])  # save()'ni aylanib o'tadi


# --- Section ---


def test_sec_01_section_defaults() -> None:
    section = make_section()
    assert section.capacity == 30
    assert section.join_enabled is True
    assert section.created_at is not None
    assert section.updated_at is not None


def test_sec_01_section_name_normalized_nfc_and_stripped() -> None:
    section = make_section(name="  Guruh ó  ")
    section.refresh_from_db()
    assert section.name == "Guruh ó"


@pytest.mark.parametrize("name", ["", "   ", " Guruh", "ó"])
def test_sec_01_section_name_must_be_canonical_at_db_level(name: str) -> None:
    with pytest.raises(IntegrityError):
        _bulk_section(name=name)


@pytest.mark.parametrize("capacity", [0, -1, 501])
def test_sec_01_capacity_range_at_db_level(capacity: int) -> None:
    with pytest.raises(IntegrityError):
        _bulk_section(capacity=capacity)


@pytest.mark.parametrize("capacity", [1, 500])
def test_sec_01_capacity_bounds_allowed(capacity: int) -> None:
    assert make_section(capacity=capacity).capacity == capacity


def test_sec_01_only_instructor_can_own_section() -> None:
    for role in (Role.STUDENT, Role.ADMIN, Role.SUPER_ADMIN):
        user = make_user(role=role, is_superuser=role == Role.SUPER_ADMIN)
        with pytest.raises(ValueError, match="o'qituvchi"):
            make_section(instructor=user)


def test_sec_01_instructor_and_course_protected_from_delete() -> None:
    from django.db.models import ProtectedError

    section = make_section()
    with pytest.raises(ProtectedError):
        section.instructor.delete()
    with pytest.raises(ProtectedError):
        section.course.delete()


# --- Membership ---


def test_sec_07_membership_defaults_pending() -> None:
    membership = make_membership()
    assert membership.status == MembershipStatus.PENDING
    assert membership.requested_at is not None
    assert membership.decided_at is None


def test_sec_07_only_students_can_be_members() -> None:
    for role in (Role.INSTRUCTOR, Role.ADMIN):
        with pytest.raises(ValueError, match="talaba"):
            make_membership(student=make_user(role=role, direction=None))


def test_sec_07_one_active_membership_per_student_at_db_level() -> None:
    student = make_user()
    make_membership(student=student)
    other = make_section()
    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.bulk_create([Membership(student=student, section=other)])
    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.bulk_create(
            [
                Membership(
                    student=student,
                    section=other,
                    status=MembershipStatus.APPROVED,
                    decided_at=timezone.now(),
                    decided_by=other.instructor,
                )
            ]
        )


def test_sec_07_history_allows_new_request_after_reject_or_remove() -> None:
    student = make_user()
    first = make_membership(student=student)
    first.status = MembershipStatus.REJECTED
    first.decided_at = timezone.now()
    first.decided_by = first.section.instructor
    first.save()
    second = make_membership(student=student, section=first.section)
    second.status = MembershipStatus.REMOVED
    second.decided_at = timezone.now()
    second.decided_by = second.section.instructor
    second.save()
    make_membership(student=student)  # yana faol so'rov — ruxsat
    assert Membership.objects.filter(student=student).count() == 3


@pytest.mark.parametrize(
    ("status", "decided"),
    [
        (MembershipStatus.PENDING, True),
        (MembershipStatus.APPROVED, False),
        (MembershipStatus.REJECTED, False),
    ],
)
def test_sec_07_decision_fields_consistent_with_status(
    status: MembershipStatus, decided: bool
) -> None:
    section = make_section()
    fields: dict[str, Any] = {"student": make_user(), "section": section, "status": status}
    if decided:
        fields.update(decided_at=timezone.now(), decided_by=section.instructor)
    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.bulk_create([Membership(**fields)])


def test_sec_07_invalid_status_rejected_at_db_level() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.bulk_create(
            [Membership(student=make_user(), section=make_section(), status="banned")]
        )


def test_sec_07_membership_rows_protected_from_cascade() -> None:
    from django.db.models import ProtectedError

    membership = make_membership()
    with pytest.raises(ProtectedError):
        membership.section.delete()
    with pytest.raises(ProtectedError):
        membership.student.delete()


def test_sec_07_active_members_query_uses_index_friendly_filter() -> None:
    section = make_section()
    approved = make_membership(section=section)
    approved.status = MembershipStatus.APPROVED
    approved.decided_at = timezone.now()
    approved.decided_by = section.instructor
    approved.save()
    make_membership(section=section)
    assert list(Membership.objects.approved().filter(section=section)) == [approved]
    assert Membership.objects.active().filter(section=section).count() == 2
