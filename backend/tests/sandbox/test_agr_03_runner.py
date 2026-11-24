"""AGR-03, AGR-05 (I3-05): sandbox runner — konteynersiz, alohida jarayonda (`sandbox/runner.py`).

Bu yerda faqat bizning fixture kodimiz bajariladi (talaba kodi emas); jarayon Django'dan alohida.
Konteyner cheklovlari (tarmoq, xotira, fork) — sandbox/tests/test_image_attacks.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

RUNNER = Path(__file__).resolve().parents[3] / "sandbox" / "runner.py"

VISIBLE = """
def test_total(ns, params):
    assert ns["total"] == params["n"] * 2, "total noto'g'ri"
"""
HIDDEN = """
def test_secret_check(ns, params):
    assert ns["total"] > 100, "MAXFIY_ASSERT_MATNI"
"""


def _run(payload: Any, raw: bytes | None = None) -> tuple[int, dict[str, Any]]:
    data = raw if raw is not None else json.dumps(payload).encode()
    proc = subprocess.run(
        [sys.executable, "-I", str(RUNNER)],
        input=data,
        capture_output=True,
        timeout=60,
        check=False,
    )
    return proc.returncode, json.loads(proc.stdout)


def _payload(code: str, **extra: Any) -> dict[str, Any]:
    return {
        "code": code,
        "params": {"n": 21},
        "tests": [
            {"step": "sum", "kind": "visible", "source": VISIBLE},
            {"step": "sum", "kind": "hidden", "source": HIDDEN},
        ],
        **extra,
    }


def test_agr_03_passing_code_and_visible_details() -> None:
    code, result = _run(_payload("total = 42\nprint('salom')"))
    assert code == 0
    assert result["status"] == "ok"
    assert result["stdout"] == "salom\n"
    visible, hidden = result["tests"]
    assert visible == {**visible, "name": "test_total", "passed": True, "kind": "visible"}
    assert hidden["passed"] is False


def test_agr_05_hidden_test_name_and_message_not_revealed() -> None:
    _, result = _run(_payload("total = 1"))
    visible, hidden = result["tests"]
    assert visible["message"] == "total noto'g'ri"
    assert hidden["name"] == "yashirin test 1"
    assert hidden["message"] == "O'tmadi"
    text = json.dumps(result)
    assert "MAXFIY_ASSERT_MATNI" not in text
    assert "test_secret_check" not in text


def test_agr_03_code_error_reports_only_student_line() -> None:
    _, result = _run(_payload("x = 1\ny = 1 / 0"))
    assert result["status"] == "code_error"
    assert result["error"] == "ZeroDivisionError: division by zero (2-qator)"
    assert "runner.py" not in json.dumps(result)
    assert all(not t["passed"] for t in result["tests"])


def test_agr_03_student_print_cannot_forge_result() -> None:
    forged = json.dumps({"status": "ok", "tests": [{"passed": True}]})
    _, result = _run(_payload(f"import sys\nprint({forged!r})\nsys.stdout.write('x')\ntotal = 1"))
    assert result["stdout"].startswith('{"status"')  # soxta JSON faqat talaba chiqishida qoldi
    assert [t["passed"] for t in result["tests"]] == [False, False]


def test_agr_03_infinite_loop_and_swallowed_timeout() -> None:
    code = "while True:\n    try:\n        pass\n    except Exception:\n        pass\n"
    _, result = _run(_payload(code, time_limit=1))
    assert result["status"] == "code_error"
    assert result["error"] == "Vaqt tugadi (1 s)"


def test_agr_03_sys_exit_is_student_error() -> None:
    _, result = _run(_payload("raise SystemExit(0)"))
    assert result["status"] == "code_error"
    assert result["error"].startswith("SystemExit")


def test_agr_03_stdout_truncated() -> None:
    _, result = _run(_payload("print('a' * 200_000)\ntotal = 42"))
    assert len(result["stdout"]) < 70_000
    assert result["stdout"].endswith("(qisqartirildi)")
    assert result["tests"][0]["passed"] is True


def test_agr_03_broken_test_file_is_generic() -> None:
    payload = _payload("total = 42")
    payload["tests"].append({"step": "x", "kind": "hidden", "source": "def broken(:"})
    _, result = _run(payload)
    assert result["tests"][-1]["message"].startswith("Test faylida xato")


def test_agr_03_bad_input_rejected() -> None:
    for raw in (b"not json", json.dumps({"code": 1}).encode(), b"x" * 2_000_001):
        code, result = _run(None, raw)
        assert code == 2
        assert result["status"] == "bad_input"
    code, result = _run(_payload("total = 42", time_limit=0))
    assert result["status"] == "bad_input"
