"""Guruh test ma'lumotlari (Faker bilan, CLAUDE.md 5.3)."""

from __future__ import annotations

import itertools
from typing import Any

from apps.accounts.models import Role, User
from apps.courses.models import Course
from apps.sections.models import Membership, Section
from tests.accounts.factories import make_direction, make_user

_seq = itertools.count(1)


def make_course() -> Course:
    n = next(_seq)
    return Course.objects.create(
        slug=f"kurs-{n}", title=f"Kurs {n}", version="1", content_hash="0" * 64
    )


def make_instructor(**fields: Any) -> User:
    return make_user(role=Role.INSTRUCTOR, direction=None, **fields)


def make_section(**fields: Any) -> Section:
    if "course" not in fields:
        fields["course"] = Course.objects.first() or make_course()
    fields.setdefault("instructor", make_instructor())
    fields.setdefault("direction", make_direction())
    fields.setdefault("name", f"Guruh {next(_seq)}")
    return Section.objects.create(**fields)


def make_membership(**fields: Any) -> Membership:
    fields.setdefault("section", make_section())
    fields.setdefault("student", make_user())
    return Membership.objects.create(**fields)
