"""Django Admin: audit jurnali — faqat super admin ko'radi (SRS 2.2), hech kim o'zgartirmaydi."""

from __future__ import annotations

from django.contrib import admin

from apps.accounts.admin_access import RoleAccessAdmin
from apps.accounts.models import Role
from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(RoleAccessAdmin):
    view_roles = (Role.SUPER_ADMIN,)
    list_display = ("created_at", "action", "actor", "target_type", "target_id", "request_id")
    list_filter = ("action",)
    search_fields = ("target_id", "request_id")
    ordering = ("-created_at",)
    list_select_related = ("actor",)
    # add/change/delete rollari bo'sh: hech kimga ruxsat yo'q (append-only).
