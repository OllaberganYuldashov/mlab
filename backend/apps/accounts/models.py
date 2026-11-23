"""Foydalanuvchi va yo'nalish (AUTH-01, AUTH-03; SRS 2.2 rollar).

Invariantlar DB darajasida (CHECK/UNIQUE/FK), chunki `bulk_create`, migratsiya yoki
qo'lda SQL ilova tekshiruvlarini aylanib o'tadi.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import timedelta
from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models import F, Func, Q, TextField
from django.db.models.functions import Now
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


def _is_canonical_text(field: str) -> Q:
    """DB: matn NFC shaklida va chetida bo'sh joy yo'q (save()'ni aylanib o'tgan yozuv uchun)."""
    canonical = Func(
        F(field), template="normalize(btrim(%(expressions)s), NFC)", output_field=TextField()
    )
    return Q(**{field: canonical})


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", _("Super admin")
    ADMIN = "admin", _("Admin")
    INSTRUCTOR = "instructor", _("O'qituvchi")
    STUDENT = "student", _("Talaba")


STAFF_ROLES = frozenset({Role.SUPER_ADMIN, Role.ADMIN})
TEMPORARY_PASSWORD_TTL = timedelta(hours=24)


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
            models.CheckConstraint(
                condition=_is_canonical_text("name"), name="accounts_direction_name_canonical"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = normalize_full_name(self.name)
        super().save(*args, **kwargs)


class UserManager(BaseUserManager["User"]):
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
    hemis_id = models.CharField(
        _("Hemis ID"),
        max_length=12,
        unique=True,
        validators=[
            RegexValidator(HEMIS_ID_DB_REGEX, _("Hemis ID 12 ta raqamdan iborat bo'lishi kerak."))
        ],
        error_messages={"unique": _("Bu Hemis ID bilan foydalanuvchi allaqachon bor.")},
    )
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
    # AUTH-04: vaqtinchalik parol berilgan — keyingi kirishda yangisini o'rnatish majburiy.
    must_change_password = models.BooleanField(_("parolni almashtirishi shart"), default=False)
    # AUTH-05, SEC-08: o'qituvchining barcha guruhlaridagi talabalar chegarasi (faqat o'qituvchida).
    student_limit = models.PositiveIntegerField(_("talaba limiti"), null=True, blank=True)
    # Vaqtinchalik parol muddati (24 soat): o'tgach u bilan kirib bo'lmaydi — yangi tiklash kerak.
    temporary_password_expires_at = models.DateTimeField(
        _("vaqtinchalik parol muddati"), null=True, blank=True
    )
    date_joined = models.DateTimeField(_("ro'yxatdan o'tgan vaqt"), default=timezone.now)
    updated_at = models.DateTimeField(_("o'zgartirilgan vaqt"), auto_now=True)

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
                condition=Q(full_name__regex=r"\S"),
                name="accounts_user_full_name_not_blank",
                violation_error_message=_("FIO bo'sh bo'lmasligi kerak."),
            ),
            models.CheckConstraint(
                condition=_is_canonical_text("full_name"), name="accounts_user_full_name_canonical"
            ),
            models.CheckConstraint(
                condition=Q(role__in=Role.values), name="accounts_user_role_valid"
            ),
            models.CheckConstraint(
                condition=~Q(role=Role.STUDENT) | Q(direction__isnull=False),
                name="accounts_user_student_has_direction",
                violation_error_message=_("Talaba uchun yo'nalish tanlanishi shart."),
            ),
            models.CheckConstraint(
                # NULL >= 1 SQL'da NULL (CHECK o'tib ketadi) — shuning uchun IS NOT NULL aniq.
                condition=(
                    Q(role=Role.INSTRUCTOR)
                    & Q(student_limit__isnull=False)
                    & Q(student_limit__gte=1)
                )
                | (~Q(role=Role.INSTRUCTOR) & Q(student_limit__isnull=True)),
                name="accounts_user_student_limit_only_instructor",
                violation_error_message=_(
                    "Talaba limiti faqat o'qituvchida bo'ladi va kamida 1 bo'lishi kerak."
                ),
            ),
            # Ikki tomonlama: super_admin <=> is_superuser (bayroq va rol bir-biriga zid bo'lmaydi).
            models.CheckConstraint(
                condition=(Q(role=Role.SUPER_ADMIN) & Q(is_superuser=True))
                | (~Q(role=Role.SUPER_ADMIN) & Q(is_superuser=False)),
                name="accounts_user_superuser_iff_super_admin",
            ),
        ]

    def __str__(self) -> str:
        # FIO va Hemis ID loglarga tushmasligi uchun faqat ichki id.
        return f"User#{self.pk}"

    @property
    def is_staff(self) -> bool:
        """Django Admin'ga kirish rolga bog'liq — alohida bayroq sinxronlashmay qolmasin."""
        return self.role in STAFF_ROLES

    # Ruxsatlar faqat rol bo'yicha (apps/accounts/permissions.py, admin_access.py). Django'ning
    # guruh/ruxsat jadvallari va "superuser hammasiga ruxsat" yorlig'i ataylab o'chirilgan:
    # aks holda shell yoki fixture orqali berilgan ruxsat rol modelini aylanib o'tadi.
    def has_perm(self, perm: str, obj: Any = None) -> bool:
        return False

    def has_perms(self, perm_list: Any, obj: Any = None) -> bool:
        return False

    def has_module_perms(self, app_label: str) -> bool:
        return False

    def clean(self) -> None:
        super().clean()
        self.full_name = normalize_full_name(self.full_name)

    def set_temporary_password(self, raw_password: str) -> None:
        """AUTH-04: vaqtinchalik parol — saqlangandan keyin `must_change_password` yoqiq qoladi."""
        self.set_password(raw_password)
        self.must_change_password = True
        self.temporary_password_expires_at = timezone.now() + TEMPORARY_PASSWORD_TTL
        self._temporary_password = True

    @property
    def temporary_password_expired(self) -> bool:
        expires = self.temporary_password_expires_at
        return self.must_change_password and expires is not None and timezone.now() >= expires

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_name = normalize_full_name(self.full_name)
        # set_password() chaqirilgan (xesh yangilanishi emas — check_password u holda `_password`ni
        # tozalaydi). Mavjud foydalanuvchi parolni almashtirdi: majburiylik olib tashlanadi.
        raw = getattr(self, "_password", None)
        changed_by_user = (
            raw is not None
            and not self._state.adding
            and not getattr(self, "_temporary_password", False)
        )
        if changed_by_user and self.must_change_password and self._same_as_stored(str(raw)):
            # Vaqtinchalik parolni "yangi" parol qilib qo'yish majburiylikni olib tashlamaydi.
            changed_by_user = False
        if changed_by_user:
            self.must_change_password = False
            self.temporary_password_expires_at = None
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = {
                    *update_fields,
                    "must_change_password",
                    "temporary_password_expires_at",
                }
        from apps.audit import record
        from apps.audit.models import Action

        # Parol va uning izi birga: audit yozilmasa, parol ham o'zgarmaydi.
        with transaction.atomic():
            super().save(*args, **kwargs)
            if changed_by_user:
                # API (change-password) va Django Admin (password_change) uchun bir xil iz.
                record(Action.PASSWORD_CHANGED, actor=self, target=self)
        self._temporary_password = False

    def _same_as_stored(self, raw: str) -> bool:
        stored = type(self).objects.filter(pk=self.pk).values_list("password", flat=True).first()
        return stored is not None and check_password(raw, stored)


class Consent(models.Model):
    """SRS 7-bo'lim: talaba qaysi siyosat versiyasiga qachon rozilik bergani (o'zgarmaydi)."""

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # rozilik izi foydalanuvchi bilan birga izsiz yo'qolmaydi
        related_name="consents",
        db_index=False,  # (user, policy_version) unikal indeksi yetarli
    )
    policy_version = models.CharField(_("siyosat versiyasi"), max_length=32)
    accepted_at = models.DateTimeField(_("rozilik vaqti"), db_default=Now(), editable=False)

    class Meta:
        verbose_name = _("rozilik")
        verbose_name_plural = _("roziliklar")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["user", "policy_version"], name="accounts_consent_user_version_uniq"
            ),
            models.CheckConstraint(
                condition=Q(policy_version__regex=r"\S"), name="accounts_consent_version_not_blank"
            ),
        ]

    def __str__(self) -> str:
        return f"Consent#{self.pk} {self.policy_version}"
