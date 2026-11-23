"""AUTH-02: 5 ta xato urinish → 15 daqiqa blok. Kalit — Hemis ID + IP (egasining qarori, #11).

Saqlash: Redis (Django cache). Sabablar: TTL tabiiy; har xato urinish bazaga yozuv qilmaydi (hujumda
DB yuklanmaydi); Redis qayta ishga tushsa bloklar tozalanadi — bu xavfsiz tomonga xato emas, lekin
qisqa muddatli va qabul qilinadi. Vaqt solishtiruvi `now()` orqali (testda soxta soat).
Redis kalitida Hemis ID va IP ochiq emas — SHA-256 xeshi.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import timezone

MAX_FAILURES = 5
LOCK_DURATION = timedelta(minutes=15)
# Kesh yozuvi blokdan biroz uzoqroq yashaydi; haqiqiy qaror `now()` bilan solishtirib qilinadi.
_CACHE_TTL = int((LOCK_DURATION + timedelta(minutes=1)).total_seconds())


def now() -> datetime:
    return timezone.now()


def _key(kind: str, hemis_id: str, ip: str) -> str:
    digest = hashlib.sha256(f"{hemis_id}\0{ip}".encode()).hexdigest()
    return f"auth:{kind}:{digest}"


def is_locked(hemis_id: str, ip: str) -> bool:
    locked_until = cache.get(_key("lock", hemis_id, ip))
    return isinstance(locked_until, datetime) and now() < locked_until


def register_failure(hemis_id: str, ip: str) -> bool:
    """Xato urinishni hisoblaydi. Blok boshlangan bo'lsa True."""
    key = _key("fail", hemis_id, ip)
    current = now()
    state = cache.get(key)
    if not isinstance(state, dict) or current - state["first"] > LOCK_DURATION:
        state = {"first": current, "count": 0}
    state["count"] += 1
    if state["count"] >= MAX_FAILURES:
        cache.set(_key("lock", hemis_id, ip), current + LOCK_DURATION, _CACHE_TTL)
        cache.delete(key)
        return True
    cache.set(key, state, _CACHE_TTL)
    return False


def reset(hemis_id: str, ip: str) -> None:
    cache.delete_many([_key("fail", hemis_id, ip), _key("lock", hemis_id, ip)])
