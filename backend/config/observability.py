"""Kuzatuvchanlik (NFR-17) va loglarda maxfiylik (NFR-11, docs/SECURITY.md).

- `RequestIdMiddleware`: har so'rovga `X-Request-ID` (proksidan kelganini qabul qiladi yoki
  yaratadi), u har log qatoriga tushadi va javobga qaytadi; so'rov oxirida bitta
  `request.finished` qatori.
- `JsonFormatter`: bir qator — bitta JSON obyekt. Formatter darajasida maskalash: Hemis ID va
  IP qisman yashiriladi; parol, token, cookie, Authorization qiymatlari hech qachon yozilmaydi.
  "Esimda bo'lsa yashiraman" emas — har log qatori shu yerdan o'tadi.
- `readiness()`: `/readyz` uchun DB va Redis tekshiruvi (liveness — `/healthz`,
  tashqi servislarsiz).
"""

from __future__ import annotations

import contextvars
import ipaddress
import json
import logging
import re
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import redis
from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("mlab.request")
readiness_logger = logging.getLogger("mlab.readiness")

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}\Z")
_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

# Sog'liq tekshiruvlari har necha soniyada chaqiriladi — muvaffaqiyatli bo'lsa loglanmaydi.
_QUIET_PATHS = frozenset({"/healthz", "/readyz"})

REDACTED = "[REDACTED]"
_SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "token",
    "secret",
    "cookie",
    "authorization",
    "sessionid",
    "csrf",
    "api_key",
    "apikey",
)
_SENSITIVE_IN_TEXT = re.compile(
    r"(?i)\b(password|passwd|token|csrftoken|secret|api[_-]?key|sessionid|authorization|cookie)\b"
    r"([\"']?\s*[:=]\s*[\"']?)"
    r"((?:bearer|basic|token)\s+)?"
    r"([^\s\"',;&]+)"
)
_HEMIS_ID_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_IPV4_RE = re.compile(r"(?<![\d.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\d.])")
_IPV6_CANDIDATE_RE = re.compile(
    r"(?<![0-9A-Za-z:])[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}(?![0-9A-Za-z:])"
)

# LogRecord'ning standart atributlari — qolgani `extra` sifatida JSON'ga qo'shiladi.
_RECORD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys() | {"message", "asctime"}
)


def current_request_id() -> str:
    return _request_id.get()


def _mask_ipv4(match: re.Match[str]) -> str:
    if all(int(part) <= 255 for part in match.groups()):
        return ".".join(match.groups()[:3]) + ".x"
    return match.group(0)


def _mask_ipv6(match: re.Match[str]) -> str:
    text = match.group(0)
    try:
        ipaddress.IPv6Address(text)
    except ValueError:
        return text
    head = [group for group in text.split(":") if group][:2]
    return ":".join(head) + ":x:x"


# Matn ichidagi join token, masalan `django.request` ning
# "Internal Server Error: /api/join/<token>" xabari.
_JOIN_TOKEN_IN_TEXT = re.compile(r"(/(?:api/)?join/)[A-Za-z0-9_-]{16,64}")


def mask_text(text: str) -> str:
    """Matndagi secret qiymatlar, join token, Hemis ID va IP manzillarni yashiradi."""
    text = _SENSITIVE_IN_TEXT.sub(lambda m: f"{m[1]}{m[2]}{m[3] or ''}{REDACTED}", text)
    text = _JOIN_TOKEN_IN_TEXT.sub(rf"\1{REDACTED}", text)
    text = _IPV4_RE.sub(_mask_ipv4, text)
    text = _IPV6_CANDIDATE_RE.sub(_mask_ipv6, text)
    return _HEMIS_ID_RE.sub(lambda m: "********" + m.group(0)[-4:], text)


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def mask_value(key: str, value: Any) -> Any:
    if is_sensitive_key(key):
        return REDACTED
    if isinstance(value, dict):
        return {str(k): mask_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [mask_value(key, v) for v in value]
    if value is None or isinstance(value, bool | int | float):
        return value
    return mask_text(str(value))


class JsonFormatter(logging.Formatter):
    """Bir qator JSON: timestamp (UTC), level, logger, request_id, message va extra maydonlar."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", None) or current_request_id(),
            "message": mask_text(record.getMessage()),
        }
        for key, value in vars(record).items():
            if key not in _RECORD_ATTRS and key not in payload:
                payload[key] = mask_value(key, value)
        if record.exc_info:
            payload["exc_info"] = mask_text(self.formatException(record.exc_info))
        if record.stack_info:
            payload["stack_info"] = mask_text(self.formatStack(record.stack_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


class RequestIdMiddleware:
    """MIDDLEWARE ro'yxatida birinchi turadi: keyingi har log qatorida request_id bo'ladi."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        token = _request_id.set(request_id)
        started = time.monotonic()
        try:
            response = self.get_response(request)
            response[REQUEST_ID_HEADER] = request_id
            if request.path not in _QUIET_PATHS or response.status_code >= 400:
                logger.log(
                    logging.WARNING if response.status_code >= 500 else logging.INFO,
                    "request.finished",
                    extra={
                        "event": "request.finished",
                        "request_id": request_id,
                        "method": request.method,
                        # Query string yozilmaydi; yo'ldagi secret (qo'shilish tokeni) niqoblanadi.
                        "path": safe_path(request.path),
                        "status": response.status_code,
                        "duration_ms": round((time.monotonic() - started) * 1000, 1),
                    },
                )
            return response
        finally:
            _request_id.reset(token)


# Yo'lda secret bo'ladigan manzillar: `/api/join/<token>` (I1-04). Token logga tushmaydi.
_SECRET_PATH_RE = re.compile(r"^(/(?:api/)?join/)[^/]+")


def safe_path(path: str) -> str:
    return _SECRET_PATH_RE.sub(r"\1[REDACTED]", path)


def _check_db() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


def _check_redis() -> None:
    client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
    try:
        client.ping()
    finally:
        client.close()


def readiness() -> dict[str, str]:
    """Har tekshiruv: "ok" yoki "fail". Xato tafsiloti faqat logga (maskalangan), javobga emas."""
    checks: dict[str, Callable[[], None]] = {"db": _check_db, "redis": _check_redis}
    results: dict[str, str] = {}
    for name, check in checks.items():
        try:
            check()
        except Exception as exc:  # har qanday xato — "tayyor emas" degani
            results[name] = "fail"
            readiness_logger.warning(
                "readiness.check_failed",
                extra={
                    "event": "readiness.check_failed",
                    "check": name,
                    "error": type(exc).__name__,
                },
            )
        else:
            results[name] = "ok"
    return results
