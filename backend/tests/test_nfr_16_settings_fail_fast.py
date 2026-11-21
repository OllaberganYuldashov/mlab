"""NFR-16/R0-01: majburiy sozlama yo'q bo'lsa ilova ishga tushmaydi (fail fast).

Har holat alohida Python jarayonida tekshiriladi: sozlamalar modul import qilinganda o'qiladi,
shuning uchun haqiqiy ishga tushishni faqat yangi jarayon to'g'ri ko'rsatadi.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]

DEV_ENV = {
    "SECRET_KEY": "dev-only-change-me",
    "DATABASE_URL": "postgres://mlab:mlab@localhost:5432/mlab",
    "REDIS_URL": "redis://localhost:6379/0",
    "ALLOWED_HOSTS": "localhost,127.0.0.1",
}
STRONG_KEY = "Abc1Def2Ghi3" * 5  # 60 belgi, soxta, faqat test uchun

PROBE = (
    "import django; django.setup(); from django.conf import settings; "
    "print(settings.DEBUG, settings.SESSION_COOKIE_SECURE, settings.CSRF_COOKIE_SECURE)"
)


def run_django(settings_module: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    clean_env = {"PATH": os.environ.get("PATH", ""), "DJANGO_SETTINGS_MODULE": settings_module}
    clean_env.update(env)
    return subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=BACKEND_DIR,
        env=clean_env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize("missing", sorted(DEV_ENV))
def test_nfr_16_app_refuses_to_start_without_required_setting(missing: str) -> None:
    env = {k: v for k, v in DEV_ENV.items() if k != missing}
    result = run_django("config.settings.dev", env)
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert missing in result.stderr


@pytest.mark.parametrize("missing", sorted(DEV_ENV))
def test_nfr_16_blank_value_counts_as_missing(missing: str) -> None:
    env = {**DEV_ENV, missing: "   "}
    result = run_django("config.settings.dev", env)
    assert result.returncode != 0
    assert missing in result.stderr


def test_nfr_16_dev_starts_with_all_required_settings() -> None:
    result = run_django("config.settings.dev", DEV_ENV)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["False", "False", "False"]


def test_nfr_16_dev_debug_is_read_from_env() -> None:
    result = run_django("config.settings.dev", {**DEV_ENV, "DEBUG": "true"})
    assert result.returncode == 0, result.stderr
    assert result.stdout.split()[0] == "True"


def test_nfr_16_invalid_boolean_is_rejected() -> None:
    result = run_django("config.settings.dev", {**DEV_ENV, "DEBUG": "ha"})
    assert result.returncode != 0
    assert "DEBUG" in result.stderr


def test_nfr_16_prod_rejects_dev_secret_key() -> None:
    result = run_django("config.settings.prod", DEV_ENV)
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr


def test_nfr_16_prod_rejects_wildcard_host() -> None:
    env = {**DEV_ENV, "SECRET_KEY": STRONG_KEY, "ALLOWED_HOSTS": "*"}
    result = run_django("config.settings.prod", env)
    assert result.returncode != 0
    assert "ALLOWED_HOSTS" in result.stderr


def test_nfr_16_prod_starts_secure_with_valid_settings() -> None:
    env = {**DEV_ENV, "SECRET_KEY": STRONG_KEY, "ALLOWED_HOSTS": "mlab.example.uz"}
    result = run_django("config.settings.prod", env)
    assert result.returncode == 0, result.stderr
    # DEBUG o'chiq, cookie'lar faqat HTTPS orqali
    assert result.stdout.split() == ["False", "True", "True"]
