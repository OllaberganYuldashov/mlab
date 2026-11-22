"""Django Admin: foydalanuvchilar va yo'nalishlar (R0-05, SRS 2.2).

- Kirish: faqat super admin va admin (`User.is_staff`).
- Parol xeshi admin sahifasida umuman ko'rsatilmaydi (`password` maydoni formada yo'q).
- Rolni faqat super admin o'zgartiradi; har o'zgarish audit jurnaliga yoziladi (ADM-02).
- Admin super admin va boshqa adminlarni tahrirlay olmaydi (ularni super admin boshqaradi).
- Foydalanuvchi qo'shish (R0-09) va o'chirish (ma'lumot o'chirish siyosati) — admin'da yo'q.
"""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from apps.accounts.admin_access import RoleAccessAdmin
from apps.accounts.models import Direction, Role, User
from apps.audit import record
from apps.audit.models import Action

STAFF = (Role.SUPER_ADMIN, Role.ADMIN)

admin.site.site_header = _("MLab boshqaruvi")
admin.site.site_title = _("MLab boshqaruvi")
admin.site.index_title = _("Boshqaruv paneli")


@admin.register(Direction)
class DirectionAdmin(RoleAccessAdmin):
    view_roles = add_roles = change_roles = delete_roles = STAFF
    list_display = ("name", "created_at")
    fields = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(User)
class UserAdmin(RoleAccessAdmin):
    view_roles = change_roles = STAFF
    list_display = ("hemis_id", "full_name", "role", "direction", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("hemis_id", "full_name")
    ordering = ("hemis_id",)
    list_select_related = ("direction",)
    # `password` ataylab yo'q: xesh ham, uning qisqa ko'rinishi ham chiqmaydi.
    fields = (
        "hemis_id",
        "full_name",
        "role",
        "direction",
        "is_active",
        "date_joined",
        "last_login",
        "updated_at",
    )
    _always_readonly = ("hemis_id", "date_joined", "last_login", "updated_at")

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        if request.user.role == Role.SUPER_ADMIN:  # type: ignore[union-attr]
            return self._always_readonly
        return (*self._always_readonly, "role")

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if not super().has_change_permission(request, obj):
            return False
        if obj is not None and request.user.role == Role.ADMIN:  # type: ignore[union-attr]
            return obj.role in (Role.INSTRUCTOR, Role.STUDENT)
        return True

    def save_model(
        self, request: HttpRequest, obj: User, form: ModelForm[User], change: bool
    ) -> None:
        previous_role = form.initial.get("role", obj.role)
        # DB cheklovi: is_superuser <=> super_admin — rol bilan birga sinxronlanadi.
        obj.is_superuser = obj.role == Role.SUPER_ADMIN
        super().save_model(request, obj, form, change)
        if change and previous_role != obj.role:
            record(
                Action.ROLE_CHANGED,
                actor=request.user,  # type: ignore[arg-type]
                target=obj,
                before={"role": previous_role},
                after={"role": obj.role},
            )
