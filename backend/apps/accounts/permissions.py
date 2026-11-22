"""Rolga asoslangan DRF ruxsatlari (SRS 2.2).

Har sinf bitta rolni tekshiradi; bir nechta rolga ruxsat kerak bo'lsa, DRF operatori bilan
birlashtiriladi:
`permission_classes = [IsAdmin | IsSuperAdmin]`. Rollar ierarxiyasi ataylab yo'q — super admin admin
huquqlarini avtomatik olmaydi (SRS 2.2 da ularning vazifalari alohida).

Bu faqat **rol** darajasidagi tekshiruv. Obyekt darajasidagi qoida (o'qituvchi — faqat o'z guruhi,
talaba — faqat o'z ishi; CLAUDE.md 5.6) har endpoint'da `get_queryset` va `has_object_permission`
bilan alohida yoziladi va "begona foydalanuvchi" testi bilan tekshiriladi.
"""

from __future__ import annotations

from typing import Any, ClassVar

from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import Role, User


def has_role(user: Any, *roles: Role) -> bool:
    """Foydalanuvchi tizimga kirgan, faol va ko'rsatilgan rollardan birida."""
    return (
        isinstance(user, User) and user.is_authenticated and user.is_active and user.role in roles
    )


class _HasRole(BasePermission):
    roles: ClassVar[tuple[Role, ...]] = ()
    message = _("Bu amal uchun ruxsat yo'q.")

    def has_permission(self, request: Request, view: APIView) -> bool:
        return has_role(request.user, *self.roles)


class IsSuperAdmin(_HasRole):
    roles = (Role.SUPER_ADMIN,)


class IsAdmin(_HasRole):
    roles = (Role.ADMIN,)


class IsInstructor(_HasRole):
    roles = (Role.INSTRUCTOR,)


class IsStudent(_HasRole):
    roles = (Role.STUDENT,)
