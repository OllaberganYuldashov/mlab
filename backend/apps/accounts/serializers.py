"""Ro'yxatdan o'tish (AUTH-01) va yo'nalishlar ro'yxati serializer'lari.

Kirish ma'lumoti chegarada bir marta tekshiriladi va normallashtiriladi (Hemis ID bo'sh joysiz,
FIO NFC). Rol, `is_superuser` kabi maydonlar serializer'da umuman yo'q — mass assignment imkonsiz.
"""

from __future__ import annotations

from typing import Any, ClassVar

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.accounts.models import (
    Consent,
    Direction,
    Role,
    User,
    normalize_full_name,
    normalize_hemis_id,
)


class DirectionSerializer(serializers.ModelSerializer[Direction]):
    class Meta:
        model = Direction
        fields = ("id", "name")


class RegisterSerializer(serializers.Serializer[User]):
    hemis_id = serializers.CharField(max_length=32, trim_whitespace=True)
    full_name = serializers.CharField(max_length=150)
    direction = serializers.PrimaryKeyRelatedField(queryset=Direction.objects.all())
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    consent = serializers.BooleanField(write_only=True)
    policy_version = serializers.CharField(write_only=True, max_length=32)

    default_error_messages: ClassVar[dict[str, Any]] = {
        "hemis_taken": _("Bu Hemis ID bilan foydalanuvchi allaqachon bor."),
    }

    def validate_hemis_id(self, value: str) -> str:
        try:
            hemis_id = normalize_hemis_id(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                _("Hemis ID 12 ta raqamdan iborat bo'lishi kerak.")
            ) from exc
        if User.objects.filter(hemis_id=hemis_id).exists():
            self.fail("hemis_taken")
        return hemis_id

    def validate_full_name(self, value: str) -> str:
        name = normalize_full_name(value)
        if not name:
            raise serializers.ValidationError(_("FIO bo'sh bo'lmasligi kerak."))
        return name

    def validate_consent(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError(
                _("Ro'yxatdan o'tish uchun foydalanish va maxfiylik siyosatiga rozilik kerak.")
            )
        return value

    def validate_policy_version(self, value: str) -> str:
        if value != settings.PRIVACY_POLICY_VERSION:
            raise serializers.ValidationError(
                _("Siyosat yangilangan. Sahifani yangilab, siyosatni qayta o'qing.")
            )
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        candidate = User(
            hemis_id=attrs["hemis_id"], full_name=attrs["full_name"], role=Role.STUDENT
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    hemis_id=validated_data["hemis_id"],
                    password=validated_data["password"],
                    full_name=validated_data["full_name"],
                    direction=validated_data["direction"],
                    role=Role.STUDENT,
                )
                Consent.objects.create(user=user, policy_version=validated_data["policy_version"])
        except IntegrityError as exc:
            # Faqat bir vaqtdagi ikki so'rov (bir xil Hemis ID) — 400; boshqa cheklov xatosi — bug.
            if not User.objects.filter(hemis_id=validated_data["hemis_id"]).exists():
                raise
            raise serializers.ValidationError(
                {"hemis_id": [self.error_messages["hemis_taken"]]}
            ) from exc
        return user

    def to_representation(self, instance: User) -> dict[str, Any]:
        return {
            "hemis_id": instance.hemis_id,
            "full_name": instance.full_name,
            "role": instance.role,
            "direction": instance.direction_id,
        }


class LoginSerializer(serializers.Serializer[User]):
    hemis_id = serializers.CharField(max_length=32)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class MeSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ("hemis_id", "full_name", "role", "direction", "must_change_password")
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer[User]):
    old_password = serializers.CharField(max_length=128, trim_whitespace=False)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user: User = self.context["user"]
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": [_("Joriy parol noto'g'ri.")]})
        if attrs["new_password"] == attrs["old_password"]:
            raise serializers.ValidationError(
                {"new_password": [_("Yangi parol eskisidan farq qilishi kerak.")]}
            )
        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        return attrs


class TemporaryPasswordSerializer(serializers.Serializer[User]):
    temporary_password = serializers.CharField(read_only=True)
