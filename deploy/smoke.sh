#!/usr/bin/env bash
# deploy/smoke.sh (R0-16) — deploy'dan keyingi smoke test: /healthz (jarayon tirik) va /readyz (DB va Redis).
# Caddy orqali tekshiradi, ya'ni foydalanuvchi ko'radigan yo'l: Caddy → web → DB/Redis.
# Chiqish kodi: 0 — hammasi yaxshi; 1 — muvaffaqiyatsiz (deploy qizil hisoblanadi).
set -euo pipefail
# shellcheck source=deploy/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_env_file
SITE="$(env_value SITE_ADDRESS)"
ATTEMPTS="${SMOKE_ATTEMPTS:-24}"   # 24 x 5 s = 2 daqiqagacha kutadi (web healthcheck + sertifikat olish)
PAUSE="${SMOKE_PAUSE:-5}"

if [ "${SITE#:}" != "$SITE" ]; then
  # Sinov rejimi (:80, domensiz): HTTPS yo'q; .env da SECURE_SSL_REDIRECT=false bo'lishi kerak.
  BASE="http://127.0.0.1"
  CURL=(curl -fsS --max-time 5)
else
  # Domen bor: haqiqiy sertifikat bilan, lekin server o'z-o'ziga (DNS'ga bog'liq emas) ulanadi.
  BASE="https://${SITE}"
  CURL=(curl -fsS --max-time 5 --resolve "${SITE}:443:127.0.0.1")
fi

check() {
  local path="$1" attempt
  for ((attempt = 1; attempt <= ATTEMPTS; attempt++)); do
    if "${CURL[@]}" -o /dev/null "${BASE}${path}"; then
      echo "OK   ${path}"
      return 0
    fi
    [ "$attempt" -lt "$ATTEMPTS" ] && sleep "$PAUSE"
  done
  echo "XATO ${path} ${ATTEMPTS} urinishdan keyin ham javob bermadi" >&2
  return 1
}

check /healthz
check /readyz
echo "Smoke test o'tdi."
