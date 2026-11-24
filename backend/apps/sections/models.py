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
from apps.courses.models import MAX_LATE_HOURS, AiMode, Course

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
    # SEC-02: faqat SHA-256 xeshi (apps/sections/tokens.py). NULL — havola o'chirilgan/yaratilmagan.
    join_token_hash = models.CharField(
        _("qo'shilish tokeni xeshi"), max_length=64, null=True, blank=True, unique=True
    )
    # SET-01..05: guruh override'lari. NULL — kurs qiymati (`apps/sections/settings.py`).
    # Kechikish jarimasi foizi faqat kurs darajasida (ACC-07) — bu yerda yo'q.
    ai_enabled = models.BooleanField(_("AI tutor"), null=True, blank=True)
    # DJ001: NULL ataylab — "kurs qiymati" ma'nosida (bo'sh satrdan farqli).
    ai_max_mode = models.CharField(  # noqa: DJ001
        _("AI maksimal rejimi"), max_length=16, choices=AiMode.choices, null=True, blank=True
    )
    practice_after_close = models.BooleanField(_("yopilgandan keyin mashq"), null=True, blank=True)
    late_hours = models.PositiveSmallIntegerField(_("kechikish (soat)"), null=True, blank=True)
    chat_enabled = models.BooleanField(_("guruh chati"), null=True, blank=True)
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
            models.CheckConstraint(
                condition=Q(ai_max_mode__isnull=True) | Q(ai_max_mode__in=AiMode.values),
                name="sections_section_ai_mode",
            ),
            models.CheckConstraint(
                condition=Q(late_hours__isnull=True) | Q(late_hours__lte=MAX_LATE_HOURS),
                name="sections_section_late_hours",
            ),
            models.CheckConstraint(
                condition=Q(join_token_hash__isnull=True)
                | Q(join_token_hash__regex=r"^[0-9a-f]{64}$"),  # noqa: S106 — regex, secret emas
                name="sections_section_token_hash",
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


class WindowMode(models.TextChoices):
    """ACC-03: Yopiq; Hozir ochish (qo'lda yoki N daqiqadan keyin yopiladi); Jadval."""

    CLOSED = "closed", _("Yopiq")
    OPEN_NOW = "open_now", _("Hozir ochiq")
    SCHEDULED = "scheduled", _("Jadval bo'yicha")


class AccessWindow(models.Model):
    """Guruh x mavzu laboratoriyasiga kirish oynasi (ACC-02). Yo'q bo'lsa — yopiq.

    Vaqtlar `timestamptz` (UTC'da saqlanadi), Asia/Tashkent'da ko'rsatiladi. Holat faqat
    `apps.sections.windows.window_state()` orqali hisoblanadi.
    """

    # db_index=False: `sections_window_uniq (section, topic)` prefiksi shu FK'ni qoplaydi
    # (I1-15 sxema ko'rigi).
    section = models.ForeignKey(
        Section, on_delete=models.PROTECT, related_name="windows", db_index=False
    )
    topic = models.ForeignKey(
        "courses.Topic", on_delete=models.PROTECT, related_name="access_windows"
    )
    mode = models.CharField(
        _("rejim"), max_length=16, choices=WindowMode.choices, default=WindowMode.CLOSED
    )
    opens_at = models.DateTimeField(_("ochilish"), null=True, blank=True)
    closes_at = models.DateTimeField(_("yopilish"), null=True, blank=True)
    # ACC-09: nazorat rejimi (AI o'chadi, paste taqiq, tab qaydi) — amalda I2-I4 modullari o'qiydi.
    proctored = models.BooleanField(_("nazorat rejimi"), default=False)
    updated_at = models.DateTimeField(_("yangilangan"), auto_now=True)

    class Meta:
        verbose_name = _("kirish oynasi")
        verbose_name_plural = _("kirish oynalari")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # Prefiks (section) FK indeksini ham almashtiradi.
            models.UniqueConstraint(fields=["section", "topic"], name="sections_window_uniq"),
            models.CheckConstraint(
                condition=Q(mode__in=WindowMode.values), name="sections_window_mode"
            ),
            models.CheckConstraint(
                condition=(
                    Q(mode=WindowMode.CLOSED) & Q(opens_at__isnull=True) & Q(closes_at__isnull=True)
                )
                | (Q(mode=WindowMode.OPEN_NOW) & Q(opens_at__isnull=False))
                | (
                    Q(mode=WindowMode.SCHEDULED)
                    & Q(opens_at__isnull=False)
                    & Q(closes_at__isnull=False)
                ),
                name="sections_window_mode_fields",
            ),
            models.CheckConstraint(
                condition=Q(closes_at__isnull=True)
                | Q(opens_at__isnull=True)
                | Q(closes_at__gt=models.F("opens_at")),
                name="sections_window_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.section_id}/{self.topic_id}: {self.mode}"


class IndependentDeadline(models.Model):
    """ACC-10: mustaqil topshiriq (A01..A15) uchun guruh bo'yicha topshirish muddati."""

    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="deadlines")
    # Topshiriqlar modeli I3 da — hozircha kod (A01..A99) bo'yicha bog'lanadi.
    assignment = models.CharField(_("topshiriq kodi"), max_length=3)
    due_at = models.DateTimeField(_("muddat"))
    updated_at = models.DateTimeField(_("yangilangan"), auto_now=True)

    class Meta:
        verbose_name = _("mustaqil topshiriq muddati")
        verbose_name_plural = _("mustaqil topshiriq muddatlari")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["section", "assignment"], name="sections_deadline_uniq"
            ),
            models.CheckConstraint(
                condition=Q(assignment__regex=r"^A(0[1-9]|[1-9][0-9])$"),
                name="sections_deadline_code",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.section_id}/{self.assignment}: {self.due_at}"
