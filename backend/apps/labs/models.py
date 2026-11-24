"""Laboratoriya ishi (LAB-05): talaba x guruh x mavzu uchun bitta yozuv.

`version` — optimistik qulf.
"""

from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class LabWork(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="lab_works", db_index=False
    )
    section = models.ForeignKey(
        "sections.Section", on_delete=models.PROTECT, related_name="lab_works"
    )
    topic = models.ForeignKey("courses.Topic", on_delete=models.PROTECT, related_name="lab_works")
    notebook = models.JSONField(_("notebook"))
    version = models.PositiveIntegerField(_("versiya"), default=1)
    saved_at = models.DateTimeField(_("saqlangan"), auto_now=True)

    class Meta:
        verbose_name = _("laboratoriya ishi")
        verbose_name_plural = _("laboratoriya ishlari")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # Prefiks (student) FK indeksini ham qoplaydi.
            models.UniqueConstraint(fields=["student", "section", "topic"], name="labs_work_uniq"),
            models.CheckConstraint(condition=Q(version__gte=1), name="labs_work_version"),
        ]

    def __str__(self) -> str:
        return f"{self.student_id}/{self.section_id}/{self.topic_id} v{self.version}"


class LabEventKind(models.TextChoices):
    PASTE = "paste", _("Joylashtirish")
    PASTE_BLOCKED = "paste_blocked", _("Joylashtirish rad etildi")


class LabEvent(models.Model):
    """INT-01, RPT-03: laboratoriya hodisasi (hozircha paste). Matn emas — faqat hajmi."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lab_events",
        db_index=False,
    )
    section = models.ForeignKey(
        "sections.Section", on_delete=models.PROTECT, related_name="lab_events", db_index=False
    )
    topic = models.ForeignKey(
        "courses.Topic", on_delete=models.PROTECT, related_name="lab_events", db_index=False
    )
    kind = models.CharField(_("tur"), max_length=16, choices=LabEventKind.choices)
    size = models.PositiveIntegerField(_("hajm (belgi)"))
    cell = models.CharField(_("katak"), max_length=64)
    at = models.DateTimeField(_("vaqt"), default=timezone.now)

    class Meta:
        verbose_name = _("laboratoriya hodisasi")
        verbose_name_plural = _("laboratoriya hodisalari")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(kind__in=LabEventKind.values), name="labs_event_kind"
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            # Talabaning o'z hodisalari va o'qituvchining guruh x mavzu ro'yxati (I3-14).
            models.Index(fields=["student", "topic", "at"], name="labs_event_student"),
            models.Index(fields=["section", "topic", "at"], name="labs_event_section"),
            models.Index(fields=["topic"], name="labs_event_topic"),
        ]

    def __str__(self) -> str:
        return f"{self.student_id}/{self.topic_id} {self.kind} {self.size}"
