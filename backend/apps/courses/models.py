"""Kurs kontenti (CNT-01, ADR-0002): Course → Topic → Lecture → LectureStep.

Manba — `content/` dagi fayllar; bazadagi nusxa `import_content` bilan yangilanadi.
"""

from __future__ import annotations

from typing import ClassVar

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Course(models.Model):
    slug = models.SlugField(_("slug"), max_length=50, unique=True)
    title = models.TextField(_("nomi"))
    version = models.CharField(_("kontent versiyasi"), max_length=32)
    content_hash = models.CharField(_("fayllar xeshi (SHA-256)"), max_length=64)
    imported_at = models.DateTimeField(_("import vaqti"), default=timezone.now)

    class Meta:
        verbose_name = _("kurs")
        verbose_name_plural = _("kurslar")
        constraints: ClassVar[list[models.BaseConstraint]] = [
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
    body = models.TextField(_("matn (Markdown)"))

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
