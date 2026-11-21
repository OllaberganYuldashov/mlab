"""config.env yordamchilari: muhit o'zgaruvchilarini qat'iy o'qish (NFR-16, fail fast)."""

from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured

from config import env


def test_required_returns_stripped_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLAB_X", "  qiymat ")
    assert env.required("MLAB_X") == "qiymat"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_required_raises_with_variable_name(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("MLAB_X", raising=False)
    else:
        monkeypatch.setenv("MLAB_X", value)
    with pytest.raises(ImproperlyConfigured, match="MLAB_X"):
        env.required("MLAB_X")


def test_required_list_splits_and_drops_blanks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLAB_HOSTS", " a.uz , ,b.uz,")
    assert env.required_list("MLAB_HOSTS") == ["a.uz", "b.uz"]


def test_required_list_with_only_separators_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLAB_HOSTS", " , ,")
    with pytest.raises(ImproperlyConfigured, match="MLAB_HOSTS"):
        env.required_list("MLAB_HOSTS")


def test_optional_list_defaults_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MLAB_ORIGINS", raising=False)
    assert env.optional_list("MLAB_ORIGINS") == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("true", True), ("1", True), ("YES", True), ("false", False), ("0", False), ("no", False)],
)
def test_boolean_parses_known_values(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool
) -> None:
    monkeypatch.setenv("MLAB_FLAG", raw)
    assert env.boolean("MLAB_FLAG", default=not expected) is expected


def test_boolean_uses_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MLAB_FLAG", raising=False)
    assert env.boolean("MLAB_FLAG", default=True) is True


def test_boolean_rejects_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLAB_FLAG", "ha")
    with pytest.raises(ImproperlyConfigured, match="MLAB_FLAG"):
        env.boolean("MLAB_FLAG", default=False)


def test_database_parses_postgres_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLAB_DB", "postgres://u:p@db.local:5433/mlab")
    cfg = env.database("MLAB_DB")
    assert cfg["ENGINE"] == "django.db.backends.postgresql"
    assert (cfg["HOST"], cfg["PORT"], cfg["NAME"], cfg["USER"]) == ("db.local", 5433, "mlab", "u")


def test_database_rejects_non_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MLAB_DB", "sqlite:///tmp/x.db")
    with pytest.raises(ImproperlyConfigured, match="MLAB_DB"):
        env.database("MLAB_DB")


@pytest.mark.parametrize("key", ["dev-only-change-me", "test-only-" + "x" * 60, "short", "a" * 60])
def test_production_rejects_weak_secret_key(key: str) -> None:
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        env.validate_production(secret_key=key, allowed_hosts=["mlab.example.uz"])


def test_production_rejects_wildcard_host() -> None:
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        env.validate_production(secret_key="Abc1Def2Ghi3" * 5, allowed_hosts=["*"])


def test_production_accepts_strong_settings() -> None:
    env.validate_production(secret_key="Abc1Def2Ghi3" * 5, allowed_hosts=["mlab.example.uz"])
