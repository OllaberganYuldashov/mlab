"""Sandbox chaqiruvi interfeysi (ADR-0007; AGR-03, I3-06).

Worker sandbox'ni faqat shu interfeys orqali chaqiradi:
- `LauncherSandbox` — prod: `sandbox-launcher` xizmatiga `POST {SANDBOX_LAUNCHER_URL}/run`
  (Docker soketi faqat launcher'da; worker'da yo'q). So'rov va javob — `sandbox/runner.py`
  shartnomasi.
- `FakeSandbox` — testlar: talaba kodini **bajarmaydi** (AGR-03), oldindan berilgan javobni
  qaytaradi.

`SandboxUnavailable` — faqat infratuzilma xatosi (launcher javob bermadi, 5xx, buzuq JSON):
qayta urinish mumkin. Talaba kodi xatosi bu emas — u runner javobida `code_error`.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections import deque
from typing import Any, Protocol

from django.conf import settings

MAX_RESPONSE = 512_000  # bayt: runner natijasi 256 KB gacha (ADR-0007) + zaxira
LAUNCHER_TIMEOUT = 75  # s: konteyner 60 s da o'ldiriladi + ishga tushish


class SandboxUnavailable(RuntimeError):
    """Sandbox javob bermadi — infratuzilma xatosi (qayta urinish mumkin)."""


class Sandbox(Protocol):
    def run(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class LauncherSandbox:
    def __init__(self, url: str) -> None:
        if not url.startswith(("http://", "https://")):
            raise SandboxUnavailable("SANDBOX_LAUNCHER_URL sozlanmagan")
        self.url = url.rstrip("/") + "/run"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(  # noqa: S310 — sxema yuqorida tekshirilgan
            self.url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=LAUNCHER_TIMEOUT) as response:  # noqa: S310
                body = response.read(MAX_RESPONSE + 1)
        except urllib.error.HTTPError as exc:
            exc.close()  # javob tanasi soketni ushlab turmasin
            raise SandboxUnavailable(f"launcher: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise SandboxUnavailable(f"launcher: {type(exc).__name__}") from exc
        if len(body) > MAX_RESPONSE:
            raise SandboxUnavailable("launcher: javob juda katta")
        try:
            data = json.loads(body)
        except ValueError as exc:
            raise SandboxUnavailable("launcher: buzuq JSON") from exc
        if not isinstance(data, dict):
            raise SandboxUnavailable("launcher: javob obyekt emas")
        return data


class FakeSandbox:
    """Testlar uchun: `responses` navbatidan oladi (dict — javob, Exception — ko'tariladi).

    Navbat bo'sh bo'lsa — barcha testlar o'tgan javob. Kod hech qachon bajarilmaydi.
    """

    def __init__(self) -> None:
        self.responses: deque[dict[str, Any] | Exception] = deque()
        self.calls: list[dict[str, Any]] = []

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if self.responses:
            item = self.responses.popleft()
            if isinstance(item, Exception):
                raise item
            return item
        return {
            "status": "ok",
            "error": None,
            "stdout": "",
            "tests": [
                {
                    "step": t["step"],
                    "kind": t["kind"],
                    "name": "fake",
                    "passed": True,
                    "message": "",
                    "ms": 0,
                }
                for t in payload["tests"]
            ],
        }


fake = FakeSandbox()


def get_sandbox() -> Sandbox:
    if settings.SANDBOX_BACKEND == "fake":
        return fake
    return LauncherSandbox(str(settings.SANDBOX_LAUNCHER_URL))
