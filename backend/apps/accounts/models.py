"""Foydalanuvchi va yo'nalish (AUTH-01, AUTH-03; SRS 2.2 rollar).

Invariantlar DB darajasida (CHECK/UNIQUE/FK), chunki `bulk_create`, migratsiya yoki
qo'lda SQL ilova tekshiruvlarini aylanib o'tadi.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Egasining qarori (#8): Hemis ID — 12 xonali, faqat ASCII raqamlar.
HEMIS_ID_RE = re.compile(r"^[0-9]{12}\Z")
HEMIS_ID_DB_REGEX = r"^[0-9]{12}$"


def normalize_hemis_id(raw: str) -> str:
    """Kiritishdagi bo'sh joylarni olib tashlaydi va formatni tekshiradi."""
    value = "".join(str(raw).split())
    if not HEMIS_ID_RE.match(value):
        raise ValueError("Hemis ID 12 ta raqamdan iborat bo'lishi kerak.")
    return value


def normalize_full_name(raw: str) -> str:
    """NFC (bir xil ko'rinadigan matn bir xil baytlar) va chetdagi bo'sh joylarsiz.

    Apostrof variantlari (U+0027, U+02BB, U+02BC, U+2018) o'zgartirilmaydi:
    talaba kiritganini ko'radi.
    Qidiruv uchun kanonik shakl kerak bo'lsa, u alohida qilinadi.
    """
    return unicodedata.normalize("NFC", raw).strip()


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", _("Super admin")
    ADMIN = "admin", _("Admin")
    INSTRUCTOR = "instructor", _("O'qituvchi")
    STUDENT = "student", _("Talaba")


STAFF_ROLES = frozenset({Role.SUPER_ADMIN, Role.ADMIN})


class Direction(models.Model):
    """Ta'lim yo'nalishi — ro'yxatni admin yuritadi, talaba undan tanlaydi."""

    name = models.TextField(_("nomi"), unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("yo'nalish")
        verbose_name_plural = _("yo'nalishlar")
        ordering = ("name",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(name__regex=r"\S"), name="accounts_direction_name_not_blank"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def _create(self, hemis_id: str, password: str | None, **extra: Any) -> User:
        user = self.model(hemis_id=normalize_hemis_id(hemis_id), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, hemis_id: str, password: str | None = None, **extra: Any) -> User:
        extra.setdefault("role", Role.STUDENT)
        extra["is_superuser"] = False
        return self._create(hemis_id, password, **extra)

    def create_superuser(self, hemis_id: str, password: str | None = None, **extra: Any) -> User:
        extra["role"] = Role.SUPER_ADMIN
        extra["is_superuser"] = True
        extra.setdefault("direction", None)
        return self._create(hemis_id, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    hemis_id = models.CharField(_("Hemis ID"), max_length=12, unique=True)
    full_name = models.TextField(_("FIO"))
    role = models.CharField(_("rol"), max_length=16, choices=Role.choices, default=Role.STUDENT)
    direction = models.ForeignKey(
        Direction,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("yo'nalish"),
    )
    is_active = models.BooleanField(_("faol"), default=True)
    date_joined = models.DateTimeField(_("ro'yxatdan o'tgan vaqt"), default=timezone.now)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "hemis_id"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["full_name"]

    class Meta:
        verbose_name = _("foydalanuvchi")
        verbose_name_plural = _("foydalanuvchilar")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(hemis_id__regex=HEMIS_ID_DB_REGEX),
                name="accounts_user_hemis_id_12_digits",
            ),
            models.CheckConstraint(
                condition=Q(full_name__regex=r"\S"), name="accounts_user_full_name_not_blank"
            ),
            models.CheckConstraint(
                condition=Q(role__in=Role.values), name="accounts_user_role_valid"
            ),
            models.CheckConstraint(
                condition=~Q(role=Role.STUDENT) | Q(direction__isnull=False),
                name="accounts_user_student_has_direction",
            ),
            models.CheckConstraint(
                condition=Q(is_superuser=False) | Q(role=Role.SUPER_ADMIN),
                name="accounts_user_superuser_is_super_admin",
            ),
        ]

    def __str__(self) -> str:
        # FIO va Hemis ID loglarga tushmasligi uchun faqat ichki id.
        return f"User#{self.pk}"

    @property
    def is_staff(self) -> bool:
        """Django Admin'ga kirish rolga bog'liq — alohida bayroq sinxronlashmay qolmasin."""
        return self.role in STAFF_ROLES

    def clean(self) -> None:
        super().clean()
        self.full_name = normalize_full_name(self.full_name)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_name = normalize_full_name(self.full_name)
        super().save(*args, **kwargs)
