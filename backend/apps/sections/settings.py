"""Ikki darajali sozlamalar (SET-01..05, ARCHITECTURE): kurs default → guruh override.

Boshqa modullar (laboratoriya, AI tutor, chat, topshirish) sozlamani faqat shu yerdan o'qiydi.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from apps.courses.models import AI_MODE_ORDER, AiMode
from apps.sections.models import Section

OVERRIDABLE = ("ai_enabled", "ai_max_mode", "practice_after_close", "late_hours", "chat_enabled")
COURSE_ONLY = ("late_penalty_percent",)


@dataclass(frozen=True)
class EffectiveSettings:
    ai_enabled: bool
    ai_max_mode: AiMode
    practice_after_close: bool
    late_hours: int
    late_penalty_percent: int
    chat_enabled: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def course_defaults(section: Section) -> dict[str, Any]:
    course = section.course
    return {name: getattr(course, name) for name in (*OVERRIDABLE, *COURSE_ONLY)}


def overrides(section: Section) -> dict[str, Any]:
    return {name: getattr(section, name) for name in OVERRIDABLE}


def effective_settings(section: Section) -> EffectiveSettings:
    values = course_defaults(section)
    values.update({k: v for k, v in overrides(section).items() if v is not None})
    values["ai_max_mode"] = AiMode(values["ai_max_mode"])
    return EffectiveSettings(**values)


def effective_ai_mode(section: Section, task_mode: AiMode | str) -> AiMode:
    """SET-01: topshiriq rejimi guruh chegarasidan yuqori bo'lsa — chegara; AI o'chiq — `off`."""
    eff = effective_settings(section)
    if not eff.ai_enabled:
        return AiMode.OFF
    task, cap = AiMode(task_mode), eff.ai_max_mode
    return min(task, cap, key=AI_MODE_ORDER.index)
