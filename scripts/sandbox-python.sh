#!/usr/bin/env bash
# sandbox-python.sh — sandbox image'idagi muhitga mos lokal Python (sandbox/Dockerfile: Python 3.14,
# sandbox/requirements.txt, mlab.py site-packages ichida). `check_lab_solutions --python <yo'l>` uchun.
# Muhit bo'lmasa yoki requirements o'zgargan bo'lsa yaratadi, aks holda qayta ishlatadi; python yo'lini chiqaradi.
# Foydalanish:
#   PY=$(scripts/sandbox-python.sh)
#   cd backend && uv run python manage.py check_lab_solutions ../content --python "$PY"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${SANDBOX_VENV:-/tmp/mlab-sandbox-venv}"
STAMP="$VENV/.requirements.sha256"
want="$(cat "$ROOT/sandbox/requirements.txt" "$ROOT/sandbox/mlab.py" | sha256sum | cut -d' ' -f1)"
if [[ ! -x "$VENV/bin/python" || "$(cat "$STAMP" 2>/dev/null)" != "$want" ]]; then
  rm -rf "$VENV"
  uv venv -q --python 3.14 "$VENV" >&2
  uv pip install -q --python "$VENV/bin/python" --require-hashes -r "$ROOT/sandbox/requirements.txt" >&2
  site="$("$VENV/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
  cp "$ROOT/sandbox/mlab.py" "$site/mlab.py"
  echo "$want" > "$STAMP"
fi
echo "$VENV/bin/python"
