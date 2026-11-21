"""Tizim darajasidagi endpoint'lar (biznes mantiqisiz)."""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


@never_cache
@require_safe
def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness: jarayon tirik va so'rovga javob beradi.

    Ataylab DB va Redis'ga murojaat qilmaydi — ular uchun `/readyz` (R0-14).
    Autentifikatsiyasiz: Caddy va Docker healthcheck chaqiradi; hech qanday ma'lumot qaytarmaydi.
    """
    return JsonResponse({"status": "ok"})
