"""Notebook holatining shakli (LAB-01, LAB-05).

Faqat kataklar manbasi saqlanadi — chiqishlar (grafik, matn) brauzerda qayta hosil qilinadi,
shuning uchun saqlangan hajm kichik va bashorat qilinadigan.

    {"format": 1, "cells": [{"id": "c1", "type": "code" | "markdown", "source": "..."}]}
"""

from __future__ import annotations

import json
import re
from typing import Any

NOTEBOOK_FORMAT = 1
MAX_CELLS = 200
MAX_NOTEBOOK_BYTES = 1024 * 1024  # 1 MB JSON
_CELL_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}\Z")
_CELL_TYPES = ("code", "markdown")


class NotebookError(ValueError):
    pass


def validate_notebook(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"format", "cells"}:
        raise NotebookError("notebook: faqat 'format' va 'cells' kalitlari")
    if value["format"] != NOTEBOOK_FORMAT or isinstance(value["format"], bool):
        raise NotebookError(f"notebook: format {NOTEBOOK_FORMAT} bo'lishi kerak")
    cells = value["cells"]
    if not isinstance(cells, list) or len(cells) > MAX_CELLS:
        raise NotebookError(f"notebook: cells ro'yxat, ko'pi bilan {MAX_CELLS} ta")
    seen: set[str] = set()
    for cell in cells:
        if not isinstance(cell, dict) or set(cell) != {"id", "type", "source"}:
            raise NotebookError("katak: faqat 'id', 'type', 'source' kalitlari")
        if not isinstance(cell["id"], str) or not _CELL_ID_RE.match(cell["id"]):
            raise NotebookError("katak id: 1..64 belgi (harf, raqam, _ -)")
        if cell["id"] in seen:
            raise NotebookError("katak id takrorlangan")
        seen.add(cell["id"])
        if cell["type"] not in _CELL_TYPES:
            raise NotebookError("katak turi: code yoki markdown")
        if not isinstance(cell["source"], str):
            raise NotebookError("katak manbasi matn bo'lishi kerak")
    if len(json.dumps(value, ensure_ascii=False).encode()) > MAX_NOTEBOOK_BYTES:
        raise NotebookError(f"notebook {MAX_NOTEBOOK_BYTES // 1024} KB dan katta")
    return value
