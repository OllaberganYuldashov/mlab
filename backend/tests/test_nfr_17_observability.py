"""NFR-17/NFR-11 (R0-14): request id, JSON loglar, shaxsiy ma'lumotni maskalash, /readyz."""

from __future__ import annotations

import json
import logging
import secrets
import sys
from typing import Any
from unittest import mock

import pytest
from django.db import OperationalError
from django.test import Client, override_settings

from config import observability
from config.observability import JsonFormatter, mask_text


def _record(msg: str, *args: object, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("mlab.test", logging.INFO, __file__, 1, msg, args, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def _format(record: logging.LogRecord) -> dict[str, object]:
    out = json.loads(JsonFormatter().format(record))
    assert isinstance(out, dict)
    return out


# --- Request ID ---


def test_nfr_17_request_id_generated_when_missing(client: Client) -> None:
    response = client.get("/healthz")
    rid = response["X-Request-ID"]
    assert len(rid) == 32
    assert rid.isalnum()


def test_nfr_17_request_id_accepted_from_proxy(client: Client) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "caddy-abc.123_X"})
    assert response["X-Request-ID"] == "caddy-abc.123_X"


@pytest.mark.parametrize("bad", ["a" * 65, "bad id", "x\ny", "<script>", "ид"])
def test_nfr_17_invalid_request_id_replaced(client: Client, bad: str) -> None:
    # Log in'ektsiyasining oldini olish: faqat [A-Za-z0-9._-]{1,64} qabul qilinadi.
    response = client.get("/healthz", headers={"X-Request-ID": bad})
    assert response["X-Request-ID"] != bad
    assert len(response["X-Request-ID"]) == 32


def test_nfr_17_request_id_in_log_lines_and_reset_after_request(
    client: Client, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="mlab.request"):
        client.get("/yoq-sahifa", headers={"X-Request-ID": "rid-1"})
    done = [r for r in caplog.records if r.name == "mlab.request"]
    assert len(done) == 1
    assert done[0].request_id == "rid-1"  # type: ignore[attr-defined]
    assert done[0].status == 404  # type: ignore[attr-defined]
    assert done[0].method == "GET"  # type: ignore[attr-defined]
    assert observability.current_request_id() == "-"


def test_nfr_17_request_log_has_no_query_string(
    client: Client, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="mlab.request"):
        client.get("/yoq-sahifa?token=abc")
    done = next(r for r in caplog.records if r.name == "mlab.request")
    assert done.path == "/yoq-sahifa"  # type: ignore[attr-defined]


def test_nfr_17_successful_health_probes_not_logged(
    client: Client, caplog: pytest.LogCaptureFixture
) -> None:
    # Docker/Caddy har necha soniyada chaqiradi — loglar to'lib ketmasin.
    with caplog.at_level(logging.INFO, logger="mlab.request"):
        client.get("/healthz")
    assert not [r for r in caplog.records if r.name == "mlab.request"]


# --- JSON formatter ---


def test_nfr_17_json_formatter_has_required_fields() -> None:
    out = _format(_record("salom %s", "dunyo"))
    assert out["message"] == "salom dunyo"
    assert out["level"] == "INFO"
    assert out["logger"] == "mlab.test"
    assert out["request_id"] == "-"
    assert str(out["timestamp"]).endswith("+00:00")


def test_nfr_17_json_formatter_includes_extra_and_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record("xato", event="demo.failed")
        record.exc_info = sys.exc_info()
    out = _format(record)
    assert out["event"] == "demo.failed"
    assert "ValueError: boom" in str(out["exc_info"])


def test_nfr_17_json_formatter_survives_unserializable_extra() -> None:
    out = _format(_record("x", obj=object()))
    assert str(out["obj"]).startswith("<object")


# --- Maskalash (NFR-11, SECURITY.md) ---


def test_nfr_11_hemis_id_masked_in_message() -> None:
    out = _format(_record("login failed for %s", "123456789012"))
    assert "123456789012" not in json.dumps(out)
    assert "********9012" in str(out["message"])


def test_nfr_11_hemis_id_masked_in_extra() -> None:
    out = _format(_record("x", hemis_id="123456789012"))
    assert out["hemis_id"] == "********9012"


def test_nfr_11_longer_digit_runs_not_mistaken_for_hemis_id() -> None:
    assert mask_text("order 12345678901234") == "order 12345678901234"


@pytest.mark.parametrize(
    ("raw", "masked"),
    [
        ("from 192.168.10.25 ok", "from 192.168.10.x ok"),
        ("ip=10.0.0.1", "ip=10.0.0.x"),
        ("2001:db8:85a3::8a2e:370:7334", "2001:db8:x:x"),
    ],
)
def test_nfr_11_ip_masked(raw: str, masked: str) -> None:
    assert mask_text(raw) == masked


def test_nfr_11_ip_masked_in_extra() -> None:
    assert _format(_record("x", ip="172.16.5.4"))["ip"] == "172.16.5.x"


@pytest.mark.parametrize(
    "key",
    ["password", "new_password", "token", "csrftoken", "sessionid", "cookie", "Authorization"],
)
def test_nfr_11_sensitive_extra_fields_never_logged(key: str) -> None:
    value = secrets.token_urlsafe(16)
    line = JsonFormatter().format(_record("x", **{key: value}))
    assert value not in line
    assert json.loads(line)[key] == "[REDACTED]"


@pytest.mark.parametrize(
    "template",
    [
        "password={}",
        "Authorization: Bearer {}",
        "Cookie: sessionid={}",
        '{{"token": "{}"}}',
        "secret={}",
    ],
)
def test_nfr_11_sensitive_values_in_message_redacted(template: str) -> None:
    value = secrets.token_urlsafe(16)
    line = JsonFormatter().format(_record(template.format(value)))
    assert value not in line


def test_nfr_11_nested_extra_masked() -> None:
    value = secrets.token_urlsafe(16)
    out = _format(_record("x", data={"user": {"password": value, "ip": "10.1.2.3"}}))
    assert value not in json.dumps(out)
    assert out["data"] == {"user": {"password": "[REDACTED]", "ip": "10.1.2.x"}}


def test_nfr_17_logging_configured_with_json_formatter() -> None:
    from django.conf import settings

    logging_config: dict[str, Any] = settings.LOGGING
    assert logging_config["formatters"]["json"]["()"] == "config.observability.JsonFormatter"
    assert settings.MIDDLEWARE[0] == "config.observability.RequestIdMiddleware"


# --- /readyz ---


@pytest.mark.django_db
def test_nfr_17_readyz_ok_when_db_and_redis_ready(client: Client) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"db": "ok", "redis": "ok"}}
    assert "no-store" in response["Cache-Control"]


@pytest.mark.django_db
def test_nfr_17_readyz_503_when_db_down(client: Client) -> None:
    with mock.patch.object(
        observability, "_check_db", side_effect=OperationalError("password=leak 10.0.0.9")
    ):
        response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "checks": {"db": "fail", "redis": "ok"}}
    # Xato tafsiloti javobga chiqmaydi.
    assert b"leak" not in response.content


@pytest.mark.django_db
def test_nfr_17_readyz_503_when_redis_down(client: Client) -> None:
    # Yopiq port: haqiqiy ulanish xatosi (mock emas).
    with override_settings(REDIS_URL="redis://127.0.0.1:1/0"):
        response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["checks"] == {"db": "ok", "redis": "fail"}


def test_nfr_17_readyz_rejects_unsafe_methods(client: Client) -> None:
    assert client.post("/readyz").status_code == 405


def test_nfr_17_readyz_db_check_really_queries() -> None:
    # _check_db haqiqatan bazaga boradi: DB bloklangan bo'lsa xato beradi.
    with pytest.raises(RuntimeError, match="Database access not allowed"):
        observability._check_db()


@pytest.mark.parametrize("text", ["version 999.1.1.1", "soat 12:30:45", "1.2.3"])
def test_nfr_11_non_ip_text_not_masked(text: str) -> None:
    assert mask_text(text) == text


def test_nfr_11_list_extra_masked() -> None:
    assert _format(_record("x", ips=["10.0.0.1", 5]))["ips"] == ["10.0.0.x", 5]
