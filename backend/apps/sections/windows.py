"""Kirish oynalari holati (ACC-01..03). Sof funksiyalar: vaqt tashqaridan beriladi (test va soat).

Chegaralar: `opens_at` lahzasida — ochiq, `closes_at` lahzasida — yopiq (yarim ochiq oraliq).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from apps.sections.models import AccessWindow, WindowMode


class MaterialKind(StrEnum):
    LECTURE = "lecture"
    QUIZ = "quiz"
    INDEPENDENT = "independent"
    LAB = "lab"


def material_always_open(kind: MaterialKind) -> bool:
    """ACC-01: ma'ruza, mashq testi va mustaqil topshiriq a'zo talabaga doim ochiq."""
    return kind is not MaterialKind.LAB


@dataclass(frozen=True)
class WindowState:
    status: str  # closed | open | upcoming
    opens_at: datetime | None
    closes_at: datetime | None
    seconds_left: int | None = None
    seconds_until_open: int | None = None


def window_state(window: AccessWindow | None, at: datetime) -> WindowState:
    if window is None or window.mode == WindowMode.CLOSED:
        return WindowState("closed", None, None)
    opens, closes = window.opens_at, window.closes_at
    assert opens is not None  # DB CHECK: ochiq/jadval rejimida bor  # noqa: S101
    if at < opens:
        return WindowState("upcoming", opens, closes, None, int((opens - at).total_seconds()))
    if closes is not None and at >= closes:
        return WindowState("closed", opens, closes)
    left = int((closes - at).total_seconds()) if closes is not None else None
    return WindowState("open", opens, closes, left)
