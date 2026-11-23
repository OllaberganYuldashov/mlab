"""Qo'shilish tokeni (SEC-02, I1-03).

To'liq token faqat yaratilgan javobda bir marta qaytadi; bazada faqat SHA-256 xeshi. Qidiruv xesh
bo'yicha (unique indeks) — satrlarni solishtirish vaqtidan token oshkor bo'lmaydi; baza o'g'irlansa
ham xeshdan tokenni tiklab bo'lmaydi (128 bit tasodif).
"""

from __future__ import annotations

import hashlib
import re
import secrets

from apps.sections.models import Section

TOKEN_BYTES = 16  # 128 bit
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    """(token, xesh) juftligi."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    return token, hash_token(token)


def find_section_by_token(token: str) -> Section | None:
    if not _TOKEN_RE.fullmatch(token):
        return None
    return Section.objects.filter(join_token_hash=hash_token(token)).first()
