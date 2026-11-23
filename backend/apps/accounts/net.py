"""Mijoz IP manzilini aniqlash (Caddy ortida — `X-Forwarded-For`, `TRUSTED_PROXY_COUNT`)."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str:
    """DRF throttle bilan bir xil qoida: ishonchli proksilar soni bo'yicha XFF'dan olinadi."""
    raw_proxies = settings.REST_FRAMEWORK.get("NUM_PROXIES") or 0
    proxies = raw_proxies if isinstance(raw_proxies, int) else 0
    remote = str(request.META.get("REMOTE_ADDR", "") or "")
    if proxies > 0:
        forwarded = [
            p.strip() for p in str(request.META.get("HTTP_X_FORWARDED_FOR", "")).split(",")
        ]
        forwarded = [p for p in forwarded if p]
        if forwarded:
            return str(forwarded[-min(proxies, len(forwarded))])
    return remote or "-"
