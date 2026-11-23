"""AUTH-02: 5 ta xato urinish → 15 daqiqa blok. Kalit — Hemis ID + IP (egasining qarori, #11).

Saqlash: Redis (Django cache). Sabablar: TTL tabiiy; har xato urinish bazaga yozilmaydi; Redis qayta
ishga tushsa bloklar tozalanadi (qisqa muddatli — qabul qilinadi).

Poyga (race) yo'q: urinish parol tekshiruvidan **oldin** atomik `INCR` bilan band qilinadi.
Bir vaqtda
yuborilgan 20 ta so'rovdan faqat 5 tasi parolni tekshirishga yetadi; qolgani darhol bloklanadi.
Muvaffaqiyatli kirish hisoblagichni nolga qaytaradi. Blok muddati `now()` bilan solishtiriladi
(testda
soxta soat). Redis kalitlarida Hemis ID va IP ochiq emas — SHA-256 xeshi.

Qo'shimcha: IP bo'yicha va umumiy daqiqalik chegara (`AUTH_LOGIN_RATE`, `AUTH_LOGIN_GLOBAL_RATE`) —
ko'p Hemis ID'ni bitta paroldan sinash (password spraying) va Argon2 yuklamasiga qarshi; API va
Django Admin login'i uchun bir xil (backend ichida).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

MAX_FAILURES = 5
LOCK_DURATION = timedelta(minutes=15)
_CACHE_TTL = int((LOCK_DURATION + timedelta(minutes=1)).total_seconds())
_PERIODS = {"second": 1, "minute": 60, "hour": 3600}


def now() -> datetime:
    return timezone.now()


def _key(kind: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode()).hexdigest()
    return f"auth:{kind}:{digest}"


def _incr(key: str, ttl: int) -> int:
    cache.add(key, 0, ttl)  # SET NX — oynani birinchi urinish ochadi
    try:
        return int(cache.incr(key))  # Redis INCRBY — atomik
    except ValueError:  # kalit shu orada muddati tugab o'chdi
        cache.add(key, 1, ttl)
        return 1


@dataclass(frozen=True)
class Attempt:
    allowed: bool
    failures_before: int  # shu urinishdan oldingi xatolar soni (audit uchun)


def is_locked(hemis_id: str, ip: str) -> bool:
    locked_until = cache.get(_key("lock", hemis_id, ip))
    return isinstance(locked_until, datetime) and now() < locked_until


def _lock(hemis_id: str, ip: str) -> None:
    cache.add(_key("lock", hemis_id, ip), now() + LOCK_DURATION, _CACHE_TTL)


def begin(hemis_id: str, ip: str) -> Attempt:
    """Parolni tekshirishdan oldin chaqiriladi. `allowed=False` — tekshirmasdan rad etish."""
    lock_key = _key("lock", hemis_id, ip)
    locked_until = cache.get(lock_key)
    if isinstance(locked_until, datetime):
        if now() < locked_until:
            return Attempt(allowed=False, failures_before=MAX_FAILURES)
        cache.delete_many([lock_key, _key("fail", hemis_id, ip)])  # blok tugadi — yangi oyna
    count = _incr(_key("fail", hemis_id, ip), int(LOCK_DURATION.total_seconds()))
    if count > MAX_FAILURES:
        _lock(hemis_id, ip)
        return Attempt(allowed=False, failures_before=MAX_FAILURES)
    return Attempt(allowed=True, failures_before=count - 1)


def failed(hemis_id: str, ip: str, attempt: Attempt) -> None:
    """Parol xato: band qilingan urinish xato bo'lib qoladi; 5-xatoda blok boshlanadi."""
    if attempt.failures_before + 1 >= MAX_FAILURES:
        _lock(hemis_id, ip)


def succeeded(hemis_id: str, ip: str) -> None:
    cache.delete_many([_key("fail", hemis_id, ip), _key("lock", hemis_id, ip)])


def _parse_rate(rate: str) -> tuple[int, int]:
    count, period = rate.split("/")
    return int(count), _PERIODS[period]


def over_rate(ip: str) -> bool:
    """IP bo'yicha va umumiy daqiqalik chegara (Hemis ID'dan qat'i nazar)."""
    for scope, ident, rate in (
        ("ip", ip, str(settings.AUTH_LOGIN_RATE)),
        ("global", "all", str(settings.AUTH_LOGIN_GLOBAL_RATE)),
    ):
        limit, seconds = _parse_rate(rate)
        if _incr(_key(f"rate-{scope}", ident), seconds) > limit:
            return True
    return False
