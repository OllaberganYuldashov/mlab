"""Audit jurnali (ADM-02): kim, nima, qachon, qaysi obyekt, oldingi va yangi qiymat.

Faqat qo'shiladi (append-only): model, QuerySet va DB trigger darajasida yangilash va
o'chirish taqiqlangan.
Yozish faqat `apps.audit.record(...)` orqali — u secret maydonlarni olib tashlaydi.
"""

from __future__ import annotations

from typing import Any, ClassVar, NoReturn

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.utils.translation import gettext_lazy as _


class AppendOnlyError(Exception):
    """Audit yozuvini o'zgartirish yoki o'chirishga urinish."""


class Action(models.TextChoices):
    LOGIN = "login", _("Kirish")
    LOGIN_FAILED = "login_failed", _("Muvaffaqiyatsiz kirish")
    LOGOUT = "logout", _("Chiqish")
    ROLE_CHANGED = "role_changed", _("Rol o'zgardi")
    USER_ACTIVE_CHANGED = "user_active_changed", _("Akkaunt faolligi o'zgardi")
    PASSWORD_RESET = "password_reset", _("Parol tiklandi")
    PASSWORD_CHANGED = "password_changed", _("Parol almashtirildi")
    INSTRUCTOR_CREATED = "instructor_created", _("O'qituvchi akkaunti yaratildi")
    STUDENT_LIMIT_CHANGED = "student_limit_changed", _("Talaba limiti o'zgardi")
    GRADE_CHANGED = "grade_changed", _("Baho o'zgardi")
    ACCESS_WINDOW_CHANGED = "access_window_changed", _("Kirish oynasi o'zgardi")


class AuditLogQuerySet(models.QuerySet["AuditLog"]):
    def update(self, **kwargs: Any) -> NoReturn:
        raise AppendOnlyError("Audit jurnali o'zgartirilmaydi.")

    def delete(self) -> NoReturn:
        raise AppendOnlyError("Audit jurnali o'chirilmaydi.")


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # tarixi bor foydalanuvchi izsiz o'chirilmaydi
        null=True,  # null — tizim harakati
        blank=True,
        related_name="+",
        db_index=False,  # (actor, created_at) indeksi yetarli
        verbose_name=_("kim"),
    )
    action = models.CharField(_("harakat"), max_length=32, choices=Action.choices)
    target_type = models.CharField(_("obyekt turi"), max_length=100)
    target_id = models.CharField(_("obyekt id"), max_length=64)
    before = models.JSONField(_("oldin"), default=dict, encoder=DjangoJSONEncoder)
    after = models.JSONField(_("keyin"), default=dict, encoder=DjangoJSONEncoder)
    request_id = models.CharField(_("so'rov id"), max_length=64, default="", blank=True)
    created_at = models.DateTimeField(_("vaqt"), db_default=Now(), editable=False)

    objects: ClassVar[models.Manager[AuditLog]] = AuditLogQuerySet.as_manager()

    class Meta:
        verbose_name = _("audit yozuvi")
        verbose_name_plural = _("audit jurnali")
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["target_type", "target_id", "created_at"], name="audit_target_created_idx"
            ),
            models.Index(fields=["actor", "created_at"], name="audit_actor_created_idx"),
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(action__in=Action.values), name="audit_auditlog_action_valid"
            ),
        ]

    def __str__(self) -> str:
        return f"AuditLog#{self.pk} {self.action} {self.target_type}#{self.target_id}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise AppendOnlyError("Audit jurnali o'zgartirilmaydi.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise AppendOnlyError("Audit jurnali o'chirilmaydi.")
