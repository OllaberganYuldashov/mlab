"""Mijoz IP manzilini aniqlash (Caddy ortida — `X-Forwarded-For`, `TRUSTED_PROXY_COUNT`).

Throttle, lockout va audit uchun yagona qoida: IPv4 — kanonik manzil (`::ffff:a.b.c.d` ham IPv4 ga
keltiriladi), IPv6 — /64 tarmoq (bitta abonentda 2^64 manzil bor: har biri yangi limit bo'lmasin).
"""

from __future__ import annotations

import ipaddress
from typing import Any

from django.conf import settings


def _raw_ip(request: Any) -> str:
    raw_proxies = settings.REST_FRAMEWORK.get("NUM_PROXIES") or 0
    proxies = raw_proxies if isinstance(raw_proxies, int) else 0
    meta = request.META
    if proxies > 0:
        forwarded = [p.strip() for p in str(meta.get("HTTP_X_FORWARDED_FOR", "")).split(",")]
        forwarded = [p for p in forwarded if p]
        if forwarded:
            return str(forwarded[-min(proxies, len(forwarded))])
    return str(meta.get("REMOTE_ADDR", "") or "")


def client_ip(request: Any) -> str:
    """`request` — Django HttpRequest yoki DRF Request (ikkalasida ham `.META`)."""
    raw = _raw_ip(request)
    try:
        address = ipaddress.ip_address(raw)
    except ValueError:
        return raw or "-"
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return str(address)
