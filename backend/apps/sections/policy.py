"""Topshirish siyosati (I1-10; ACC-06..08, ACC-10). I3 topshirish va baholash shuni chaqiradi.

Shartnoma (ACC-06): oyna yopilganda laboratoriya tugallanmagan ishni avtomatik saqlaydi va rasmiy
topshirish `submission_policy()` `closed`/`practice` qaytargan paytdan boshlab qabul qilinmaydi;
`late` — qabul qilinadi va "kechikkan" belgisi qo'yiladi; `practice` — baholanmaydi.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from apps.courses.models import Topic
from apps.sections.models import AccessWindow, IndependentDeadline, Section
from apps.sections.settings import effective_settings
from apps.sections.windows import window_state


class SubmissionStatus(StrEnum):
    ON_TIME = "on_time"
    LATE = "late"
    PRACTICE = "practice"
    CLOSED = "closed"


def submission_policy(section: Section, topic: Topic, at: datetime) -> SubmissionStatus:
    window = AccessWindow.objects.filter(section=section, topic=topic).first()
    state = window_state(window, at)
    if state.status == "open":
        return SubmissionStatus.ON_TIME
    if state.status == "upcoming" or state.closes_at is None:
        return SubmissionStatus.CLOSED  # hali ochilmagan yoki hech qachon ochilmagan
    settings = effective_settings(section)
    if at < state.closes_at + timedelta(hours=settings.late_hours):
        return SubmissionStatus.LATE
    if settings.practice_after_close:
        return SubmissionStatus.PRACTICE
    return SubmissionStatus.CLOSED


def independent_policy(
    section: Section, deadline: IndependentDeadline | None, at: datetime
) -> SubmissionStatus:
    """ACC-10: muddat belgilanmagan bo'lsa — doim o'z vaqtida (ACC-01: mustaqil ish doim ochiq)."""
    if deadline is None or at < deadline.due_at:
        return SubmissionStatus.ON_TIME
    late_hours = effective_settings(section).late_hours
    if at < deadline.due_at + timedelta(hours=late_hours):
        return SubmissionStatus.LATE
    return SubmissionStatus.CLOSED


def apply_late_penalty(points: Decimal | int, percent: int) -> Decimal:
    """ACC-07: ball `Decimal(5,2)` (ARCHITECTURE) — jarimadan keyin 0.01 gacha, yarmi yuqoriga.

    float ishlatilmaydi: 0.1 + 0.2 kabi xatolar baholarda qolmasin.
    """
    value = Decimal(points)
    if value < 0 or not 0 <= percent <= 100:
        raise ValueError("Ball yoki foiz noto'g'ri.")
    kept = value * (Decimal(100) - Decimal(percent)) / Decimal(100)
    return kept.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
