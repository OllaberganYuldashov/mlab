"""NFR-08 (R0-15): prod konteynerlari va compose — xavfsizlik va resurs qoidalari.

Docker daemon bulut CI'da yo'q: image build o'rniga konfiguratsiya qoidalari tekshiriladi;
`docker compose config` — qo'shimcha qo'lda qadam (docs/learn/server.md).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "deploy" / "compose.prod.yaml").read_text(encoding="utf-8"))
SERVICES: dict[str, dict[str, Any]] = COMPOSE["services"]


def test_nfr_08_only_caddy_publishes_ports() -> None:
    published = {name for name, svc in SERVICES.items() if svc.get("ports")}
    assert published == {"caddy"}
    assert sorted(SERVICES["caddy"]["ports"]) == ["443:443", "80:80"]


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_nfr_08_every_service_has_memory_limit(name: str) -> None:
    assert SERVICES[name].get("mem_limit"), f"{name}: mem_limit yo'q"


def test_nfr_08_memory_budget_fits_4gb() -> None:
    def mb(value: str) -> int:
        match = re.fullmatch(r"(\d+)([mg])", value)
        assert match, value
        return int(match.group(1)) * (1024 if match.group(2) == "g" else 1)

    always_on = ("db", "redis", "web", "caddy")
    assert sum(mb(SERVICES[n]["mem_limit"]) for n in always_on) <= 2560  # 1.5 GB zaxira I3 uchun


@pytest.mark.parametrize("name", ["db", "redis", "web", "caddy"])
def test_nfr_08_long_running_services_have_healthcheck_and_restart(name: str) -> None:
    assert SERVICES[name].get("healthcheck"), name
    assert SERVICES[name]["restart"] == "unless-stopped"


@pytest.mark.parametrize("name", ["migrate", "web", "caddy"])
def test_nfr_08_app_containers_drop_capabilities(name: str) -> None:
    assert SERVICES[name]["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in SERVICES[name]["security_opt"]


def test_nfr_08_web_is_read_only_and_waits_for_migrations() -> None:
    web = SERVICES["web"]
    assert web["read_only"] is True
    assert web["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert SERVICES["migrate"]["restart"] == "no"


def test_nfr_08_no_literal_secrets_in_compose() -> None:
    text = (ROOT / "deploy" / "compose.prod.yaml").read_text(encoding="utf-8")
    # Secret'lar faqat ${VAR:?...} orqali majburiy; literal parol/kalit yo'q.
    for var in ("SECRET_KEY", "POSTGRES_PASSWORD", "ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS"):
        assert f"${{{var}:?" in text, f"{var} majburiy emas"
    assert not re.search(r"(PASSWORD|SECRET_KEY):\s+[A-Za-z0-9]{8,}\s*$", text, re.MULTILINE)


def test_nfr_08_trusted_proxy_count_defaults_to_one() -> None:
    assert COMPOSE["x-backend-env"]["TRUSTED_PROXY_COUNT"] == "${TRUSTED_PROXY_COUNT:-1}"


def test_nfr_08_database_and_redis_are_internal_only() -> None:
    assert COMPOSE["networks"] == {"internal": {}}
    for name in ("db", "redis", "web"):
        assert SERVICES[name]["networks"] == ["internal"]


@pytest.mark.parametrize("dockerfile", ["backend/Dockerfile", "frontend/Dockerfile"])
def test_nfr_08_images_run_as_non_root(dockerfile: str) -> None:
    lines = (ROOT / dockerfile).read_text(encoding="utf-8").splitlines()
    users = [ln.split()[1] for ln in lines if ln.startswith("USER ")]
    assert users, "USER yo'q — root bo'lib ishlaydi"
    assert users[-1] not in {"root", "0"}


def test_nfr_08_backend_image_installs_from_lockfile_without_dev_deps() -> None:
    text = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "uv sync --frozen --no-dev" in text
    assert "FROM python:" in text
    assert text.count("FROM ") == 2  # multi-stage


def test_nfr_08_caddyfile_security_headers_and_spa_fallback() -> None:
    text = (ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    for header in (
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Content-Security-Policy",
        "Referrer-Policy",
    ):
        assert header in text, header
    assert "try_files {path} /index.html" in text
    assert "admin off" in text
    hsts = next(
        ln for ln in text.splitlines() if ln.strip().startswith("Strict-Transport-Security")
    )
    assert "includeSubDomains" not in hsts  # domen ma'lum bo'lgunga qadar (SRS 12)
    assert "{$SITE_ADDRESS::80}" in text


def test_nfr_08_dockerignore_excludes_secrets() -> None:
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for entry in (".env", ".env.*", ".git"):
        assert entry in lines


def test_acc_05_websocket_routed_to_django_with_small_frame_limit() -> None:
    caddy = (ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    matcher = next(ln for ln in caddy.splitlines() if ln.strip().startswith("@backend"))
    assert "/ws/*" in matcher
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert '"--ws-max-size", "65536"' in dockerfile


def test_nfr_17_uvicorn_access_log_disabled() -> None:
    """Uvicorn access log'i JsonFormatter'dan o'tmaydi va `/api/join/<token>` ni ochiq
    yozardi (I1-15); so'rov logi Django `request.finished` qatorida (yo'l `safe_path` bilan)."""
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert '"--no-access-log"' in dockerfile
