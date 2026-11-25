"""Kontent yechimlari tekshiruvi (I3-15; AGR-07): har variantda yechim barcha testlardan o'tadimi.

`content/labs/<A##>-<slug>/solutions/<daraja>.py` (yoki umumiy `solution.py`) — `{parametr}` li
shablon (shart kabi to'ldiriladi). Har variant uchun yechim `sandbox/runner.py` orqali **alohida
jarayonda** bajariladi (Django jarayonida emas — AGR-03): lokal Python (sandbox paketlari bilan)
yoki sandbox image.
Qo'shimcha himoya: bo'sh kod bilan hech bir yashirin test o'tmasligi kerak (test "bo'sh" emasligi).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apps.grading.content import LabData, load_labs
from apps.grading.models import TestKind
from apps.grading.views import render_statement

REPO = Path(__file__).resolve().parents[3]
RUNNER = REPO / "sandbox" / "runner.py"
TIME_LIMIT = 30  # s: yechimlar sklearn o'qitadi; sandbox chegarasi (10 s) — talaba kodi uchun

Runner = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class Failure:
    lab: str
    variant: str
    reason: str

    def __str__(self) -> str:
        return f"{self.lab} {self.variant}: {self.reason}"


def local_runner(python: str, datasets: Path) -> Runner:
    """Berilgan Python (sandbox requirements bilan) va `sandbox/mlab.py` bilan runner."""

    def run(payload: dict[str, Any]) -> dict[str, Any]:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(RUNNER.parent),
            "PYTHONSAFEPATH": "1",
            "MLAB_DATASETS": str(datasets),
            "MPLBACKEND": "Agg",
        }
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(  # noqa: S603 — buyruq ro'yxati, shell yo'q
                [python, str(RUNNER)],
                input=json.dumps(payload).encode(),
                capture_output=True,
                timeout=TIME_LIMIT * 20,
                check=False,
                cwd=tmp,
                env={**env, "HOME": tmp, "MPLCONFIGDIR": tmp},
            )
        return _parse(proc)

    return run


def docker_runner(image: str) -> Runner:
    """Sandbox image bilan (CI, I3-18): tarmoqsiz, image'dagi datasetlar."""

    def run(payload: dict[str, Any]) -> dict[str, Any]:
        proc = subprocess.run(  # noqa: S603
            ["docker", "run", "--rm", "-i", "--network", "none", image],  # noqa: S607
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=TIME_LIMIT * 20,
            check=False,
        )
        return _parse(proc)

    return run


def _parse(proc: subprocess.CompletedProcess[bytes]) -> dict[str, Any]:
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return {"status": "runner_failed", "error": proc.stderr.decode(errors="replace")[-500:]}
    return data if isinstance(data, dict) else {"status": "runner_failed", "error": "javob"}


def _template(lab_dir: Path, level: str) -> str | None:
    for name in (f"{level}.py", "solution.py"):
        path = lab_dir / "solutions" / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return None


def _tests(lab: LabData, hidden_only: bool = False) -> list[dict[str, str]]:
    """Muallif vositasi: yashirin testlar ham `visible` deb yuboriladi — nom va assert ko'rinsin."""
    visible = str(TestKind.VISIBLE)
    out = []
    for step in lab.steps:
        if step.visible is not None and not hidden_only:
            out.append({"step": step.key, "kind": visible, "source": step.visible})
        out.append({"step": step.key, "kind": visible, "source": step.hidden})
    return out


def _failed(result: dict[str, Any]) -> list[str]:
    return [
        f"{t.get('step')}/{t.get('name')}: {t.get('message')}"
        for t in result.get("tests", [])
        if not t.get("passed")
    ]


def check_labs(root: Path, run: Runner, only: str | None = None) -> tuple[int, list[Failure]]:
    """(tekshirilgan variantlar soni, xatolar)."""
    root = root.resolve()
    failures: list[Failure] = []
    checked = 0
    for lab in load_labs(root):
        if only and lab.code != only:
            continue
        lab_dir = next((root / "labs").glob(f"{lab.code}-*"))
        tests = _tests(lab)
        for i, (level, number, params) in enumerate(lab.variants):
            name = f"{level}-{number}"
            template = _template(lab_dir, level)
            if template is None:
                failures.append(Failure(lab.code, name, "yechim fayli yo'q (solutions/)"))
                continue
            checked += 1
            payload = {
                "code": render_statement(template, params),
                "params": params,
                "time_limit": TIME_LIMIT,
                "tests": tests,
            }
            result = run(payload)
            if result.get("status") != "ok":
                failures.append(
                    Failure(lab.code, name, f"{result.get('status')}: {result.get('error')}")
                )
            elif bad := _failed(result):
                failures.append(Failure(lab.code, name, "; ".join(bad)))
            elif not result.get("tests"):
                failures.append(Failure(lab.code, name, "hech qanday test ishlamadi"))
            if i == 0:
                empty = run({**payload, "code": "", "tests": _tests(lab, hidden_only=True)})
                leaked = [t for t in empty.get("tests", []) if t.get("passed")]
                if leaked:
                    failures.append(
                        Failure(
                            lab.code, name, f"bo'sh kod bilan {len(leaked)} ta yashirin test o'tdi"
                        )
                    )
    return checked, failures
