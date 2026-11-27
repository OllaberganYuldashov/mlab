"""docs/status/*.json ni plan.py (reja) va live.json (GitHub holati) dan yasaydi (dashboard: "MLab loyiha holati").

Holat va PR qo'lda yozilmaydi: `python3 scripts/sync_status.py` ularni GitHub Issues'dan `live.json` ga yozadi va
shu skriptni chaqiradi. live.json'dagi qiymat plan.py dagisidan ustun (docs/status/README.md).
"""

from __future__ import annotations

import json
from pathlib import Path

from plan import ITERATIONS, META, RELEASES, TASKS

HERE = Path(__file__).resolve().parent
POINTS = {"S": 1, "M": 2}
STATUSES = {"done", "in_progress", "ready", "planned", "blocked"}


def apply_live(tasks: list[dict], meta: dict, live: dict) -> tuple[list[dict], dict]:
    """live.json ni plan.py ustiga qo'yadi. META.next_task bo'sh bo'lsa — live.json'dagi avtomatik qiymat."""
    issues = live.get("issues", {})
    merged = [{**t, **issues.get(t["issue"], {})} if t["issue"] else dict(t) for t in tasks]
    out = {**meta, "as_of": live.get("as_of") or meta["as_of"]}
    if not out.get("next_task"):
        out["next_task"] = live.get("next_task", "")
    return merged, out


def main() -> None:
    live_path = HERE / "live.json"
    live = json.loads(live_path.read_text(encoding="utf-8")) if live_path.exists() else {}
    tasks, meta = apply_live(TASKS, META, live)
    rows = []
    est = {i["iteration"]: i["est_points"] for i in ITERATIONS}
    epics: dict[str, list[dict]] = {}
    for t in tasks:
        assert t["status"] in STATUSES, t
        if t["key"].startswith("E-"):
            epics.setdefault(t["iteration"], []).append(t)
        rows.append({**t, "points": POINTS.get(t.get("size", ""), 0)})
    # Epik (hali issue'larga bo'linmagan) — iteratsiya taxminini epiklarga teng bo'lib beradi.
    for iteration, items in epics.items():
        total, n = est[iteration] or 0, len(items)
        shares = [total // n + (1 if k < total % n else 0) for k in range(n)]
        for item, share in zip(items, shares, strict=True):
            next(r for r in rows if r["key"] == item["key"])["points"] = share
    iter_keys = {i["iteration"] for i in ITERATIONS}
    assert all(r["iteration"] in iter_keys for r in rows)
    for name, data in (
        ("tasks", rows),
        ("iterations", ITERATIONS),
        ("releases", RELEASES),
        ("meta", [meta]),
    ):
        (HERE / f"{name}.json").write_text(
            json.dumps({"rows": data}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    print(f"{len(rows)} task, {len(ITERATIONS)} iteratsiya, {len(RELEASES)} reliz")


if __name__ == "__main__":
    main()
