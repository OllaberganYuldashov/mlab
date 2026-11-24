"""Amaliy topshiriqlar (AGR-07; I3-02). Manba — `content/labs/<A##>-<slug>/`.

Yashirin testlar (`TestFile.kind = hidden`) faqat serverda: hech qaysi talaba API'si ularni
qaytarmaydi (AGR-05).
"""

from __future__ import annotations

from typing import ClassVar

from django.db import models
from django.db.models import Q
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
