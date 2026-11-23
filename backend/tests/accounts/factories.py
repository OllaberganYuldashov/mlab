"""Test ma'lumotlari: FIO va Hemis ID faqat Faker bilan (CLAUDE.md 5.3).

factory_boy o'rniga oddiy tiplangan funksiyalar — mypy strict bilan to'liq tekshiriladi.
"""

from __future__ import annotations

import itertools
import secrets
from typing import Any

from faker import Faker

from apps.accounts.models import Direction, Role, User

fake = Faker()
_seq = itertools.count(1)
# gitleaks: literal parol yozilmaydi, har ishga tushishda yangisi.
DEFAULT_PASSWORD = secrets.token_urlsafe(12)


def make_direction(name: str | None = None) -> Direction:
    return Direction.objects.create(name=name or f"Yo'nalish {next(_seq)}")


def make_user(*, password: str = DEFAULT_PASSWORD, **fields: Any) -> User:
    fields.setdefault("hemis_id", fake.unique.numerify("############"))
    fields.setdefault("full_name", fake.name())
    fields.setdefault("role", Role.STUDENT)
    if fields["role"] == Role.INSTRUCTOR:
        fields.setdefault("student_limit", 30)
    if "direction" not in fields:
        fields["direction"] = make_direction() if fields["role"] == Role.STUDENT else None
    user = User(**fields)
    user.set_password(password)
    user.save()
    return user
