"""Kurs kontenti (CNT-01, ADR-0002): Course → Topic → Lecture → LectureStep.

Manba — `content/` dagi fayllar; bazadagi nusxa `import_content` bilan yangilanadi.
"""

from __future__ import annotations

from typing import ClassVar

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AiMode(models.TextChoices):
    """AI-01 rejimlari, kuchayish tartibida (chegara solishtirish shu tartib bo'yicha)."""

    OFF = "off", _("O'chiq")
    GUIDE = "guide", _("Yo'naltiruvchi")
    EXPLAIN = "explain", _("Tushuntirish")
    FULL = "full", _("To'liq yordam")


AI_MODE_ORDER = [AiMode.OFF, AiMode.GUIDE, AiMode.EXPLAIN, AiMode.FULL]
MAX_LATE_HOURS = 168  # 7 kun


class Course(models.Model):
    slug = models.SlugField(_("slug"), max_length=50, unique=True)
    title = models.TextField(_("nomi"))
    version = models.CharField(_("kontent versiyasi"), max_length=32)
    content_hash = models.CharField(_("fayllar xeshi (SHA-256)"), max_length=64)
    imported_at = models.DateTimeField(_("import vaqti"), default=timezone.now)
    # Kurs default sozlamalari (SET, `course.yaml` → `defaults:`); guruh override qiladi.
    ai_enabled = models.BooleanField(_("AI tutor yoqilgan"), default=True)
    ai_max_mode = models.CharField(
        _("AI maksimal rejimi"), max_length=16, choices=AiMode.choices, default=AiMode.EXPLAIN
    )
    practice_after_close = models.BooleanField(_("yopilgandan keyin mashq"), default=False)
    late_hours = models.PositiveSmallIntegerField(_("kechikish muddati (soat)"), default=0)
    late_penalty_percent = models.PositiveSmallIntegerField(_("kechikish jarimasi (%)"), default=0)
    chat_enabled = models.BooleanField(_("guruh chati"), default=True)

    class Meta:
        verbose_name = _("kurs")
        verbose_name_plural = _("kurslar")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(ai_max_mode__in=AiMode.values), name="courses_course_ai_mode"
            ),
            models.CheckConstraint(
                condition=Q(late_hours__lte=MAX_LATE_HOURS), name="courses_course_late_hours"
            ),
            models.CheckConstraint(
                condition=Q(late_penalty_percent__lte=100), name="courses_course_late_penalty"
            ),
            models.CheckConstraint(condition=Q(title__regex=r"\S"), name="courses_course_title"),
            models.CheckConstraint(
                condition=Q(content_hash__regex=r"^[0-9a-f]{64}$"), name="courses_course_hash"
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Topic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="topics")
    code = models.CharField(_("kod"), max_length=8)
    title = models.TextField(_("nomi"))
    order = models.PositiveSmallIntegerField(_("tartib"))

    class Meta:
        verbose_name = _("mavzu")
        verbose_name_plural = _("mavzular")
        ordering = ("order",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["course", "code"], name="courses_topic_code_uniq"),
            # DEFERRED: import mavzular tartibini almashtirsa (1<->2), oxirida tekshiriladi.
            models.UniqueConstraint(
                fields=["course", "order"],
                name="courses_topic_order_uniq",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(
                condition=Q(code__regex=r"^[A-Z][0-9]{2}$"), name="courses_topic_code_format"
            ),
            models.CheckConstraint(condition=Q(title__regex=r"\S"), name="courses_topic_title"),
        ]

    def __str__(self) -> str:
        return f"{self.code} {self.title}"


class Lecture(models.Model):
    topic = models.OneToOneField(Topic, on_delete=models.CASCADE, related_name="lecture")
    title = models.TextField(_("nomi"))

    class Meta:
        verbose_name = _("ma'ruza")
        verbose_name_plural = _("ma'ruzalar")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(condition=Q(title__regex=r"\S"), name="courses_lecture_title"),
        ]

    def __str__(self) -> str:
        return self.title


class LectureStep(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveSmallIntegerField(_("tartib"))
    title = models.TextField(_("sarlavha"))
    # Bo'sh bo'lishi mumkin, agar qadamda faqat tezkor savol bo'lsa (CNT-02).
    body = models.TextField(_("matn (Markdown)"), blank=True)
    # CNT-02 tezkor savol: {"question", "options": [..], "answer": indeks, "explain"}.
    # Baholanmaydi — shuning uchun to'g'ri javob talabaga ham beriladi (mijozda darhol
    # tekshiriladi). Shakli importda tekshiriladi.
    question = models.JSONField(_("tezkor savol"), null=True, blank=True)

    class Meta:
        verbose_name = _("ma'ruza qadami")
        verbose_name_plural = _("ma'ruza qadamlari")
        ordering = ("order",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["lecture", "order"], name="courses_step_order_uniq"),
            models.CheckConstraint(condition=Q(order__gte=1), name="courses_step_order_positive"),
            models.CheckConstraint(condition=Q(title__regex=r"\S"), name="courses_step_title"),
        ]

    def __str__(self) -> str:
        return f"{self.order}. {self.title}"


MAX_IMAGE_BYTES = 500 * 1024


class ImageType(models.TextChoices):
    PNG = "image/png", "PNG"
    JPEG = "image/jpeg", "JPEG"
    WEBP = "image/webp", "WebP"


class LectureImage(models.Model):
    """Ma'ruza rasmi (CNT-02). Baytlar bazada: kichik (<= 500 KB), zaxira (`deploy/backup.sh`) bilan
    birga saqlanadi va media volume kerak emas. SVG qabul qilinmaydi (skript ichishi mumkin)."""

    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="images", db_index=False
    )
    name = models.CharField(_("fayl nomi"), max_length=64)
    content_type = models.CharField(_("turi"), max_length=16, choices=ImageType.choices)
    sha256 = models.CharField(_("SHA-256"), max_length=64)
    size = models.PositiveIntegerField(_("hajmi (bayt)"))
    data = models.BinaryField(_("baytlar"))

    class Meta:
        verbose_name = _("ma'ruza rasmi")
        verbose_name_plural = _("ma'ruza rasmlari")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # Prefiks (topic) FK indeksini ham qoplaydi.
            models.UniqueConstraint(fields=["topic", "name"], name="courses_image_name_uniq"),
            models.CheckConstraint(
                condition=Q(name__regex=r"^[A-Za-z0-9_-]+\.(png|jpg|jpeg|webp)$"),
                name="courses_image_name_format",
            ),
            models.CheckConstraint(
                condition=Q(content_type__in=ImageType.values), name="courses_image_type"
            ),
            models.CheckConstraint(
                condition=Q(sha256__regex=r"^[0-9a-f]{64}$"), name="courses_image_sha256"
            ),
            models.CheckConstraint(
                condition=Q(size__gte=1, size__lte=MAX_IMAGE_BYTES), name="courses_image_size"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.topic_id}/{self.name}"
