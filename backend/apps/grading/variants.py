"""Deterministik variant tanlash (AGR-08, INT-03; I3-03).

indeks = HMAC-SHA256(kalit, "variant:{talaba pk}:{topshiriq}:{daraja}") mod variantlar soni.
Kalitsiz qo'shnining variantini taxmin qilib bo'lmaydi; bir talaba uchun natija har doim bir xil.
Tanlov `StudentAssignment` da saqlanadi — keyingi ochilishlarda qayta hisoblanmaydi.

Kalit: `VARIANT_SECRET`; berilmasa `SECRET_KEY` dan alohida maqsad bilan hosil qilinadi
(prod compose'ga yangi majburiy o'zgaruvchi qo'shilguncha ham ishlaydi — I3-18).
"""

from __future__ import annotations

import hashlib
import hmac

from django.conf import settings
from django.db import transaction

from apps.accounts.models import User
from apps.grading.models import Assignment, Level, StudentAssignment, Variant


class NoVariants(LookupError):
    """Topshiriqda shu daraja uchun variant yo'q (kontent xatosi)."""


def _key() -> bytes:
    secret = str(getattr(settings, "VARIANT_SECRET", "") or "")
    if secret:
        return secret.encode()
    return hmac.new(str(settings.SECRET_KEY).encode(), b"mlab-variant-key", hashlib.sha256).digest()


def _digest(purpose: str, student_id: int, code: str, level: str) -> int:
    message = f"{purpose}:{student_id}:{code}:{level}".encode()
    return int.from_bytes(hmac.new(_key(), message, hashlib.sha256).digest()[:8], "big")


def pick_index(student_id: int, code: str, level: str, count: int) -> int:
    if count < 1:
        raise NoVariants(f"{code}/{level}: variant yo'q")
    return _digest("variant", student_id, code, level) % count


def dataset_seed(student_id: int, code: str) -> int:
    """Dataset qismi uchun seed (0..2^31-1). Darajaga bog'liq emas: daraja almashsa ham o'sha."""
    return _digest("seed", student_id, code, "") % (2**31)


def assign(student: User, assignment: Assignment, level: str = Level.BASIC) -> StudentAssignment:
    """Talabaga topshiriqni beradi yoki mavjudini qaytaradi (idempotent, race-safe).

    Daraja hozircha default `basic`; moslashuvchan qoida — I3-10 (ADP-01).
    """
    existing = StudentAssignment.objects.filter(student=student, assignment=assignment).first()
    if existing is not None:
        return existing
    variants = list(Variant.objects.filter(assignment=assignment, level=level).order_by("number"))
    chosen = variants[pick_index(student.pk, assignment.code, level, len(variants))]
    with transaction.atomic():
        # Ikki so'rov bir vaqtda: unique cheklov bittasini to'xtatadi, u mavjudini oladi.
        record, _ = StudentAssignment.objects.get_or_create(
            student=student,
            assignment=assignment,
            defaults={
                "variant": chosen,
                "level": level,
                "seed": dataset_seed(student.pk, assignment.code),
            },
        )
    return record
