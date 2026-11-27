"""docs/CODEMAP.md eskirmagan: modul yoki izoh o'zgarsa — `python3 scripts/codemap.py`."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_codemap_is_up_to_date() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "codemap.py"), "--check"],
        check=False,
        capture_output=True,
    )
    assert result.returncode == 0, "docs/CODEMAP.md eskirgan: python3 scripts/codemap.py"
