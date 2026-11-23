"""Django Admin: foydalanuvchilar va yo'nalishlar (R0-05, SRS 2.2).

- Kirish: faqat super admin va admin (`User.is_staff`).
- Parol xeshi admin sahifasida umuman ko'rsatilmaydi (`password` maydoni formada yo'q).
- Rolni faqat super admin o'zgartiradi; har o'zgarish audit jurnaliga yoziladi (ADM-02).
- Admin super admin va boshqa adminlarni tahrirlay olmaydi (ularni super admin boshqaradi).
- Foydalanuvchi qo'shish (R0-09) va o'chirish (ma'lumot o'chirish siyosati) — admin'da yo'q.
"""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import QuerySet
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

# Django guruh/ruxsat jadvallari ishlatilmaydi (ruxsat faqat rol bo'yicha) — muharriri yo'q.
admin.site.unregister(Group)


@admin.register(Direction)
class DirectionAdmin(RoleAccessAdmin):
    view_roles = add_roles = change_roles = delete_roles = STAFF
    list_display = ("name", "created_at")
    fields = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


# Audit qilinadigan maydonlar (ADM-02): rol, akkaunt faolligi, o'qituvchi talaba limiti.
_AUDITED = {
    "role": Action.ROLE_CHANGED,
    "is_active": Action.USER_ACTIVE_CHANGED,
    "student_limit": Action.STUDENT_LIMIT_CHANGED,
}


class UserAdminForm(forms.ModelForm):  # type: ignore[type-arg]  # runtime generic emas
    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        role = data.get("role", getattr(self.instance, "role", None))
        if "student_limit" in data and role != Role.INSTRUCTOR:
            # Limit faqat o'qituvchida (DB CHECK): boshqa rolga o'tganda o'zi tozalanadi.
            data["student_limit"] = None
        return data


@admin.register(User)
class UserAdmin(RoleAccessAdmin):
    view_roles = change_roles = STAFF
    form = UserAdminForm
    list_display = ("hemis_id", "full_name", "role", "direction", "student_limit", "is_active")
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
        "student_limit",
        "is_active",
        "date_joined",
        "last_login",
        "updated_at",
    )
    _always_readonly = ("hemis_id", "date_joined", "last_login", "updated_at")

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        qs = super().get_queryset(request)
        if request.user.role == Role.ADMIN:  # type: ignore[union-attr]
            # Admin faqat o'qituvchi va talabalarni boshqaradi; boshqa xodimlar unga ko'rinmaydi.
            return qs.filter(role__in=(Role.INSTRUCTOR, Role.STUDENT))
        return qs

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        readonly: tuple[str, ...] = self._always_readonly
        if request.user.role != Role.SUPER_ADMIN:  # type: ignore[union-attr]
            readonly = (*readonly, "role")
        if obj is not None and obj.pk == request.user.pk:
            # O'zini pasaytirish yoki o'chirib qo'yish — tizimni boshqaruvchisiz qoldirishi mumkin.
            readonly = (*readonly, "role", "is_active")
        return tuple(dict.fromkeys(readonly))

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if not super().has_change_permission(request, obj):
            return False
        if obj is not None and request.user.role == Role.ADMIN:  # type: ignore[union-attr]
            return obj.role in (Role.INSTRUCTOR, Role.STUDENT)
        return True

    def save_model(
        self, request: HttpRequest, obj: User, form: ModelForm[User], change: bool
    ) -> None:
        previous = {key: form.initial.get(key) for key in _AUDITED}
        # DB cheklovi: is_superuser <=> super_admin — rol bilan birga sinxronlanadi.
        obj.is_superuser = obj.role == Role.SUPER_ADMIN
        super().save_model(request, obj, form, change)
        if not change:
            return
        for key, action in _AUDITED.items():
            if key in form.changed_data:
                record(
                    action,
                    actor=request.user,  # type: ignore[arg-type]
                    target=obj,
                    before={key: previous[key]},
                    after={key: getattr(obj, key)},
                )
