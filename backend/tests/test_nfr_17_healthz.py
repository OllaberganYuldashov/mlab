"""NFR-17/R0-01: /healthz — liveness tekshiruvi (tashqi servislarsiz, autentifikatsiyasiz)."""

from __future__ import annotations

import pytest
from django.test import Client


def test_nfr_17_healthz_returns_ok(client: Client) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "no-store" in response["Cache-Control"]


def test_nfr_17_healthz_allows_head(client: Client) -> None:
    assert client.head("/healthz").status_code == 200


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_nfr_17_healthz_rejects_unsafe_methods(client: Client, method: str) -> None:
    assert getattr(client, method)("/healthz").status_code == 405


def test_nfr_17_healthz_does_not_touch_database(client: Client) -> None:
    # django_db belgisi yo'q: pytest-django bu testda bazaga har qanday murojaatni xato qiladi.
    # Demak /healthz DB yoki migratsiya holatidan qat'i nazar javob beradi (liveness).
    assert client.get("/healthz").status_code == 200


def test_unknown_url_is_404(client: Client) -> None:
    assert client.get("/yoq-sahifa").status_code == 404
