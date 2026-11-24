"""AGR-03 (I3-05): sandbox image'ga hujum testlari — haqiqiy Docker bilan, ADR-0007 cheklovlarida.

Ishga tushirish (repo ildizidan, Docker kerak):
  docker build -f sandbox/Dockerfile -t mlab-sandbox:dev .
  cd backend && uv run pytest ../sandbox/tests -p no:django -p no:cacheprovider --no-cov
CI job'i — I3-18/I3-19 (workflow o'zgarishi needs:owner). `SANDBOX_IMAGE` — boshqa teg.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

IMAGE = os.environ.get("SANDBOX_IMAGE", "mlab-sandbox:dev")
# ADR-0007 2-band: launcher aynan shu parametrlar bilan ishga tushiradi (launcher — I3-06).
LIMITS = [
    "--network", "none",
    "--read-only",
    "--tmpfs", "/tmp:size=64m,noexec",
    "--user", "10003:10003",
    "--memory", "512m", "--memory-swap", "512m",
    "--cpus", "1",
    "--pids-limit", "64",
    "--cap-drop", "ALL",
    "--security-opt", "no-new-privileges",
    "--ulimit", "nofile=64",
]  # fmt: skip
CHECK = "def test_ok(ns, params):\n    assert ns.get('ok') is True, repr(ns.get('ok'))\n"


def _run(code: str, time_limit: int = 20, timeout: int = 90) -> tuple[int, dict[str, Any] | None]:
    payload = {
        "code": code,
        "params": {},
        "time_limit": time_limit,
        "tests": [{"step": "s", "kind": "visible", "source": CHECK}],
    }
    proc = subprocess.run(
        ["docker", "run", "--rm", "-i", *LIMITS, IMAGE],
        input=json.dumps(payload).encode(),
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError:
        return proc.returncode, None


def _passed(result: dict[str, Any] | None) -> bool:
    return result is not None and result["tests"][0]["passed"] is True


def test_agr_03_ml_stack_and_datasets_work_offline() -> None:
    code = (
        "import mlab\n"
        "from sklearn.linear_model import LogisticRegression\n"
        "import matplotlib.pyplot as plt\n"
        "df = mlab.load('iris')\n"
        "X, y = df.iloc[:, :4], df.iloc[:, 4]\n"
        "acc = LogisticRegression(max_iter=500).fit(X, y).score(X, y)\n"
        "plt.plot([1, 2]); plt.savefig('/tmp/f.png')\n"
        "ok = len(df) == 150 and acc > 0.9\n"
    )
    rc, result = _run(code)
    assert rc == 0, result
    assert _passed(result), result


def test_agr_03_versions_match_pyodide() -> None:
    code = (
        "import sys, numpy, pandas, sklearn, scipy, matplotlib\n"
        "ok = (sys.version_info[:2] == (3, 14) and numpy.__version__ == '2.4.6'"
        " and pandas.__version__ == '3.0.2' and sklearn.__version__ == '1.8.0'"
        " and scipy.__version__ == '1.18.0' and matplotlib.__version__ == '3.10.8')\n"
    )
    assert _passed(_run(code)[1])


def test_agr_03_runs_as_unprivileged_user() -> None:
    assert _passed(_run("import os\nok = (os.getuid(), os.getgid()) == (10003, 10003)\n")[1])


def test_agr_03_no_network() -> None:
    code = (
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
        "    ok = False\n"
        "except OSError:\n"
        "    ok = True\n"
    )
    assert _passed(_run(code)[1])


def test_agr_03_filesystem_read_only_and_tmp_noexec() -> None:
    code = (
        "import os, subprocess\n"
        "blocked = 0\n"
        "for path in ('/opt/mlab/runner.py', '/etc/x', '/opt/venv/lib/x.py', '/home/x'):\n"
        "    try:\n"
        "        open(path, 'w').write('x')\n"
        "    except OSError:\n"
        "        blocked += 1\n"
        "open('/tmp/run.sh', 'w').write('#!/bin/sh\\necho hi\\n')\n"
        "os.chmod('/tmp/run.sh', 0o755)\n"
        "try:\n"
        "    subprocess.run(['/tmp/run.sh'], check=True)\n"
        "    noexec = False\n"
        "except OSError:\n"
        "    noexec = True\n"
        "ok = blocked == 4 and noexec\n"
    )
    assert _passed(_run(code)[1])


def test_agr_03_fork_bomb_is_contained() -> None:
    code = (
        "import os\n"
        "children = 0\n"
        "try:\n"
        "    for _ in range(10_000):\n"
        "        if os.fork() == 0:\n"
        "            import time; time.sleep(30); os._exit(0)\n"
        "        children += 1\n"
        "except OSError:\n"
        "    pass\n"
        "ok = children < 64\n"
    )
    rc, result = _run(code, timeout=120)
    assert _passed(result), (rc, result)


def test_agr_03_memory_limit() -> None:
    code = "blocks = []\nwhile True:\n    blocks.append(bytearray(50_000_000))\n"
    rc, result = _run(code)
    # Python MemoryError (talaba xatosi) yoki OOM-killer (137) — ikkalasida xost himoyalangan.
    assert rc == 137 or (result is not None and result["status"] == "code_error"), (rc, result)


def test_agr_03_cpu_time_limit() -> None:
    rc, result = _run("while True:\n    pass\n", time_limit=2)
    assert rc == 0
    assert result is not None
    assert result["error"] == "Vaqt tugadi (2 s)"
