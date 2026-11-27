"""AGR-03 (I3-18a, #202): `sandbox/launcher.py` — soxta `docker` CLI bilan.

Bulutda Docker daemon yo'q.

Haqiqiy Docker bilan cheklovlar — `sandbox/tests/test_image_attacks.py`;
launcher aynan o'sha parametrlarni ishlatadi.
"""

from __future__ import annotations

import http.client
import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SANDBOX = Path(__file__).resolve().parents[3] / "sandbox"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher_mod = _load("mlab_sandbox_launcher", SANDBOX / "launcher.py")

FAKE_DOCKER = """#!{python}
import json, os, sys, time
log = os.environ["FAKE_LOG"]
mode = open(os.environ["FAKE_MODE"]).read().strip()
args = sys.argv[1:]
with open(log, "a") as f:
    f.write(json.dumps(args) + "\\n")
if args[0] == "rm":
    sys.exit(0)
data = sys.stdin.buffer.read()
with open(log + ".stdin", "wb") as f:
    f.write(data)
if mode == "ok":
    sys.stdout.write(json.dumps({{"status": "ok", "tests": [], "echo": len(data)}}))
elif mode == "sleep":
    time.sleep(30)
elif mode == "flood":
    while True:
        sys.stdout.write("x" * 65536)
elif mode == "daemon":
    sys.exit(125)
elif mode == "oom":
    sys.exit(137)
elif mode == "garbage":
    sys.stdout.write("not json")
"""


class Fake:
    def __init__(self, tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.bin = tmp / "docker"
        self.bin.write_text(FAKE_DOCKER.format(python=sys.executable))
        self.bin.chmod(0o755)
        self.log = tmp / "calls.jsonl"
        self.mode_file = tmp / "mode"
        self.mode("ok")
        monkeypatch.setenv("FAKE_LOG", str(self.log))
        monkeypatch.setenv("FAKE_MODE", str(self.mode_file))

    def mode(self, value: str) -> None:
        self.mode_file.write_text(value)

    def calls(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def stdin(self) -> bytes:
        return Path(str(self.log) + ".stdin").read_bytes()


@pytest.fixture
def fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Fake:
    return Fake(tmp_path, monkeypatch)


@pytest.fixture
def launcher(fake: Fake) -> Any:
    return launcher_mod.Launcher("mlab-sandbox:test", docker=str(fake.bin), wall_timeout=2)


PAYLOAD = json.dumps({"code": "x = 1", "params": {}, "tests": []}).encode()


def test_agr_03_run_uses_fixed_limits_and_stdin(launcher: Any, fake: Fake) -> None:
    result = launcher.run(PAYLOAD)

    assert result == {"status": "ok", "tests": [], "echo": len(PAYLOAD)}
    run, rm = fake.calls()
    assert run[:3] == ["run", "--rm", "-i"]
    name = run[run.index("--name") + 1]
    assert name.startswith("mlab-sbx-")
    assert run[-1] == "mlab-sandbox:test"
    assert tuple(run[run.index("mlab.sandbox=1") + 1 : -1]) == launcher_mod.LIMITS
    assert fake.stdin() == PAYLOAD
    assert rm == ["rm", "-f", name]  # har holatda o'chiriladi


def test_agr_03_limits_match_adr_attack_tests() -> None:
    attacks = _load("mlab_sandbox_attacks", SANDBOX / "tests" / "test_image_attacks.py")
    assert list(launcher_mod.LIMITS) == attacks.LIMITS


def test_agr_03_payload_cannot_change_container_settings(launcher: Any, fake: Fake) -> None:
    evil = json.dumps(
        {"code": "x", "image": "alpine", "args": ["--privileged"], "tests": []}
    ).encode()
    launcher.run(evil)

    run = fake.calls()[0]
    assert "--privileged" not in run
    assert "alpine" not in run
    assert run[-1] == "mlab-sandbox:test"


def test_agr_03_timeout_kills_and_removes_container(launcher: Any, fake: Fake) -> None:
    fake.mode("sleep")
    result = launcher.run(PAYLOAD)

    assert result["status"] == "code_error"
    assert "Vaqt chegarasi" in result["error"]
    assert result["tests"] == []
    assert fake.calls()[-1][:2] == ["rm", "-f"]


def test_agr_03_output_flood_is_cut(launcher: Any, fake: Fake) -> None:
    fake.mode("flood")
    result = launcher.run(PAYLOAD)

    assert result == launcher_mod._code_error("Chiqish juda katta")
    assert fake.calls()[-1][:2] == ["rm", "-f"]


@pytest.mark.parametrize(
    ("mode", "message"),
    [("oom", "xotira chegarasi"), ("garbage", "natija bermadi")],
)
def test_agr_03_killed_or_garbage_is_code_error(
    launcher: Any, fake: Fake, mode: str, message: str
) -> None:
    fake.mode(mode)
    result = launcher.run(PAYLOAD)

    assert result["status"] == "code_error"
    assert message in result["error"]


def test_agr_03_docker_failure_is_unavailable(launcher: Any, fake: Fake) -> None:
    fake.mode("daemon")
    with pytest.raises(launcher_mod.DockerUnavailable):
        launcher.run(PAYLOAD)


def test_agr_03_missing_docker_binary_is_unavailable(tmp_path: Path) -> None:
    launcher = launcher_mod.Launcher("mlab-sandbox:test", docker=str(tmp_path / "yoq"))
    with pytest.raises(launcher_mod.DockerUnavailable):
        launcher.run(PAYLOAD)


def test_agr_03_at_most_two_parallel(launcher: Any) -> None:
    assert launcher.slots.acquire(blocking=False)
    assert launcher.slots.acquire(blocking=False)
    try:
        with pytest.raises(launcher_mod.Busy):
            launcher.run(PAYLOAD)
    finally:
        launcher.slots.release()
        launcher.slots.release()


@pytest.mark.parametrize("image", ["", "-v /:/host", "a b", "mlab\tsandbox"])
def test_agr_03_bad_image_fails_fast(image: str) -> None:
    with pytest.raises(ValueError, match="SANDBOX_IMAGE"):
        launcher_mod.Launcher(image)


# --- HTTP ---


@pytest.fixture
def server(launcher: Any) -> Iterator[str]:
    from http.server import ThreadingHTTPServer

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), launcher_mod.make_handler(launcher))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def _request(
    url: str, method: str = "GET", body: bytes | None = None
) -> tuple[int, dict[str, Any], dict[str, str]]:
    req = urllib.request.Request(url, data=body, method=method)  # noqa: S310 — lokal test serveri
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read()), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read()), dict(exc.headers)


def test_agr_03_http_run_returns_runner_json(server: str) -> None:
    status, body, _ = _request(server + "/run", "POST", PAYLOAD)
    assert status == 200
    assert body["status"] == "ok"


def test_agr_03_http_healthz(server: str) -> None:
    assert _request(server + "/healthz")[:2] == (200, {"status": "ok"})


@pytest.mark.parametrize(
    ("method", "path", "body", "expected"),
    [
        ("GET", "/run", None, 405),
        ("GET", "/containers/json", None, 404),
        ("POST", "/containers/create", b"{}", 404),
        ("POST", "/run", b"not json", 400),
        ("POST", "/run", b"[]", 400),
        ("POST", "/run", b'{"code": 1}', 400),
    ],
)
def test_agr_03_http_rejects_bad_requests(
    server: str, fake: Fake, method: str, path: str, body: bytes | None, expected: int
) -> None:
    assert _request(server + path, method, body)[0] == expected
    assert fake.calls() == []  # konteyner ishga tushmadi


def test_agr_03_http_too_large_is_413(server: str, fake: Fake) -> None:
    # Tana yuborilmaydi: server sarlavhaning o'zidan rad etadi (2 MB o'qimaydi).
    host, port = server.removeprefix("http://").split(":")
    conn = http.client.HTTPConnection(host, int(port), timeout=10)
    try:
        conn.putrequest("POST", "/run")
        conn.putheader("Content-Length", str(launcher_mod.MAX_INPUT + 1))
        conn.endheaders()
        resp = conn.getresponse()
        assert (resp.status, json.loads(resp.read())) == (413, {"error": "size"})
    finally:
        conn.close()
    assert fake.calls() == []


def test_agr_03_http_busy_and_docker_down_are_503(server: str, launcher: Any, fake: Fake) -> None:
    fake.mode("daemon")
    status, body, headers = _request(server + "/run", "POST", PAYLOAD)
    assert (status, body["error"]) == (503, "docker_unavailable")
    assert headers["Retry-After"] == "5"

    fake.mode("ok")
    launcher.slots.acquire()
    launcher.slots.acquire()
    try:
        status, body, _ = _request(server + "/run", "POST", PAYLOAD)
    finally:
        launcher.slots.release()
        launcher.slots.release()
    assert (status, body["error"]) == (503, "busy")


def test_agr_03_logs_never_contain_code(server: str, caplog: pytest.LogCaptureFixture) -> None:
    secret_test = "def test_hidden(ns, params): assert ns['maxfiy_qiymat'] == 42"
    body = json.dumps({"code": "x", "tests": [{"source": secret_test}]}).encode()
    with caplog.at_level("INFO", logger="sandbox.launcher"):
        _request(server + "/run", "POST", body)
    assert caplog.records
    assert all("maxfiy_qiymat" not in r.getMessage() for r in caplog.records)


def test_agr_03_main_fails_fast_without_image(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SANDBOX_IMAGE", raising=False)
    assert launcher_mod.main() == 2
