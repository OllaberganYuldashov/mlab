"""Aiken formatidagi test fayllarini o'qish (CNT-05). Sof funksiya — bazaga tegmaydi.

Format (Moodle Aiken, savol matni bir necha qatordan bo'lishi mumkin)::

    Savol matni?
    A) birinchi variant        # "A." ham qabul qilinadi
    B) ikkinchi variant
    ANSWER: B
    <bo'sh qator>

Variantlar A dan ketma-ket (2..6 ta). Matn o'zgartirilmaydi (o'zbek apostrof variantlari saqlanadi);
savolning tabiiy kaliti — NFC ko'rinishdagi, bo'shliqlari siqilgan matnning SHA-256 xeshi.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

LETTERS = "ABCDEF"
_OPTION_RE = re.compile(r"^([A-Z])[.)]\s*(.*)$")
_ANSWER_RE = re.compile(r"^ANSWER:\s*(.*)$")


class AikenError(Exception):
    def __init__(self, line: int | None, message: str) -> None:
        self.line, self.message = line, message
        super().__init__(f"{line}: {message}" if line else message)


@dataclass(frozen=True)
class AikenQuestion:
    line: int
    text: str
    options: tuple[str, ...]
    answer: int

    @property
    def key(self) -> str:
        return question_key(self.text)


def question_key(text: str) -> str:
    normal = " ".join(unicodedata.normalize("NFC", text).split())
    return hashlib.sha256(normal.encode()).hexdigest()


def parse_aiken(text: str) -> tuple[AikenQuestion, ...]:
    lines = text.removeprefix("﻿").splitlines()
    result: list[AikenQuestion] = []
    seen: dict[str, int] = {}
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        start = i + 1
        question: list[str] = []
        while i < len(lines) and lines[i].strip() and not _OPTION_RE.match(lines[i].strip()):
            if _ANSWER_RE.match(lines[i].strip()):
                raise AikenError(i + 1, "ANSWER variantlardan keyin bo'ladi")
            question.append(lines[i].strip())
            i += 1
        if not question:
            raise AikenError(start, "savol matni yo'q (variantdan oldin savol bo'lishi kerak)")
        options: list[str] = []
        last = i
        while i < len(lines) and (match := _OPTION_RE.match(lines[i].strip())):
            letter, value = match.group(1), match.group(2).strip()
            if len(options) == len(LETTERS):
                raise AikenError(i + 1, f"variantlar soni 2..{len(LETTERS)} bo'lishi kerak")
            if letter != LETTERS[len(options)]:
                raise AikenError(i + 1, f"variant harfi {LETTERS[len(options)]} bo'lishi kerak")
            if not value:
                raise AikenError(i + 1, "variant matni bo'sh")
            if value in options:
                raise AikenError(i + 1, "variant takrorlangan")
            options.append(value)
            last = i
            i += 1
        if i >= len(lines) or not (answer := _ANSWER_RE.match(lines[i].strip())):
            raise AikenError(last + 1, "variantlardan keyin 'ANSWER: <harf>' qatori kerak")
        if len(options) < 2:
            raise AikenError(i + 1, f"variantlar soni 2..{len(LETTERS)} bo'lishi kerak")
        letter = answer.group(1).strip()
        if len(letter) != 1 or letter not in LETTERS[: len(options)]:
            raise AikenError(i + 1, f"ANSWER bittasi: {', '.join(LETTERS[: len(options)])}")
        item = AikenQuestion(start, "\n".join(question), tuple(options), LETTERS.index(letter))
        if item.key in seen:
            raise AikenError(start, f"savol takrorlangan ({seen[item.key]}-qatordagi bilan)")
        seen[item.key] = start
        result.append(item)
        i += 1
        if i < len(lines) and lines[i].strip():
            raise AikenError(i + 1, "savollar orasida bo'sh qator bo'lishi kerak")
    if not result:
        raise AikenError(None, "faylda savol yo'q")
    return tuple(result)
