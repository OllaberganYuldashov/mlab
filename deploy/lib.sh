#!/usr/bin/env bash
# deploy/lib.sh (R0-16) — deploy.sh, smoke.sh va backup.sh uchun umumiy funksiyalar.
# Faqat `source` qilinadi. Secret'lar bu yerda yo'q: hammasi MLAB_ENV_FILE (server .env, chmod 600) da.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${MLAB_ENV_FILE:-/opt/mlab/.env}"

die() {
  echo "XATO: $*" >&2
  exit 1
}

compose() {
  docker compose -f "$REPO_DIR/deploy/compose.prod.yaml" --env-file "$ENV_FILE" "$@"
}

# .env mavjud va faqat egasi o'qiy oladi (chmod 600) — aks holda to'xtaymiz.
require_env_file() {
  [ -f "$ENV_FILE" ] || die "$ENV_FILE topilmadi (docs/learn/server.md, 3-qadam)"
  local mode
  mode="$(stat -c '%a' "$ENV_FILE")"
  case "$mode" in
    600 | 400) ;;
    *) die "$ENV_FILE ruxsati $mode — chmod 600 qiling" ;;
  esac
}

# .env dan bitta qiymat (shell'ga source qilmasdan: qiymatda maxsus belgilar bo'lishi mumkin).
env_value() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//'
}
