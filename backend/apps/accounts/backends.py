"""Yagona autentifikatsiya backend'i: API va Django Admin login'i shu yerdan o'tadi (lockout)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import ModelBackend
from django.http import HttpRequest

from apps.accounts import lockout
from apps.accounts.models import User
from apps.accounts.net import client_ip

LOCKED_ATTR = "_mlab_login_locked"
FAILURES_ATTR = "_mlab_login_failures_before"


def normalize_login(raw: Any) -> str:
    """Kiritilgan Hemis ID bo'sh joylarsiz (format noto'g'ri bo'lsa ham — javob bir xil)."""
    return "".join(str(raw or "").split())


class LockoutModelBackend(ModelBackend):
    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        hemis_id = normalize_login(kwargs.pop("hemis_id", None) or username)
        ip = client_ip(request) if request is not None else "-"
        if lockout.over_rate(ip):
            return self._reject(request)
        attempt = lockout.begin(hemis_id, ip)
        if not attempt.allowed:
            return self._reject(request)
        if request is not None:
            setattr(request, FAILURES_ATTR, attempt.failures_before)
        user = super().authenticate(request, username=hemis_id, password=password, **kwargs)
        if user is None:
            # 5-xato javobi oddiy "noto'g'ri"; blok keyingi urinishdan boshlanadi.
            lockout.failed(hemis_id, ip, attempt)
            return None
        lockout.succeeded(hemis_id, ip)
        return user

    @staticmethod
    def _reject(request: HttpRequest | None) -> None:
        if request is not None:
            setattr(request, LOCKED_ATTR, True)
        return None
