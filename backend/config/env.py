"""Muhit o'zgaruvchilarini qat'iy o'qish (NFR-16, fail fast).

Qoida: majburiy sozlama yo'q yoki bo'sh bo'lsa, ilova ishga tushmaydi va qaysi
o'zgaruvchi yetishmayotganini aniq aytadi. Qiymatlar xato xabariga hech qachon chiqarilmaydi
(secret bo'lishi mumkin).
"""

from __future__ import annotations

import os
from typing import Any, cast

import environ
from django.core.exceptions import ImproperlyConfigured

_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})
_WEAK_KEY_PREFIXES = ("dev-only", "test-only", "django-insecure", "change-me")
_MIN_PROD_KEY_LENGTH = 50
_MIN_PROD_KEY_UNIQUE_CHARS = 5


def _missing(name: str) -> ImproperlyConfigured:
    return ImproperlyConfigured(
        f"Majburiy muhit o'zgaruvchisi yo'q yoki bo'sh: {name}. "
        f"Nomi va namunaviy qiymati: .env.example; tavsifi: docs/SECURITY.md."
    )


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise _missing(name)
    return value


def optional(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def _split(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def required_list(name: str) -> list[str]:
    items = _split(required(name))
    if not items:
        raise _missing(name)
    return items


def optional_list(name: str) -> list[str]:
    return _split(os.environ.get(name, ""))


def boolean(name: str, *, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise ImproperlyConfigured(
        f"{name} mantiqiy qiymat bo'lishi kerak (true/false, 1/0, yes/no, on/off)."
    )


def database(name: str = "DATABASE_URL") -> dict[str, Any]:
    url = required(name)
    if not url.startswith(("postgres://", "postgresql://")):
        raise ImproperlyConfigured(f"{name} PostgreSQL manzili bo'lishi kerak (postgres://...).")
    return cast(dict[str, Any], environ.Env.db_url_config(url))


def validate_production(*, secret_key: str, allowed_hosts: list[str]) -> None:
    """Prod sozlamalarida dev qiymatlari bilan ishga tushishni taqiqlaydi."""
    weak = (
        len(secret_key) < _MIN_PROD_KEY_LENGTH
        or len(set(secret_key)) < _MIN_PROD_KEY_UNIQUE_CHARS
        or secret_key.lower().startswith(_WEAK_KEY_PREFIXES)
    )
    if weak:
        raise ImproperlyConfigured(
            "SECRET_KEY prod uchun yaroqsiz: kamida 50 belgili tasodifiy qiymat bo'lishi kerak "
            "(dev/test qiymati ishlatilmaydi)."
        )
    if "*" in allowed_hosts:
        raise ImproperlyConfigured("ALLOWED_HOSTS prod'da '*' bo'lishi mumkin emas.")
