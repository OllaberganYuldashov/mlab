"""docs/status/*.json ni plan.py dagi ma'lumotdan yasaydi (dashboard: "MLab loyiha holati").

Har run oxirida Claude `plan.py` dagi holatlarni yangilaydi, `python3 docs/status/build.py` ni ishga tushiradi
va fayllarni dashboard'ga yuklaydi (docs/prompts/nightly-run.md, 8-qadam).
"""

from __future__ import annotations

import json
from pathlib import Path

from plan import ITERATIONS, META, RELEASES, TASKS

HERE = Path(__file__).resolve().parent
POINTS = {"S": 1, "M": 2}
STATUSES = {"done", "in_progress", "ready", "planned", "blocked"}


def main() -> None:
    rows = []
    est = {i["iteration"]: i["est_points"] for i in ITERATIONS}
    epics: dict[str, list[dict]] = {}
    for t in TASKS:
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
        ("meta", [META]),
    ):
        (HERE / f"{name}.json").write_text(
            json.dumps({"rows": data}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    print(f"{len(rows)} task, {len(ITERATIONS)} iteratsiya, {len(RELEASES)} reliz")


if __name__ == "__main__":
    main()
