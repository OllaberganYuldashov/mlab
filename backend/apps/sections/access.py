"""Kursga kirish (SEC-05): tasdiqlangan a'zo kursga avtomatik yozilgan — alohida obuna yo'q."""

from __future__ import annotations

from apps.accounts.models import Role, User
from apps.courses.models import Course
from apps.sections.models import Membership, Section


def can_access_course(user: User, course: Course) -> bool:
    if not user.is_active:
        return False
    if user.role in (Role.ADMIN, Role.SUPER_ADMIN):
        return True
    if user.role == Role.INSTRUCTOR:
        return Section.objects.filter(instructor=user, course=course).exists()
    return Membership.objects.approved().filter(student=user, section__course=course).exists()
