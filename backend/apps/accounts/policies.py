"""Obyekt darajasidagi qoidalar (CLAUDE.md 5.6): kim kimning parolini tiklaydi (AUTH-04, SRS 2.2).

Endpoint ruxsat bermagan nishon uchun 404 qaytaradi (mavjudligi ham oshkor qilinmaydi).
"""

from __future__ import annotations

from apps.accounts.models import Role, User

# Kim -> qaysi rollarning parolini tiklaydi (o'zinikini emas — o'zi uchun change-password).
_RESETTABLE: dict[str, frozenset[str]] = {
    Role.SUPER_ADMIN: frozenset({Role.ADMIN, Role.INSTRUCTOR, Role.STUDENT}),
    Role.ADMIN: frozenset({Role.INSTRUCTOR, Role.STUDENT}),
    Role.INSTRUCTOR: frozenset({Role.STUDENT}),
}

RESET_ROLES = frozenset(_RESETTABLE)


def instructor_teaches(instructor: User, student: User) -> bool:
    """O'qituvchi talabaning guruhini olib boradimi. Guruhlar (sections) I1 da — hozir doim False.

    Fail closed: guruh modeli kelguncha o'qituvchi hech kimning parolini tiklay olmaydi.
    I1 da shu funksiya `Section` a'zoligi bo'yicha yoziladi (testlar tayyor).
    """
    return False


def can_reset_password(actor: User, target: User) -> bool:
    if actor.pk == target.pk or not target.is_active:
        # Nofaol akkauntga ishlaydigan parol berilmaydi (avval admin uni faollashtiradi).
        return False
    if target.role not in _RESETTABLE.get(actor.role, frozenset()):
        return False
    if actor.role == Role.INSTRUCTOR:
        return instructor_teaches(actor, target)
    return True
