"""SEC-08: o'qituvchi bo'yicha umumiy talaba limiti (I1 guruhlari a'zolikni tasdiqlashdan oldin)."""

from __future__ import annotations

from django.db import transaction
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

    Faqat tranzaksiya ichida: o'qituvchi qatori shu yerda `select_for_update` bilan qulflanib qayta
    o'qiladi — parallel limit o'zgarishi yoki ikki tasdiq limitni aylanib o'ta olmaydi. Chaqiruvchi
    (I1) `current_students` ni shu qulfdan keyin, o'sha tranzaksiyada hisoblaydi.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("ensure_capacity faqat transaction.atomic() ichida chaqiriladi.")
    locked = User.objects.select_for_update().filter(pk=instructor.pk).first()
    if locked is None or locked.role != Role.INSTRUCTOR or locked.student_limit is None:
        raise ValueError("Limit faqat o'qituvchi uchun tekshiriladi.")
    if adding < 1 or current_students < 0:
        raise ValueError("Noto'g'ri son.")
    if current_students + adding > locked.student_limit:
        raise StudentLimitExceeded(locked.student_limit)
