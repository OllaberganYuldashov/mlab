"""Guruhlar va a'zolik (SEC, I1-01).

Invariantlar DB darajasida: nom kanonik (NFC, chetida bo'sh joy yo'q), sig'im 1..500,
talabada bir vaqtda ko'pi bilan bitta faol (`pending`/`approved`) a'zolik (SEC-07),
qaror maydonlari holatga mos. A'zolik tarixi o'chirilmaydi (`removed`/`rejected` qoladi).
Rol tekshiruvi (egasi — o'qituvchi, a'zo — talaba) jadvallararo bo'lgani uchun `save()` da.
"""

from __future__ import annotations

from typing import Any, ClassVar

from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Direction, Role, User, _is_canonical_text, normalize_full_name
from apps.courses.models import Course

MIN_CAPACITY = 1
MAX_CAPACITY = 500
DEFAULT_CAPACITY = 30


class Section(models.Model):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="sections")
    # db_index=False: `sections_by_instructor` indeksining prefiksi FK indeksini takrorlaydi.
    instructor = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="sections", db_index=False
    )
    direction = models.ForeignKey(Direction, on_delete=models.PROTECT, related_name="sections")
    name = models.TextField(_("nomi"))
    capacity = models.PositiveSmallIntegerField(_("sig'im"), default=DEFAULT_CAPACITY)
    join_enabled = models.BooleanField(_("qo'shilish yoqilgan"), default=True)
    created_at = models.DateTimeField(_("yaratilgan"), db_default=Now())
    updated_at = models.DateTimeField(_("yangilangan"), auto_now=True)

    class Meta:
        verbose_name = _("guruh")
        verbose_name_plural = _("guruhlar")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(name__regex=r"\S") & _is_canonical_text("name"),
                name="sections_section_name",
            ),
            models.CheckConstraint(
                condition=Q(capacity__gte=MIN_CAPACITY) & Q(capacity__lte=MAX_CAPACITY),
                name="sections_section_capacity",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            # Ro'yxat: o'qituvchining guruhlari, yangisi birinchi (keyset — `id` bo'yicha).
            models.Index(fields=["instructor", "-id"], name="sections_by_instructor_id"),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = normalize_full_name(self.name)
        if self.instructor.role != Role.INSTRUCTOR:
            raise ValueError("Guruh egasi faqat o'qituvchi bo'lishi mumkin.")
        super().save(*args, **kwargs)


class MembershipStatus(models.TextChoices):
    PENDING = "pending", _("Kutilmoqda")
    APPROVED = "approved", _("Tasdiqlangan")
    REJECTED = "rejected", _("Rad etilgan")
    REMOVED = "removed", _("Chiqarilgan")


ACTIVE_STATUSES = (MembershipStatus.PENDING, MembershipStatus.APPROVED)
DECIDER_ROLES = frozenset({Role.INSTRUCTOR, Role.ADMIN, Role.SUPER_ADMIN})


class MembershipQuerySet(models.QuerySet["Membership"]):
    def active(self) -> MembershipQuerySet:
        return self.filter(status__in=ACTIVE_STATUSES)

    def approved(self) -> MembershipQuerySet:
        return self.filter(status=MembershipStatus.APPROVED)


class Membership(models.Model):
    student = models.ForeignKey(User, on_delete=models.PROTECT, related_name="memberships")
    # db_index=False: `sections_members_by_status` prefiksi FK indeksini takrorlaydi.
    section = models.ForeignKey(
        Section, on_delete=models.PROTECT, related_name="memberships", db_index=False
    )
    status = models.CharField(
        _("holat"),
        max_length=16,
        choices=MembershipStatus.choices,
        default=MembershipStatus.PENDING,
    )
    requested_at = models.DateTimeField(_("so'ralgan"), db_default=Now())
    decided_at = models.DateTimeField(_("qaror vaqti"), null=True, blank=True)
    decided_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    objects = MembershipQuerySet.as_manager()

    class Meta:
        verbose_name = _("a'zolik")
        verbose_name_plural = _("a'zoliklar")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # SEC-07: bitta faol guruh. Partial unique — tarixdagi rad/chiqarilganlar cheklanmaydi.
            models.UniqueConstraint(
                fields=["student"],
                condition=Q(status__in=ACTIVE_STATUSES),
                name="sections_membership_one_active",
            ),
            models.CheckConstraint(
                condition=Q(status__in=MembershipStatus.values),
                name="sections_membership_status",
            ),
            # Kutilayotgan so'rovda qaror yo'q; qolganlarida qaror vaqti va kim qaror qilgani bor.
            models.CheckConstraint(
                condition=(
                    Q(status=MembershipStatus.PENDING)
                    & Q(decided_at__isnull=True)
                    & Q(decided_by__isnull=True)
                )
                | (
                    ~Q(status=MembershipStatus.PENDING)
                    & Q(decided_at__isnull=False)
                    & Q(decided_by__isnull=False)
                ),
                name="sections_membership_decision",
            ),
            models.CheckConstraint(
                condition=Q(decided_at__isnull=True) | Q(decided_at__gte=models.F("requested_at")),
                name="sections_membership_decided_after_request",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["section", "status", "id"], name="sections_members_by_status"),
        ]

    def __str__(self) -> str:
        return f"{self.student_id} → {self.section_id} ({self.status})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.student.role != Role.STUDENT:
            raise ValueError("Guruh a'zosi faqat talaba bo'lishi mumkin.")
        if self.decided_by is not None and self.decided_by.role not in DECIDER_ROLES:
            raise ValueError("A'zolik bo'yicha qarorni faqat o'qituvchi yoki admin qiladi.")
        super().save(*args, **kwargs)
