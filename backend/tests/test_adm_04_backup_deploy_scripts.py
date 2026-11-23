"""ADM-04, NFR-08 (R0-16): zaxira, tiklash va deploy skriptlari.

Haqiqiy bash soxta `docker` va `curl` bilan ishga tushadi.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy"

FAKE_DOCKER = """#!/usr/bin/env bash
echo "docker $*" >> "$FAKE_LOG"
case "$*" in
  *"pg_dump"*)
    [ "${FAKE_DUMP_FAIL:-0}" = "1" ] && exit 1
    printf '%s' "${FAKE_DUMP_BODY-DUMP-BYTES}" ;;
  *"pg_restore"*) cat > "$FAKE_RESTORE_STDIN" ;;
  *"ps --status running"*) echo db ;;
esac
exit 0
"""
FAKE_CURL = '#!/usr/bin/env bash\necho "curl $*" >> "$FAKE_LOG"\nexit 0\n'


@pytest.fixture
def sandbox(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("docker", FAKE_DOCKER), ("curl", FAKE_CURL)):
        script = bin_dir / name
        script.write_text(body)
        script.chmod(0o755)
    env_file = tmp_path / "env"
    env_file.write_text("SITE_ADDRESS=mlab.example.uz\nPOSTGRES_PASSWORD=x\n")
    env_file.chmod(0o600)
    backups = tmp_path / "backups"
    return {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "MLAB_ENV_FILE": str(env_file),
        "MLAB_BACKUP_DIR": str(backups),
        "FAKE_LOG": str(tmp_path / "log"),
        "FAKE_RESTORE_STDIN": str(tmp_path / "restored"),
        "SMOKE_PAUSE": "0",
        "SMOKE_ATTEMPTS": "1",
        "HOME": str(tmp_path),
    }


def run(script: str, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(DEPLOY / script), *args],  # noqa: S607
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def dumps(env: dict[str, str]) -> list[Path]:
    return sorted(Path(env["MLAB_BACKUP_DIR"]).glob("db-*.dump"))


def test_adm_04_backup_creates_private_dump(sandbox: dict[str, str]) -> None:
    result = run("backup.sh", "backup", env=sandbox)
    assert result.returncode == 0, result.stderr
    (dump,) = dumps(sandbox)
    assert dump.read_text() == "DUMP-BYTES"
    assert oct(dump.stat().st_mode & 0o777) == "0o600"  # faqat egasi o'qiydi
    assert not list(Path(sandbox["MLAB_BACKUP_DIR"]).glob("*.part"))


def test_adm_04_failed_dump_leaves_no_file(sandbox: dict[str, str]) -> None:
    result = run("backup.sh", "backup", env={**sandbox, "FAKE_DUMP_FAIL": "1"})
    assert result.returncode != 0
    assert dumps(sandbox) == []
    assert not list(Path(sandbox["MLAB_BACKUP_DIR"]).glob("*.part"))


def test_adm_04_empty_dump_is_rejected(sandbox: dict[str, str]) -> None:
    result = run("backup.sh", "backup", env={**sandbox, "FAKE_DUMP_BODY": ""})
    assert result.returncode != 0
    assert dumps(sandbox) == []


def test_adm_04_retention_deletes_only_old_dumps(sandbox: dict[str, str]) -> None:
    backups = Path(sandbox["MLAB_BACKUP_DIR"])
    backups.mkdir()
    old = backups / "db-20200101-000000.dump"
    recent = backups / "db-20991231-000000.dump"
    foreign = backups / "notes.txt"
    for path in (old, recent, foreign):
        path.write_text("x")
    long_ago = time.time() - 40 * 86400
    os.utime(old, (long_ago, long_ago))
    os.utime(foreign, (long_ago, long_ago))
    result = run("backup.sh", "backup", env={**sandbox, "MLAB_BACKUP_KEEP_DAYS": "14"})
    assert result.returncode == 0, result.stderr
    assert not old.exists()
    assert recent.exists()
    assert foreign.exists()  # boshqa fayllarga tegilmaydi
    assert len(dumps(sandbox)) == 2


def test_adm_04_invalid_retention_rejected(sandbox: dict[str, str]) -> None:
    for bad in ("0", "abc", "-1"):
        result = run("backup.sh", "backup", env={**sandbox, "MLAB_BACKUP_KEEP_DAYS": bad})
        assert result.returncode != 0
    assert dumps(sandbox) == []


def test_adm_04_restore_requires_explicit_confirmation(sandbox: dict[str, str]) -> None:
    dump = Path(sandbox["MLAB_BACKUP_DIR"]) / "db-test.dump"
    dump.parent.mkdir()
    dump.write_text("OLD-STATE")
    result = run("backup.sh", "restore", str(dump), env=sandbox)
    assert result.returncode != 0
    assert "--yes" in result.stderr
    assert not Path(sandbox["FAKE_RESTORE_STDIN"]).exists()


def test_adm_04_restore_backs_up_current_state_then_restores(sandbox: dict[str, str]) -> None:
    dump = Path(sandbox["MLAB_BACKUP_DIR"]) / "db-test.dump"
    dump.parent.mkdir()
    dump.write_text("OLD-STATE")
    result = run("backup.sh", "restore", str(dump), "--yes", env=sandbox)
    assert result.returncode == 0, result.stderr
    assert Path(sandbox["FAKE_RESTORE_STDIN"]).read_text() == "OLD-STATE"
    assert len(dumps(sandbox)) == 2  # tiklashdan oldingi holat ham saqlangan
    log = Path(sandbox["FAKE_LOG"]).read_text().splitlines()
    pre_backup = next(i for i, ln in enumerate(log) if "pg_dump" in ln)
    stop = next(i for i, ln in enumerate(log) if " stop caddy web" in ln)
    restore = next(i for i, ln in enumerate(log) if "pg_restore" in ln)
    assert pre_backup < stop < restore
    assert any(ln.startswith("curl") and "/readyz" in ln for ln in log)


def test_adm_04_restore_missing_file(sandbox: dict[str, str]) -> None:
    result = run("backup.sh", "restore", "/nonexistent.dump", "--yes", env=sandbox)
    assert result.returncode != 0


def test_adm_04_env_file_with_loose_permissions_rejected(sandbox: dict[str, str]) -> None:
    Path(sandbox["MLAB_ENV_FILE"]).chmod(0o644)
    result = run("backup.sh", "backup", env=sandbox)
    assert result.returncode != 0
    assert "chmod 600" in result.stderr


@pytest.mark.parametrize(
    "tag", ["main", "latest", "good-2026-11-23", "good-2026-11-23-1415-ABC1234", "$(id)", ""]
)
def test_nfr_08_deploy_rejects_non_good_tags(sandbox: dict[str, str], tag: str) -> None:
    result = run("deploy.sh", tag, env=sandbox)
    assert result.returncode != 0
    assert "good-" in result.stderr
    assert not Path(sandbox["FAKE_LOG"]).exists()  # docker umuman chaqirilmagan


def test_nfr_08_smoke_checks_health_and_readiness(sandbox: dict[str, str]) -> None:
    result = run("smoke.sh", env=sandbox)
    assert result.returncode == 0, result.stderr
    log = Path(sandbox["FAKE_LOG"]).read_text()
    assert "https://mlab.example.uz/healthz" in log
    assert "https://mlab.example.uz/readyz" in log
    assert "--resolve mlab.example.uz:443:127.0.0.1" in log


def test_nfr_08_smoke_fails_when_service_down(sandbox: dict[str, str], tmp_path: Path) -> None:
    (tmp_path / "bin" / "curl").write_text("#!/usr/bin/env bash\nexit 22\n")
    result = run("smoke.sh", env=sandbox)
    assert result.returncode != 0


# --- deploy workflow ---


WORKFLOW = yaml.safe_load((ROOT / ".github" / "workflows" / "deploy.yml").read_text())


def test_nfr_08_deploy_workflow_is_manual_with_approval() -> None:
    triggers = WORKFLOW[True] if True in WORKFLOW else WORKFLOW["on"]  # PyYAML: `on` -> True
    assert set(triggers) == {"workflow_dispatch"}
    assert triggers["workflow_dispatch"]["inputs"]["tag"]["required"] is True
    job = WORKFLOW["jobs"]["deploy"]
    assert job["environment"] == "production"
    assert WORKFLOW["permissions"] == {"contents": "read"}
    assert WORKFLOW["concurrency"]["cancel-in-progress"] is False


def test_nfr_08_deploy_workflow_has_no_inline_secrets_or_injection() -> None:
    text = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
    assert "secrets." not in text
    # `run:` ichiga kirish qiymati qo'yilmaydi (script injection): faqat env orqali.
    for step in WORKFLOW["jobs"]["deploy"]["steps"]:
        assert "${{" not in step["run"]
