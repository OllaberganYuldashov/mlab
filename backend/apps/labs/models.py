"""Laboratoriya ishi (LAB-05): talaba x guruh x mavzu uchun bitta yozuv.

`version` — optimistik qulf.
"""

from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q
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
