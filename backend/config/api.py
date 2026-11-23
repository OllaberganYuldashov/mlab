"""API darajasidagi umumiy yordamchilar."""

from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import has_role


class IsStaffRole(BasePermission):
    """OpenAPI sxemasi faqat super admin va admin uchun (API xaritasi hujumchiga kerak emas)."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return has_role(request.user, Role.SUPER_ADMIN, Role.ADMIN)
