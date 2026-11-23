"""Kirish hodisalari audit jurnaliga (ADM-02): API va Django Admin login'i uchun bir xil."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.http import HttpRequest

from apps.accounts.backends import FAILURES_ATTR, LOCKED_ATTR, normalize_login
from apps.accounts.lockout import MAX_FAILURES
from apps.accounts.models import User
from apps.accounts.net import client_ip
from apps.audit import record
from apps.audit.models import Action
from config.observability import mask_text


def _ip(request: HttpRequest | None) -> str:
    return mask_text(client_ip(request)) if request is not None else "-"


@receiver(user_logged_in)
def _on_login(sender: Any, request: HttpRequest | None, user: User, **kwargs: Any) -> None:
    record(Action.LOGIN, actor=user, target=user, after={"ip": _ip(request)})


@receiver(user_logged_out)
def _on_logout(sender: Any, request: HttpRequest | None, user: User | None, **kwargs: Any) -> None:
    if isinstance(user, User):
        record(Action.LOGOUT, actor=user, target=user, after={"ip": _ip(request)})


@receiver(user_login_failed)
def _on_login_failed(
    sender: Any, credentials: dict[str, Any], request: HttpRequest | None = None, **kwargs: Any
) -> None:
    # Shovqin va DoS'ga qarshi faqat ikki hodisa yoziladi: oynadagi birinchi xato va blokni
    # boshlagan 5-xato. Blok paytidagi rad etishlar yozilmaydi.
    # Parol `credentials`dan hech qachon olinmaydi.
    if request is None or getattr(request, LOCKED_ATTR, False):
        return
    failures_before = getattr(request, FAILURES_ATTR, None)
    if failures_before not in (0, MAX_FAILURES - 1):
        return
    hemis_id = normalize_login(credentials.get("hemis_id") or credentials.get("username"))
    target = User.objects.filter(hemis_id=hemis_id).first()
    if target is None:
        return
    record(
        Action.LOGIN_FAILED,
        actor=None,
        target=target,
        after={"ip": _ip(request), "lock_started": failures_before == MAX_FAILURES - 1},
    )
