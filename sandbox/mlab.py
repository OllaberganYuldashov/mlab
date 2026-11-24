"""Sandbox'dagi `mlab` moduli: brauzerdagi (Pyodide worker) bilan bir xil API, tarmoqsiz.

df = mlab.load("iris"). Datasetlar image ichida: /opt/mlab/datasets/<nom>.csv (content/datasets).
"""

from __future__ import annotations

import os
import re

DATASETS_DIR = os.environ.get("MLAB_DATASETS", "/opt/mlab/datasets")
_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}\Z")


def load(name: str):
    """Platformadagi datasetni pandas DataFrame sifatida yuklaydi: df = mlab.load("iris")."""
    if not isinstance(name, str) or not _NAME.match(name):
        raise ValueError(f"Dataset nomi noto'g'ri: {name!r}")
    path = os.path.join(DATASETS_DIR, f"{name}.csv")
    if not os.path.isfile(path):
        raise ValueError(f"Bunday dataset yo'q: {name!r}")
    import pandas as pd

    return pd.read_csv(path)
