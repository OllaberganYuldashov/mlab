"""Tizim darajasidagi endpoint'lar (biznes mantiqisiz)."""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from config import observability


@never_cache
@require_safe
def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness: jarayon tirik va so'rovga javob beradi.

    Ataylab DB va Redis'ga murojaat qilmaydi — ular uchun `/readyz`.
    Autentifikatsiyasiz: Caddy va Docker healthcheck chaqiradi; hech qanday ma'lumot qaytarmaydi.
    """
    return JsonResponse({"status": "ok"})


@never_cache
@require_safe
def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness (R0-14, NFR-17): DB va Redis tayyor bo'lsa 200, aks holda 503.

    Caddy/deploy smoke testi shu bilan trafikni yo'naltiradi. Javobda faqat "ok"/"fail" —
    xato tafsiloti (host, parol, versiya) chiqmaydi, u maskalangan holda logga yoziladi.
    """
    checks = observability.readiness()
    ready = all(value == "ok" for value in checks.values())
    return JsonResponse(
        {"status": "ok" if ready else "unavailable", "checks": checks},
        status=200 if ready else 503,
    )
