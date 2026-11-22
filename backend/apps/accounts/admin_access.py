"""Django Admin'da rolga asoslangan kirish (SRS 2.2).

Admin saytiga faqat super admin va admin kiradi (`User.is_staff` roldan hisoblanadi).
Har model uchun kim ko'radi, qo'shadi, o'zgartiradi, o'chiradi —
`RoleAccessAdmin` da aniq ro'yxat. Django'ning
`is_superuser` "hammasiga ruxsat" xatti-harakati bu yerda ishlatilmaydi: ruxsat faqat rol bo'yicha.
"""

from __future__ import annotations

from typing import Any, ClassVar

from django.contrib import admin
from django.http import HttpRequest

from apps.accounts.models import Role
from apps.accounts.permissions import has_role


class RoleAccessAdmin(admin.ModelAdmin):  # type: ignore[type-arg]  # runtime generic emas
    view_roles: ClassVar[tuple[Role, ...]] = ()
    add_roles: ClassVar[tuple[Role, ...]] = ()
    change_roles: ClassVar[tuple[Role, ...]] = ()
    delete_roles: ClassVar[tuple[Role, ...]] = ()

    def has_module_permission(self, request: HttpRequest) -> bool:
        return has_role(request.user, *self.view_roles)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return has_role(request.user, *self.view_roles)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return has_role(request.user, *self.add_roles)

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return has_role(request.user, *self.change_roles)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return has_role(request.user, *self.delete_roles)
