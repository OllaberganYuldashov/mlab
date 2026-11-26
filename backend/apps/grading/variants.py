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
from apps.audit import record as audit
from apps.audit.models import Action
from apps.grading.levels import rule_level
from apps.grading.models import (
    Assignment,
    LevelSource,
    StudentAssignment,
    Submission,
    SubmissionStatus,
    Variant,
)


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


class LevelLocked(Exception):
    """Ochiq (navbatdagi yoki tekshirilayotgan) urinish bor — darajani hozir o'zgartirmaymiz."""


def _pick(student_id: int, assignment: Assignment, level: str) -> Variant:
    variants = list(Variant.objects.filter(assignment=assignment, level=level).order_by("number"))
    return variants[pick_index(student_id, assignment.code, level, len(variants))]


def assign(student: User, assignment: Assignment, level: str | None = None) -> StudentAssignment:
    """Talabaga topshiriqni beradi yoki mavjudini qaytaradi (idempotent, race-safe).

    ADP-01: daraja birinchi ochilishda qoida bo'yicha (`levels.rule_level`) tanlanadi va qotiriladi;
    keyin test yoki boshqa ballar o'zgarsa ham o'zgarmaydi (faqat o'qituvchi — `set_level`).
    """
    existing = StudentAssignment.objects.filter(student=student, assignment=assignment).first()
    if existing is not None:
        return existing
    chosen_level = level or rule_level(student, assignment)
    chosen = _pick(student.pk, assignment, chosen_level)
    with transaction.atomic():
        # Ikki so'rov bir vaqtda: unique cheklov bittasini to'xtatadi, u mavjudini oladi.
        record, _ = StudentAssignment.objects.get_or_create(
            student=student,
            assignment=assignment,
            defaults={
                "variant": chosen,
                "level": chosen_level,
                "seed": dataset_seed(student.pk, assignment.code),
            },
        )
    return record


def set_level(
    student: User, assignment: Assignment, level: str, actor: User
) -> tuple[StudentAssignment, bool]:
    """ADP-02: o'qituvchi darajani o'zgartiradi — yangi daraja uchun yangi variant (o'sha HMAC).

    Ochiq urinish bo'lsa `LevelLocked` (navbatdagi kod eski variant uchun yozilgan). O'zgarish
    audit'ga yoziladi. Talaba hali ochmagan bo'lsa — yozuv shu daraja bilan yaratiladi.
    Natija: (yozuv, o'zgardimi).
    """
    with transaction.atomic():
        _, created = StudentAssignment.objects.get_or_create(
            student=student,
            assignment=assignment,
            defaults={
                "variant": _pick(student.pk, assignment, level),
                "level": level,
                "level_source": LevelSource.INSTRUCTOR,
                "seed": dataset_seed(student.pk, assignment.code),
            },
        )
        current = (
            StudentAssignment.objects.select_for_update()
            .select_related("variant")
            .get(student=student, assignment=assignment)
        )
        if created:  # talaba hali ochmagan — daraja o'qituvchi qarori bilan qotirildi
            after = {"level": level, "variant": current.variant.number}
            audit(Action.LEVEL_CHANGED, actor=actor, target=current, before={}, after=after)
            return current, True
        if current.level == level:
            current.level_source = LevelSource.INSTRUCTOR  # qoida tanlaganini o'qituvchi tasdiqladi
            current.save(update_fields=["level_source"])
            return current, False
        if Submission.objects.filter(
            student_assignment=current,
            status__in=[SubmissionStatus.QUEUED, SubmissionStatus.RUNNING],
        ).exists():
            raise LevelLocked
        before = {"level": current.level, "variant": current.variant.number}
        current.level = level
        current.variant = _pick(student.pk, assignment, level)
        current.level_source = LevelSource.INSTRUCTOR
        current.save(update_fields=["level", "variant", "level_source"])
        audit(
            Action.LEVEL_CHANGED,
            actor=actor,
            target=current,
            before=before,
            after={"level": level, "variant": current.variant.number},
        )
    return current, True
