"""SEC-08: o'qituvchi bo'yicha umumiy talaba limiti (I1 guruhlari a'zolikni tasdiqlashdan oldin)."""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Role, User


class StudentLimitExceeded(Exception):
    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(
            str(_("O'qituvchining talaba limiti ({limit}) to'ldi.")).format(limit=limit)
        )


def ensure_capacity(instructor: User, current_students: int, adding: int = 1) -> None:
    """`current_students + adding` limitdan oshsa — rad etadi.

    I1 da chaqiruvchi `current_students` ni a'zolik jadvalidan shu tranzaksiya ichida, o'qituvchi
    qatorini `select_for_update` bilan qulflab hisoblaydi (parallel tasdiqlar limitni oshirmasin).
    """
    if instructor.role != Role.INSTRUCTOR or instructor.student_limit is None:
        raise ValueError("Limit faqat o'qituvchi uchun tekshiriladi.")
    if adding < 1 or current_students < 0:
        raise ValueError("Noto'g'ri son.")
    if current_students + adding > instructor.student_limit:
        raise StudentLimitExceeded(instructor.student_limit)
