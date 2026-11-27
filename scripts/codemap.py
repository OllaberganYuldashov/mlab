"""docs/CODEMAP.md ni yasaydi: har modul uchun bitta qator (fayl izohining birinchi qatori).

Run boshida butun fayllarni o'qish o'rniga shu xarita o'qiladi (docs/prompts/nightly-run.md).
Ishga tushirish: python3 scripts/codemap.py  (--check: fayl eskirgan bo'lsa 1 bilan chiqadi)
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "CODEMAP.md"


def py_summary(path: Path) -> str:
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
    except SyntaxError:
        return ""
    return (doc or "").strip().split("\n")[0]


def ts_summary(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"/\*\*\s*\n?\s*\*?\s*(.+?)(?:\n|\*/)", text)
    return m.group(1).strip().rstrip("*/ ").strip() if m else ""


def section(title: str, files: list[Path], summary) -> list[str]:
    lines = [f"## {title}", ""]
    for f in files:
        s = summary(f)
        lines.append(f"- `{f.relative_to(ROOT)}`" + (f" — {s}" if s else ""))
    return [*lines, ""]


def build() -> str:
    out = [
        "# CODEMAP — kod xaritasi",
        "",
        "> Avtomatik: `python3 scripts/codemap.py`. Qo'lda tahrirlanmaydi."
        " Har qator — fayl izohining birinchi qatori.",
        "> Run boshida kerakli faylni shu yerdan toping va faqat o'shani o'qing"
        " (docs/prompts/nightly-run.md).",
        "",
    ]
    apps = sorted(
        p for p in (ROOT / "backend" / "apps").iterdir() if p.is_dir() and p.name != "__pycache__"
    )
    for app in apps:
        files = sorted(
            f
            for f in app.rglob("*.py")
            if "migrations" not in f.parts
            and "__pycache__" not in f.parts
            and f.name != "__init__.py"
            and f.stat().st_size > 0
        )
        if files:
            out += section(f"backend/apps/{app.name}", files, py_summary)
    cfg = sorted(f for f in (ROOT / "backend" / "config").rglob("*.py") if f.name != "__init__.py")
    out += section("backend/config", cfg, py_summary)
    tests = sorted({f.parent for f in (ROOT / "backend" / "tests").rglob("test_*.py")})
    out += (
        ["## backend/tests", ""]
        + [f"- `{d.relative_to(ROOT)}/` — {len(list(d.glob('test_*.py')))} fayl" for d in tests]
        + [""]
    )
    front = sorted(
        f
        for f in (ROOT / "frontend" / "src").rglob("*.ts*")
        if ".test." not in f.name and not f.name.endswith(".d.ts")
    )
    out += section("frontend/src", front, ts_summary)
    out += section(
        "frontend/e2e", sorted((ROOT / "frontend" / "e2e").glob("*.spec.ts")), ts_summary
    )
    out += section("sandbox", sorted((ROOT / "sandbox").glob("*.py")), py_summary)
    out += section("scripts", sorted((ROOT / "scripts").glob("*.py")), py_summary)
    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    text = build()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text(encoding="utf-8") == text else 1)
    OUT.write_text(text, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {text.count(chr(10))} qator")
