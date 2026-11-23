"""AUTH-04: vaqtinchalik parol bilan kirgan foydalanuvchi parolni almashtirmaguncha boshqa
joyga kira olmaydi. Middleware darajasida — har yangi API yoki admin sahifasi avtomatik
himoyalangan (view'da unutib bo'lmaydi).
"""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.translation import gettext as _

ALLOWED_PATHS = frozenset(
    {
        "/api/auth/csrf",
        "/api/auth/me",
        "/api/auth/logout",
        "/api/auth/change-password",
        "/admin/password_change/",
        "/admin/password_change/done/",
        "/admin/logout/",
        "/admin/login/",
        "/healthz",
        "/readyz",
    }
)


class PasswordChangeRequiredMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and getattr(user, "must_change_password", False)
            and request.path not in ALLOWED_PATHS
        ):
            return JsonResponse(
                {"detail": _("Avval parolni almashtiring."), "code": "password_change_required"},
                status=403,
            )
        return self.get_response(request)
