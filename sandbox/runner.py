"""Sandbox runner (ADR-0007 4-band; AGR-03, AGR-05; I3-05).

Konteyner ichida ishlaydi: stdin'dan bitta JSON, stdout'ga bitta JSON. Faqat standart kutubxona.

Kirish:
  {"code": "<talaba kodi>", "params": {...}, "time_limit": 10,
   "tests": [{"step": "load", "kind": "visible" | "hidden",
              "source": "def test_x(ns, params): ..."}]}
Chiqish:
  {"status": "ok" | "code_error" | "bad_input",
   "error": "<talaba kodi xatosi: tur va qisqa xabar>" | null,
   "stdout": "<talaba chiqishi, qisqartirilgan>",
   "tests": [{"step", "kind", "name", "passed", "message", "ms"}]}

AGR-05: yashirin test uchun nom "yashirin test N" va xabar umumiy — test kodi, assert matni va
traceback chiqmaydi. Talabaning `print()` i alohida buferga yoziladi: u natija JSON'ini
soxtalashtira olmaydi (natija asl stdout fd'siga yoziladi).

Cheklov: talaba kodi runner bilan bir jarayonda. Ataylab ichki holatni o'zgartirishga urinish
(introspeksiya) konteyner bilan cheklanadi, lekin natija yaxlitligini to'liq kafolatlamaydi;
kod saqlanadi va o'qituvchi ko'radi (I3-19 xavfsizlik ko'rigida qayta baholanadi).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import signal
import sys
import time
import traceback
from types import FrameType
from typing import Any

MAX_INPUT = 2_000_000  # bayt: kod + testlar
MAX_STDOUT = 64_000  # belgi: talaba chiqishi
MAX_MESSAGE = 500  # belgi: ko'rinadigan test xabari
MAX_RESULT = 256_000  # bayt: butun natija (ADR-0007)
DEFAULT_TIME_LIMIT = (
    10  # s: talaba kodi va har test uchun alohida; umumiy chegara — launcher (60 s)
)


class _Timeout(BaseException):
    """BaseException: talabaning `except Exception` bloki uni yutib yubora olmaydi."""


def _alarm(_signum: int, _frame: FrameType | None) -> None:
    raise _Timeout


def _short(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".strip()
    return text[:MAX_MESSAGE]


def _student_error(exc: BaseException, filename: str) -> str:
    """Faqat talaba kodi qatorlari: runner ichki traceback'i ko'rsatilmaydi."""
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == filename]
    where = f" ({frames[-1].lineno}-qator)" if frames else ""
    return f"{_short(exc)}{where}"[:MAX_MESSAGE]


def _limited(seconds: int) -> contextlib.AbstractContextManager[None]:
    @contextlib.contextmanager
    def manager() -> Any:
        signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)

    return manager()


def _validate(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or not isinstance(data.get("code"), str):
        raise ValueError("code")
    tests = data.get("tests")
    if not isinstance(tests, list) or not all(
        isinstance(t, dict)
        and isinstance(t.get("step"), str)
        and t.get("kind") in ("visible", "hidden")
        and isinstance(t.get("source"), str)
        for t in tests
    ):
        raise ValueError("tests")
    params = data.get("params", {})
    limit = data.get("time_limit", DEFAULT_TIME_LIMIT)
    if not isinstance(params, dict) or type(limit) is not int or not 1 <= limit <= 60:
        raise ValueError("params/time_limit")
    return {
        "code": data["code"],
        "tests": tests,
        "params": params,
        "time_limit": limit,
    }


def run(data: dict[str, Any]) -> dict[str, Any]:
    captured = io.StringIO()
    ns: dict[str, Any] = {"__name__": "__main__", "__builtins__": __builtins__}
    result: dict[str, Any] = {"status": "ok", "error": None, "stdout": "", "tests": []}
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        try:
            compiled = compile(data["code"], "<talaba>", "exec")
            with _limited(data["time_limit"]):
                exec(compiled, ns)  # noqa: S102 — izolyatsiyalangan konteyner ichida (ADR-0007)
        except _Timeout:
            result.update(status="code_error", error=f"Vaqt tugadi ({data['time_limit']} s)")
        except BaseException as exc:
            result.update(status="code_error", error=_student_error(exc, "<talaba>"))
        hidden_n = 0
        for spec in data["tests"]:
            hidden = spec["kind"] == "hidden"
            module: dict[str, Any] = {"__name__": f"mlab_test_{spec['step']}"}
            try:
                exec(compile(spec["source"], f"<test:{spec['step']}>", "exec"), module)  # noqa: S102
            except BaseException:
                result["tests"].append(
                    {
                        "step": spec["step"],
                        "kind": spec["kind"],
                        "name": "test fayli",
                        "passed": False,
                        "message": "Test faylida xato (o'qituvchiga xabar bering)",
                        "ms": 0,
                    }
                )
                continue
            for name, func in module.items():
                if not (name.startswith("test_") and callable(func)):
                    continue
                if hidden:
                    hidden_n += 1
                started = time.monotonic()
                passed, message = True, ""
                try:
                    if result["status"] == "code_error":
                        raise RuntimeError("kod xato bilan tugagan")
                    with _limited(data["time_limit"]):
                        func(ns, data["params"])
                except _Timeout:
                    passed, message = False, f"Vaqt tugadi ({data['time_limit']} s)"
                except AssertionError as exc:
                    passed, message = False, (str(exc) or "Natija kutilganidek emas")[:MAX_MESSAGE]
                except BaseException as exc:
                    passed, message = False, _short(exc)
                if hidden:
                    name = f"yashirin test {hidden_n}"
                    message = "" if passed else "O'tmadi"
                result["tests"].append(
                    {
                        "step": spec["step"],
                        "kind": spec["kind"],
                        "name": name,
                        "passed": passed,
                        "message": message,
                        "ms": int((time.monotonic() - started) * 1000),
                    }
                )
    out = captured.getvalue()
    result["stdout"] = out[:MAX_STDOUT] + ("\n…(qisqartirildi)" if len(out) > MAX_STDOUT else "")
    return result


def _encode(result: dict[str, Any]) -> bytes:
    payload = json.dumps(result, ensure_ascii=False).encode()
    if len(payload) > MAX_RESULT:
        result["stdout"] = "…(chiqish juda katta — qisqartirildi)"
        payload = json.dumps(result, ensure_ascii=False).encode()
    return payload


def main() -> int:
    # Natija uchun asl stdout fd'si; talaba print() lari buferga ketadi.
    out = os.fdopen(os.dup(sys.stdout.fileno()), "wb")
    raw = sys.stdin.buffer.read(MAX_INPUT + 1)
    try:
        if len(raw) > MAX_INPUT:
            raise ValueError("size")
        data = _validate(json.loads(raw))
    except ValueError as exc:
        out.write(json.dumps({"status": "bad_input", "error": str(exc)}).encode())
        out.flush()
        return 2
    result = run(data)
    out.write(_encode(result))
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
