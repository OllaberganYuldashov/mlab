"""scripts/sync_status.py va docs/status/build.py: dashboard holati GitHub Issues'dan.

gh javobi soxta — tarmoqqa chiqilmaydi.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path) -> ModuleType:
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync = _load("sync_status", ROOT / "scripts" / "sync_status.py")
build = _load("status_build", ROOT / "docs" / "status" / "build.py")


def _issue(
    number: int,
    state: str = "OPEN",
    labels: tuple[str, ...] = (),
    prs: tuple[tuple[int, bool], ...] = (),
) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Issue {number}",
        "state": state,
        "labels": {"nodes": [{"name": n} for n in labels]},
        "closedByPullRequestsReferences": {
            "nodes": [{"number": n, "merged": merged} for n, merged in prs]
        },
    }


def _gh(*issues: dict[str, Any], ready: tuple[dict[str, Any], ...] = ()) -> dict[str, Any]:
    repo: dict[str, Any] = {f"i{i['number']}": i for i in issues}
    repo["ready"] = {"nodes": list(ready)}
    return {"data": {"repository": repo}}


def test_closed_issue_is_done_with_only_merged_prs() -> None:
    data = _gh(_issue(164, "CLOSED", prs=((196, True), (190, False), (195, True))))
    live = sync.parse(data, "2026-11-28")
    assert live["issues"]["#164"] == {"status": "done", "pr": "#195, #196"}


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (("status:in-progress",), "in_progress"),
        (("status:review", "needs:owner"), "in_progress"),
        (("status:blocked", "status:ready"), "blocked"),
        (("status:ready", "size:S"), "ready"),
    ],
)
def test_open_issue_status_from_labels(labels: tuple[str, ...], expected: str) -> None:
    live = sync.parse(_gh(_issue(165, labels=labels)), "2026-11-28")
    assert live["issues"]["#165"]["status"] == expected


def test_open_issue_without_status_label_keeps_plan_value() -> None:
    live = sync.parse(_gh(_issue(166, labels=("type:chore",))), "2026-11-28")
    assert "#166" not in live["issues"]


def test_plan_issue_numbers_reads_plan() -> None:
    numbers = sync.plan_issue_numbers()
    assert numbers == sorted(set(numbers))
    assert 165 in numbers


def test_missing_issue_is_ignored() -> None:
    data = _gh(_issue(1))
    data["data"]["repository"]["i999"] = None
    assert "#999" not in sync.parse(data, "2026-11-28")["issues"]


def test_next_task_is_smallest_ready_issue_not_taken_by_day_run() -> None:
    ready = (
        _issue(170, labels=("status:ready",)),
        _issue(165, labels=("status:ready", "run:day")),
        _issue(167, labels=("status:ready",)),
    )
    live = sync.parse(_gh(ready=ready), "2026-11-28")
    assert live["next_task"] == "#167 Issue 167"
    assert live["as_of"] == "2026-11-28"


def test_next_task_when_nothing_ready() -> None:
    assert "yo'q" in sync.parse(_gh(), "2026-11-28")["next_task"]


def test_query_has_alias_per_issue() -> None:
    q = sync.build_query("o", "r", [5, 165])
    assert "i5: issue(number: 5)" in q
    assert "i165: issue(number: 165)" in q
    assert 'labels: ["status:ready"]' in q


def test_build_applies_live_over_plan() -> None:
    tasks = [
        {"issue": "#165", "status": "ready", "pr": "", "key": "I3-17"},
        {"issue": "", "status": "planned", "pr": "", "key": "E-I4-1"},
    ]
    live = {
        "as_of": "2026-11-29",
        "next_task": "#167 X",
        "issues": {"#165": {"status": "done", "pr": "#201"}},
    }
    rows, meta = build.apply_live(tasks, {"as_of": "2026-11-01", "next_task": ""}, live)
    assert rows[0] == {"issue": "#165", "status": "done", "pr": "#201", "key": "I3-17"}
    assert rows[1]["status"] == "planned"
    assert meta == {"as_of": "2026-11-29", "next_task": "#167 X"}


def test_manual_next_task_is_kept() -> None:
    _, meta = build.apply_live(
        [], {"as_of": "2026-11-01", "next_task": "qo'lda"}, {"next_task": "#1"}
    )
    assert meta == {"as_of": "2026-11-01", "next_task": "qo'lda"}


def test_main_uses_gh_and_writes_live(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[str] = []
    monkeypatch.setattr(sync, "LIVE", tmp_path / "live.json")
    monkeypatch.setattr(sync, "repo_slug", lambda: ("o", "r"))
    monkeypatch.setattr(sync, "plan_issue_numbers", lambda: [5])

    def fake_gh(query: str) -> dict[str, Any]:
        calls.append(query)
        return _gh(_issue(5, "CLOSED"))

    monkeypatch.setattr(sync, "gh_graphql", fake_gh)

    class Done:
        returncode = 0

    monkeypatch.setattr(sync.subprocess, "run", lambda *a, **k: Done())
    assert sync.main([]) == 0
    assert '"#5"' in (tmp_path / "live.json").read_text(encoding="utf-8")
    assert len(calls) == 1
