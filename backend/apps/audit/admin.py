"""Django Admin: audit jurnali faqat o'qish uchun (admin sayti R0-05 da ulanadi)."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):  # type: ignore[type-arg]  # runtime generic emas
    list_display = ("created_at", "action", "actor", "target_type", "target_id", "request_id")
    list_filter = ("action",)
    search_fields = ("target_id", "request_id")
    ordering = ("-created_at",)
    list_select_related = ("actor",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
