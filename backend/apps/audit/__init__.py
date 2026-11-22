"""Audit jurnali (ADM-02). Ommaviy API: `from apps.audit import record`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.db.models import Model

    from apps.accounts.models import User
    from apps.audit.models import Action, AuditLog


def _scrub(value: Any) -> Any:
    from config.observability import is_sensitive_key

    if isinstance(value, dict):
        # Secret kalitlar butunlay tashlanadi (hatto "[REDACTED]" ham yozilmaydi).
        return {str(k): _scrub(v) for k, v in value.items() if not is_sensitive_key(str(k))}
    if isinstance(value, list | tuple):
        return [_scrub(item) for item in value]
    return value


def record(
    action: Action,
    *,
    actor: User | None,
    target: Model,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    """Audit yozuvi qo'shadi. Parol, token, cookie kabi kalitlar umuman saqlanmaydi.

    Chaqiruvchi tranzaksiya ichida bo'lsa, yozuv ham o'sha tranzaksiya bilan birga qaytariladi
    (harakat bo'lmagan bo'lsa, uning izi ham qolmaydi).
    """
    from apps.audit.models import AuditLog
    from config.observability import current_request_id

    request_id = current_request_id()
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target._meta.label_lower,
        target_id=str(target.pk),
        before=_scrub(before or {}),
        after=_scrub(after or {}),
        request_id="" if request_id == "-" else request_id,
    )
