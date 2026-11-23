"""ACC-04: takroriy jadval yordamchisi — haftalik slotlar bo'yicha mavzularni joylashtirish.

Sof funksiya: vaqt zonasi tashqaridan (Asia/Tashkent). Mahalliy vaqt `zoneinfo` bilan — kelajakda
DST bo'lsa ham to'g'ri (Toshkentda hozir yo'q).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo

MAX_SLOT_MINUTES = 600


@dataclass(frozen=True)
class Slot:
    weekday: int  # 0 = dushanba ... 6 = yakshanba
    start: time
    minutes: int


def _validate(slots: list[Slot]) -> list[Slot]:
    if not slots:
        raise ValueError("Kamida bitta slot kerak.")
    for slot in slots:
        if not 0 <= slot.weekday <= 6:
            raise ValueError("slot kuni 0 (dushanba) .. 6 (yakshanba) bo'lishi kerak.")
        if not 1 <= slot.minutes <= MAX_SLOT_MINUTES:
            raise ValueError(f"slot davomiyligi 1..{MAX_SLOT_MINUTES} daqiqa.")
    ordered = sorted(slots, key=lambda s: (s.weekday, s.start))
    for prev, cur in pairwise(ordered):
        if prev.weekday == cur.weekday:
            prev_end = datetime.combine(date.min, prev.start) + timedelta(minutes=prev.minutes)
            if datetime.combine(date.min, cur.start) < prev_end:
                raise ValueError("slotlar bir-biriga to'g'ri kelmasligi kerak.")
    return ordered


def plan_slots(
    count: int, slots: list[Slot], start: date, tz: ZoneInfo
) -> list[tuple[datetime, datetime]]:
    """`start` kunidan (o'zi ham) boshlab `count` ta (ochilish, yopilish) juftligi."""
    ordered = _validate(slots)
    result: list[tuple[datetime, datetime]] = []
    day = start
    while len(result) < count:
        for slot in (s for s in ordered if s.weekday == day.weekday()):
            opens = datetime.combine(day, slot.start, tzinfo=tz)
            result.append((opens, opens + timedelta(minutes=slot.minutes)))
            if len(result) == count:
                break
        day += timedelta(days=1)
    return result
