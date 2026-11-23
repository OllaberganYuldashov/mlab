"""Real vaqt xabarlari (ACC-05). Xabar tranzaksiya tasdiqlangandan keyin ketadi (`on_commit`).

Redis ishlamasa HTTP amali (oynani ochish) buzilmaydi: xato logga yoziladi, talaba sahifani
yangilaganda (yoki taymer bilan) holatni API'dan oladi.
"""

from __future__ import annotations

import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger("mlab.realtime")


def section_group(section_id: int) -> str:
    return f"section-{section_id}"


def _send(group: str, message: dict[str, Any]) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(group, message)


def _safe_send(group: str, message: dict[str, Any]) -> None:
    try:
        _send(group, message)
    except Exception:  # Redis yo'q, tarmoq xatosi — amalni buzmaydi
        logger.exception(
            "realtime.send_failed", extra={"event": "realtime.send_failed", "group": group}
        )


def window_changed(section_id: int, payload: dict[str, Any]) -> None:
    """Guruh kanaliga oyna o'zgarishi; tranzaksiya qaytarilsa xabar ketmaydi."""
    message = {"type": "window.changed", **payload}
    transaction.on_commit(lambda: _safe_send(section_group(section_id), message))
