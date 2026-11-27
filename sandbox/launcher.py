"""sandbox-launcher (ADR-0007 2-band; AGR-03, I3-18a): Docker'ga kiradigan yagona xizmat.

Worker `POST /run` ga runner shartnomasidagi JSON yuboradi (`sandbox/runner.py`:
code, params, time_limit, tests). Launcher har so'rov uchun yangi konteyner ishga tushiradi —
image va cheklovlar shu faylda qotirilgan, so'rov ularni o'zgartira olmaydi.
Kod va testlar konteynerga stdin orqali, natija — stdout'dagi JSON.

Javoblar (worker `apps/grading/sandbox.py: LauncherSandbox`):
- 200 + runner JSON — konteyner tugadi (talaba kodi xatosi ham shu yerda: `code_error`);
- 200 + `code_error` — 60 s, xotira chegarasi yoki juda katta chiqish (talaba kodi sababchi,
  qayta urinilmaydi);
- 503 — band (2 konteyner ishlayapti) yoki Docker ishlamayapti: worker keyinroq qayta urinadi;
- 400/404/405/411/413 — noto'g'ri so'rov.

Faqat stdlib. Ishga tushirish: `SANDBOX_IMAGE=mlab-sandbox:<versiya> python launcher.py`
(port 8080, faqat ichki tarmoq).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

MAX_INPUT = 2_000_000  # bayt: runner.MAX_INPUT bilan bir xil
MAX_OUTPUT = 512_000  # bayt: runner natijasi 256 KB gacha (ADR-0007) + zaxira
WALL_TIMEOUT = 60  # s: konteyner umri (ADR-0007)
MAX_PARALLEL = 2  # ADR-0007: bir vaqtda 2 sandbox (RAM byudjeti 2 x 512 MB)
DOCKER = "docker"
PORT = 8080

# ADR-0007 2-band — `sandbox/tests/test_image_attacks.py` dagi LIMITS bilan aynan bir xil
# (test tekshiradi). /tmp — konteyner ichidagi tmpfs, xostniki emas.
LIMITS = (
    "--network", "none",
    "--read-only",
    "--tmpfs", "/tmp:size=64m,noexec",  # noqa: S108
    "--user", "10003:10003",
    "--memory", "512m", "--memory-swap", "512m",
    "--cpus", "1",
    "--pids-limit", "64",
    "--cap-drop", "ALL",
    "--security-opt", "no-new-privileges",
    "--ulimit", "nofile=64",
)  # fmt: skip

logger = logging.getLogger("sandbox.launcher")


class Busy(Exception):
    """Bo'sh joy yo'q — 503."""


class DockerUnavailable(Exception):
    """Docker CLI yoki daemon ishlamadi — 503 (infratuzilma xatosi)."""


def _code_error(message: str) -> dict[str, Any]:
    # Worker `_valid_result`: status ok|code_error va tests ro'yxati — bo'sh ro'yxat 0 ball beradi.
    return {"status": "code_error", "error": message, "stdout": "", "tests": []}


class Launcher:
    def __init__(
        self, image: str, docker: str = DOCKER, wall_timeout: float = WALL_TIMEOUT
    ) -> None:
        if not image or any(c.isspace() for c in image) or image.startswith("-"):
            raise ValueError("SANDBOX_IMAGE noto'g'ri yoki berilmagan")
        self.image = image
        self.docker = docker
        self.wall_timeout = wall_timeout
        self.slots = threading.BoundedSemaphore(MAX_PARALLEL)

    def command(self, name: str) -> list[str]:
        return [
            self.docker, "run", "--rm", "-i", "--name", name, "--label", "mlab.sandbox=1",
            *LIMITS, self.image,
        ]  # fmt: skip

    def run(self, payload: bytes) -> dict[str, Any]:
        if not self.slots.acquire(blocking=False):
            raise Busy
        try:
            return self._run(payload)
        finally:
            self.slots.release()

    def _run(self, payload: bytes) -> dict[str, Any]:
        name = f"mlab-sbx-{uuid.uuid4().hex}"
        try:
            proc = subprocess.Popen(  # noqa: S603 — argumentlar qotirilgan, shell yo'q
                self.command(name),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise DockerUnavailable(type(exc).__name__) from exc
        chunks: list[bytes] = []
        overflow = threading.Event()

        def read() -> None:
            assert proc.stdout is not None  # noqa: S101
            size = 0
            while chunk := proc.stdout.read(65536):
                size += len(chunk)
                if size > MAX_OUTPUT:
                    overflow.set()
                    proc.kill()
                    return
                chunks.append(chunk)

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        timed_out = False
        try:
            try:
                assert proc.stdin is not None  # noqa: S101
                proc.stdin.write(payload)
                proc.stdin.close()
            except OSError:
                pass  # konteyner stdin'ni o'qimay tugadi — natija quyida
            try:
                proc.wait(timeout=self.wall_timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.kill()
                proc.wait()
            reader.join(timeout=5)
            if proc.stdout is not None:
                proc.stdout.close()
        finally:
            # CLI o'ldirilsa ham konteyner ishlashda davom etishi mumkin —
            # har holatda majburan o'chiramiz.
            self._remove(name)
        if timed_out:
            return _code_error(f"Vaqt chegarasi ({int(self.wall_timeout)} s) tugadi")
        if overflow.is_set():
            return _code_error("Chiqish juda katta")
        if proc.returncode == 125:  # `docker run` o'zi ishlamadi (daemon, image)
            raise DockerUnavailable("docker run: 125")
        try:
            data = json.loads(b"".join(chunks))
        except ValueError:
            data = None
        if isinstance(data, dict):
            return data
        if proc.returncode == 137:
            return _code_error("Sandbox to'xtatildi (xotira chegarasi — 512 MB)")
        return _code_error("Sandbox natija bermadi")

    def _remove(self, name: str) -> None:
        try:
            subprocess.run(  # noqa: S603
                [self.docker, "rm", "-f", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            logger.warning(json.dumps({"event": "launcher.remove_failed", "container": name}))


def make_handler(launcher: Launcher) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "mlab-launcher"
        sys_version = ""

        def _send(self, status: HTTPStatus, body: dict[str, Any]) -> None:
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            if status == HTTPStatus.SERVICE_UNAVAILABLE:
                self.send_header("Retry-After", "5")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self._send(HTTPStatus.OK, {"status": "ok"})
            elif self.path == "/run":
                self._send(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method"})
            else:
                self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:
            if self.path != "/run":
                self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            length = self.headers.get("Content-Length")
            if length is None or not length.isdigit():
                self._send(HTTPStatus.LENGTH_REQUIRED, {"error": "length"})
                return
            if int(length) > MAX_INPUT:
                self.close_connection = True
                self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "size"})
                return
            raw = self.rfile.read(int(length))
            try:
                data = json.loads(raw)
            except ValueError:
                data = None
            if not isinstance(data, dict) or not isinstance(data.get("code"), str):
                self._send(HTTPStatus.BAD_REQUEST, {"error": "bad_json"})
                return
            started = time.monotonic()
            outcome = "ok"
            try:
                result = launcher.run(raw)
                outcome = str(result.get("status"))[:32]
                self._send(HTTPStatus.OK, result)
            except Busy:
                outcome = "busy"
                self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "busy"})
            except DockerUnavailable as exc:
                outcome = "docker_unavailable"
                logger.error(
                    json.dumps({"event": "launcher.docker_unavailable", "reason": str(exc)})
                )
                self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "docker_unavailable"})
            finally:
                # Kod va testlar logga yozilmaydi (yashirin testlar — AGR-05).
                logger.info(
                    json.dumps(
                        {
                            "event": "launcher.run",
                            "outcome": outcome,
                            "duration_ms": int((time.monotonic() - started) * 1000),
                            "bytes": len(raw),
                        }
                    )
                )

        def log_message(self, format: str, *args: Any) -> None:
            return  # standart access log o'rniga yuqoridagi strukturali log

    return Handler


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    try:
        launcher = Launcher(os.environ.get("SANDBOX_IMAGE", ""))
    except ValueError as exc:
        logger.error(json.dumps({"event": "launcher.config_error", "reason": str(exc)}))
        return 2
    server = ThreadingHTTPServer(("0.0.0.0", PORT), make_handler(launcher))  # noqa: S104 — faqat ichki tarmoq
    logger.info(json.dumps({"event": "launcher.start", "port": PORT, "image": launcher.image}))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
