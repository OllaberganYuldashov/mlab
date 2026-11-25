"""AGR-07 (I3-15): kontent yechimlari tekshiruvi — har variantda yechim barcha testlardan o'tadi.

Yechim `sandbox/runner.py` orqali alohida jarayonda bajariladi (Django jarayonida emas, AGR-03).
Bu testda faqat standart kutubxona bilan topshiriq (CI backend muhitida pandas yo'q); haqiqiy
A01-A05 yechimlari sandbox paketlari bilan: `manage.py check_lab_solutions ../content --python ...`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from apps.grading.solutions import Failure, check_labs, local_runner

ASSIGNMENT = """code: A01
title: Yig'indi
topic: M01
statement: |
  `total` ga {n} * 2 ni yozing.
steps:
  - key: total
    title: Yig'indi
    points: 100
"""


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    lab = "labs/A01-yigindi"
    _write(tmp_path, f"{lab}/assignment.yaml", ASSIGNMENT)
    for level in ("basic", "medium", "advanced"):
        for n in range(1, 6):
            _write(tmp_path, f"{lab}/variants/{level}-{n}.yaml", f"params:\n  n: {n * 10}\n")
    _write(
        tmp_path,
        f"{lab}/tests/visible/total.py",
        "def test_bor(ns, params):\n    assert 'total' in ns, 'total yo`q'\n",
    )
    _write(
        tmp_path,
        f"{lab}/tests/hidden/total.py",
        "def test_qiymat(ns, params):\n    assert ns['total'] == params['n'] * 2\n",
    )
    _write(tmp_path, f"{lab}/solutions/solution.py", "total = {n} * 2\n")
    (tmp_path / "datasets").mkdir()
    return tmp_path


def _run(root: Path) -> tuple[int, list[Failure]]:
    return check_labs(root, local_runner(sys.executable, root / "datasets"))


def test_agr_07_good_solution_passes_every_variant(root: Path) -> None:
    assert _run(root) == (15, [])


def test_agr_07_wrong_solution_is_reported_per_variant(root: Path) -> None:
    _write(root, "labs/A01-yigindi/solutions/solution.py", "total = {n} * 3\n")
    checked, failures = _run(root)
    assert checked == 15
    assert len(failures) == 15
    assert "total/test_qiymat" in str(failures[0])


def test_agr_07_level_specific_solution_and_missing_file(root: Path) -> None:
    _write(root, "labs/A01-yigindi/solutions/advanced.py", "total = 0\n")  # daraja fayli ustun
    (root / "labs/A01-yigindi/solutions/solution.py").unlink()
    _write(root, "labs/A01-yigindi/solutions/basic.py", "total = {n} * 2\n")
    checked, failures = _run(root)
    reasons = {(f.variant.split("-")[0], f.reason.split(":")[0]) for f in failures}
    assert ("medium", "yechim fayli yo'q (solutions/)") in reasons
    assert any(v == "advanced" for v, _ in reasons)
    assert not any(f.variant.startswith("basic") for f in failures)
    assert checked == 10


def test_agr_07_vacuous_hidden_test_is_caught(root: Path) -> None:
    _write(
        root,
        "labs/A01-yigindi/tests/hidden/total.py",
        "def test_har_doim(ns, params):\n    assert True\n",
    )
    _, failures = _run(root)
    assert [f.reason for f in failures] == ["bo'sh kod bilan 1 ta yashirin test o'tdi"]


def test_agr_07_runner_crash_is_a_failure(root: Path, tmp_path: Path) -> None:
    broken = tmp_path / "python-broken"
    broken.write_text("#!/bin/sh\necho xato >&2\nexit 3\n")
    broken.chmod(0o755)
    checked, failures = check_labs(root, local_runner(str(broken), root / "datasets"))
    assert checked == 15
    assert failures[0].reason.startswith("runner_failed")


def test_agr_07_command_ok_and_error(root: Path) -> None:
    from io import StringIO

    out = StringIO()
    call_command("check_lab_solutions", str(root), "--python", sys.executable, stdout=out)
    assert "OK: 15 ta variant" in out.getvalue()
    call_command(
        "check_lab_solutions",
        str(root),
        "--python",
        sys.executable,
        "--lab",
        "A99",
        stdout=StringIO(),
    )
    _write(root, "labs/A01-yigindi/solutions/solution.py", "total = -1\n")
    with pytest.raises(CommandError, match="15 ta xato"):
        call_command(
            "check_lab_solutions",
            str(root),
            "--python",
            sys.executable,
            stdout=StringIO(),
            stderr=StringIO(),
        )
