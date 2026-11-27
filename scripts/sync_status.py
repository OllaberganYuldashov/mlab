"""Dashboard holatini GitHub Issues'dan oladi va `docs/status/build.py` ni chaqiradi.

plan.py — faqat reja (iteratsiya, hajm, natija). Holat va PR qo'lda yozilmaydi: shu skript har
issue uchun `gh api graphql` bilan holatini (yopiq → done; status:in-progress / status:review → in_progress;
status:blocked → blocked; status:ready → ready) va uni yopgan merge bo'lgan PR'larni oladi va
`docs/status/live.json` ga yozadi. build.py shu faylni plan.py ustiga qo'yadi.
Ishga tushirish: python3 scripts/sync_status.py  (--offline: gh'siz, mavjud live.json bilan build).
Tafsilot: docs/status/README.md.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STATUS_DIR = ROOT / "docs" / "status"
LIVE = STATUS_DIR / "live.json"
TZ = ZoneInfo("Asia/Tashkent")

# Label → dashboard holati. Tartib muhim: bir nechta label bo'lsa birinchisi oladi.
LABEL_STATUS = (
    ("status:blocked", "blocked"),
    ("status:review", "in_progress"),
    ("status:in-progress", "in_progress"),
    ("status:ready", "ready"),
)

ISSUE_FIELDS = (
    "number title state labels(first: 20) { nodes { name } } "
    "closedByPullRequestsReferences(first: 10, includeClosedPrs: true) { nodes { number merged } }"
)


def repo_slug() -> tuple[str, str]:
    url = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],  # noqa: S607
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    m = re.search(r"([^/:]+)/([^/]+?)(?:\.git)?$", url)
    if not m:
        raise SystemExit(f"Repo nomini aniqlab bo'lmadi: {url}")
    return m.group(1), m.group(2)


def build_query(owner: str, name: str, numbers: list[int]) -> str:
    aliases = " ".join(f"i{n}: issue(number: {n}) {{ {ISSUE_FIELDS} }}" for n in numbers)
    ready = (
        'ready: issues(first: 20, states: OPEN, labels: ["status:ready"], '
        "orderBy: {field: CREATED_AT, direction: ASC}) "
        "{ nodes { number title labels(first: 20) { nodes { name } } } }"
    )
    return f'{{ repository(owner: "{owner}", name: "{name}") {{ {ready} {aliases} }} }}'


def gh_graphql(query: str) -> dict[str, Any]:
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    data: dict[str, Any] = json.loads(out)
    if data.get("errors"):
        raise SystemExit(f"GraphQL xatosi: {data['errors']}")
    return data


def _labels(node: dict[str, Any]) -> set[str]:
    return {lbl["name"] for lbl in node.get("labels", {}).get("nodes", [])}


def issue_status(node: dict[str, Any]) -> str | None:
    """Issue holati; status label'i yo'q ochiq issue uchun None (plan.py qiymati qoladi)."""
    if node["state"] == "CLOSED":
        return "done"
    labels = _labels(node)
    return next((status for label, status in LABEL_STATUS if label in labels), None)


def merged_prs(node: dict[str, Any]) -> str:
    refs = node.get("closedByPullRequestsReferences", {}).get("nodes", [])
    return ", ".join(f"#{n}" for n in sorted({r["number"] for r in refs if r.get("merged")}))


def next_task(ready_nodes: list[dict[str, Any]]) -> str:
    """Eng kichik raqamli status:ready issue (kunduzgi `run:day` sessiyasi olganlari tashlanadi)."""
    free = [n for n in ready_nodes if "run:day" not in _labels(n)]
    if not free:
        return "status:ready issue yo'q — backlog ko'rib chiqiladi"
    first = min(free, key=lambda n: n["number"])
    return f"#{first['number']} {first['title']}"


def parse(data: dict[str, Any], today: str) -> dict[str, Any]:
    repo = data["data"]["repository"]
    issues: dict[str, dict[str, str]] = {}
    for key, node in repo.items():
        if not key.startswith("i") or node is None:
            continue
        entry: dict[str, str] = {}
        status = issue_status(node)
        if status:
            entry["status"] = status
        prs = merged_prs(node)
        if prs:
            entry["pr"] = prs
        if entry:
            issues[f"#{node['number']}"] = entry
    return {
        "as_of": today,
        "next_task": next_task(repo["ready"]["nodes"]),
        "issues": dict(sorted(issues.items(), key=lambda kv: int(kv[0][1:]))),
    }


def plan_issue_numbers() -> list[int]:
    sys.path.insert(0, str(STATUS_DIR))
    from plan import TASKS

    return sorted({int(t["issue"][1:]) for t in TASKS if t["issue"].startswith("#")})


def main(argv: list[str]) -> int:
    if "--offline" not in argv:
        owner, name = repo_slug()
        data = gh_graphql(build_query(owner, name, plan_issue_numbers()))
        live = parse(data, datetime.now(TZ).date().isoformat())
        LIVE.write_text(json.dumps(live, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"live.json: {len(live['issues'])} issue, keyingi: {live['next_task']}")
    return subprocess.run([sys.executable, str(STATUS_DIR / "build.py")], check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
