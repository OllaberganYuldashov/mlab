"""Amaliy topshiriqlar (AGR-07; I3-02). Manba — `content/labs/<A##>-<slug>/`.

Yashirin testlar (`TestFile.kind = hidden`) faqat serverda: hech qaysi talaba API'si ularni
qaytarmaydi (AGR-05).
"""

from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.courses.models import Course


class Level(models.TextChoices):
    BASIC = "basic", _("asosiy")
    MEDIUM = "medium", _("o'rta")
    ADVANCED = "advanced", _("ilg'or")


class Assignment(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="assignments", db_index=False
    )
    code = models.CharField(_("kod"), max_length=3)
    title = models.TextField(_("nomi"))
    topic_code = models.CharField(_("mavzu"), max_length=3)
    statement = models.TextField(_("shart (Markdown, {parametr} bilan)"))
    challenge = models.TextField(_("challenge"), blank=True)
    independent = models.TextField(_("mustaqil topshiriq"), blank=True)

    class Meta:
        verbose_name = _("topshiriq")
        verbose_name_plural = _("topshiriqlar")
        ordering = ("code",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["course", "code"], name="grading_assignment_code_uniq"),
            models.CheckConstraint(
                condition=Q(code__regex=r"^A[0-9]{2}$"), name="grading_assignment_code"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} {self.title}"


class AssignmentStep(models.Model):
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="steps", db_index=False
    )
    order = models.PositiveSmallIntegerField(_("tartib"))
    key = models.CharField(_("kalit"), max_length=32)
    title = models.TextField(_("sarlavha"))
    points = models.PositiveSmallIntegerField(_("ball"))

    class Meta:
        verbose_name = _("topshiriq qadami")
        verbose_name_plural = _("topshiriq qadamlari")
        ordering = ("assignment", "order")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["assignment", "key"], name="grading_step_key_uniq"),
            # DEFERRED: import qadamlar tartibini almashtirsa, tekshiruv tranzaksiya oxirida.
            models.UniqueConstraint(
                fields=["assignment", "order"],
                name="grading_step_order_uniq",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(
                condition=Q(points__gte=1, points__lte=100), name="grading_step_points"
            ),
            models.CheckConstraint(
                condition=Q(key__regex=r"^[a-z][a-z0-9_]{0,31}$"), name="grading_step_key"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.assignment_id}/{self.key}"


class Variant(models.Model):
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="variants", db_index=False
    )
    level = models.CharField(_("daraja"), max_length=8, choices=Level.choices)
    number = models.PositiveSmallIntegerField(_("raqam"))
    params = models.JSONField(_("parametrlar"))

    class Meta:
        verbose_name = _("variant")
        verbose_name_plural = _("variantlar")
        ordering = ("assignment", "level", "number")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["assignment", "level", "number"], name="grading_variant_uniq"
            ),
            models.CheckConstraint(
                condition=Q(level__in=Level.values), name="grading_variant_level"
            ),
            models.CheckConstraint(condition=Q(number__gte=1), name="grading_variant_number"),
        ]

    def __str__(self) -> str:
        return f"{self.assignment_id}/{self.level}-{self.number}"


class TestKind(models.TextChoices):
    __test__ = False  # pytest buni test klassi deb yig'masin

    VISIBLE = "visible", _("ko'rinadigan")
    HIDDEN = "hidden", _("yashirin")


class TestFile(models.Model):
    __test__ = False  # pytest buni test klassi deb yig'masin

    step = models.ForeignKey(
        AssignmentStep, on_delete=models.CASCADE, related_name="tests", db_index=False
    )
    kind = models.CharField(_("turi"), max_length=8, choices=TestKind.choices)
    source = models.TextField(_("Python kodi"))

    class Meta:
        verbose_name = _("test fayli")
        verbose_name_plural = _("test fayllari")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["step", "kind"], name="grading_test_uniq"),
            models.CheckConstraint(condition=Q(kind__in=TestKind.values), name="grading_test_kind"),
        ]

    def __str__(self) -> str:
        return f"{self.step_id}/{self.kind}"


class StudentAssignmentStatus(models.TextChoices):
    ASSIGNED = "assigned", _("berilgan")
    SUBMITTED = "submitted", _("topshirilgan")


class LevelSource(models.TextChoices):
    RULE = "rule", _("qoida bo'yicha")
    INSTRUCTOR = "instructor", _("o'qituvchi tanlagan")


class StudentAssignment(models.Model):
    """Talaba x topshiriq (AGR-08, INT-03): daraja va variant bir marta tanlanadi va saqlanadi.

    Variant `apps.grading.variants.assign()` da HMAC bilan tanlanadi, keyin saqlangani ishlatiladi —
    kontentga variant qo'shilsa yoki kalit almashsa ham talabaning varianti o'zgarmaydi.
    `seed` — dataset qismini tanlash uchun (masalan, qatorlar namunasi), variantdan mustaqil.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_assignments",
        db_index=False,
    )
    # PROTECT: talabaga berilgan topshiriq/variant import bilan jim o'chmasin (import xato beradi).
    assignment = models.ForeignKey(
        Assignment, on_delete=models.PROTECT, related_name="student_assignments"
    )
    variant = models.ForeignKey(
        Variant, on_delete=models.PROTECT, related_name="student_assignments"
    )
    level = models.CharField(_("daraja"), max_length=8, choices=Level.choices)
    # ADP-01/02: daraja qoida bo'yicha (birinchi ochilishda) yoki o'qituvchi qo'lda o'zgartirgan.
    level_source = models.CharField(
        _("daraja manbai"), max_length=10, choices=LevelSource.choices, default=LevelSource.RULE
    )
    seed = models.PositiveIntegerField(_("dataset seed"))
    status = models.CharField(
        _("holat"),
        max_length=16,
        choices=StudentAssignmentStatus.choices,
        default=StudentAssignmentStatus.ASSIGNED,
    )
    created_at = models.DateTimeField(_("berilgan vaqt"), default=timezone.now)

    class Meta:
        verbose_name = _("talaba topshirig'i")
        verbose_name_plural = _("talaba topshiriqlari")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # Prefiks (student) FK indeksini ham qoplaydi; ikki tab bir vaqtda ochsa — bitta yozuv.
            models.UniqueConstraint(
                fields=["student", "assignment"], name="grading_student_assignment_uniq"
            ),
            models.CheckConstraint(
                condition=Q(level__in=Level.values), name="grading_student_assignment_level"
            ),
            models.CheckConstraint(
                condition=Q(status__in=StudentAssignmentStatus.values),
                name="grading_student_assignment_status",
            ),
            models.CheckConstraint(
                condition=Q(level_source__in=LevelSource.values),
                name="grading_student_assignment_level_source",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_id}/{self.assignment_id} {self.level}"


class SubmissionStatus(models.TextChoices):
    QUEUED = "queued", _("navbatda")
    RUNNING = "running", _("tekshirilmoqda")
    DONE = "done", _("baholandi")
    ERROR = "error", _("xato")


class SubmissionPolicy(models.TextChoices):
    """ACC-06..08: topshirish paytidagi siyosat (`sections.policy.submission_policy`)."""

    ON_TIME = "on_time", _("o'z vaqtida")
    LATE = "late", _("kechikkan")
    PRACTICE = "practice", _("mashq (rasmiy emas)")


class Submission(models.Model):
    """Topshirilgan kod va uning bahosi (AGR-02, AGR-04, AGR-06; I3-06).

    Holat faqat oldinga: `queued → running → done | error`. Infratuzilma xatosida (sandbox javob
    bermadi) `running → queued` qaytadi va qayta uriniladi; talaba kodi xatosi — `done` (0 ball).
    Har urinish alohida yozuv (AGR-06): eng yuqori ball — I3-08.
    """

    student_assignment = models.ForeignKey(
        StudentAssignment,
        on_delete=models.PROTECT,
        related_name="submissions",
        db_index=False,  # (student_assignment, created_at) indeksi prefiks sifatida qoplaydi
    )
    code = models.TextField(_("kod"))
    status = models.CharField(
        _("holat"),
        max_length=8,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.QUEUED,
    )
    score = models.PositiveSmallIntegerField(_("ball"), null=True, blank=True)
    result = models.JSONField(_("natija"), null=True, blank=True)
    error = models.CharField(_("infratuzilma xatosi"), max_length=32, blank=True)
    attempts = models.PositiveSmallIntegerField(_("urinishlar"), default=0)
    policy = models.CharField(
        _("siyosat"),
        max_length=8,
        choices=SubmissionPolicy.choices,
        default=SubmissionPolicy.ON_TIME,
    )
    # Topshirish paytidagi jarima foizi (keyin kurs sozlamasi o'zgarsa ham ball o'zgarmaydi).
    penalty_percent = models.PositiveSmallIntegerField(_("kechikish jarimasi, %"), default=0)
    # ACC-07: jarimadan keyingi ball, Decimal(5,2) (float yo'q). Rasmiy — faqat policy != practice.
    final_score = models.DecimalField(
        _("yakuniy ball"), max_digits=5, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(_("topshirilgan"), default=timezone.now)
    started_at = models.DateTimeField(_("boshlangan"), null=True, blank=True)
    finished_at = models.DateTimeField(_("tugagan"), null=True, blank=True)

    class Meta:
        verbose_name = _("topshirish")
        verbose_name_plural = _("topshirishlar")
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["student_assignment", "created_at"], name="grading_submission_sa_created"
            ),
            # Navbat uzunligi va "osilib qolgan" yozuvlarni qayta navbatga qo'yish uchun.
            models.Index(
                fields=["created_at"],
                name="grading_submission_pending",
                condition=Q(status__in=["queued", "running"]),
            ),
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(status__in=SubmissionStatus.values), name="grading_submission_status"
            ),
            models.CheckConstraint(
                condition=Q(score__isnull=True) | Q(score__lte=100),
                name="grading_submission_score",
            ),
            models.CheckConstraint(
                condition=~Q(status="done")
                | Q(score__isnull=False, result__isnull=False, finished_at__isnull=False),
                name="grading_submission_done_complete",
            ),
            models.CheckConstraint(
                condition=~Q(status="error") | (Q(finished_at__isnull=False) & ~Q(error="")),
                name="grading_submission_error_reason",
            ),
            models.CheckConstraint(
                condition=~Q(status="running") | Q(started_at__isnull=False),
                name="grading_submission_running_started",
            ),
            models.CheckConstraint(
                condition=Q(policy__in=SubmissionPolicy.values), name="grading_submission_policy"
            ),
            models.CheckConstraint(
                condition=Q(penalty_percent__lte=100), name="grading_submission_penalty"
            ),
            models.CheckConstraint(
                condition=Q(final_score__isnull=True) | Q(final_score__gte=0, final_score__lte=100),
                name="grading_submission_final_score",
            ),
            models.CheckConstraint(
                condition=~Q(status="done") | Q(final_score__isnull=False),
                name="grading_submission_done_final",
            ),
            # AGR-02: bir topshiriqda bir vaqtda bitta ochiq urinish (ikki tab, ikki marta bosish).
            models.UniqueConstraint(
                fields=["student_assignment"],
                condition=Q(status__in=["queued", "running"]),
                name="grading_submission_one_open",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.pk} {self.status}"
