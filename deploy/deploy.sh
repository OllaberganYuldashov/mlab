#!/usr/bin/env bash
# deploy/deploy.sh (R0-16; ADR-0004) — serverda bitta `good-*` tegni deploy qiladi. Takroriy chaqirish xavfsiz:
# bir xil teg ikkinchi marta chaqirilsa image'lar keshdan olinadi, konteynerlar o'zgarmasa tegilmaydi.
# Foydalanish:  deploy/deploy.sh good-2026-11-23-1415-abc1234
# Ham self-hosted runner (workflow), ham qo'lda SSH orqali chaqiriladi — mantiq shu yerda, workflow faqat chaqiradi.
set -euo pipefail
# shellcheck source=deploy/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

TAG="${1:-}"
[[ "$TAG" =~ ^good-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4}-[0-9a-f]{7}$ ]] \
  || die "teg 'good-YYYY-MM-DD-HHMM-<sha7>' ko'rinishida bo'lishi kerak (berilgan: '${TAG}')"

require_env_file
cd "$REPO_DIR"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "ishchi katalogda o'zgarishlar bor — avval ularni saqlang yoki bekor qiling"

PREVIOUS="$(git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)"
echo "Hozirgi versiya: ${PREVIOUS}; yangi: ${TAG}"

# Migratsiyadan oldin zaxira: noto'g'ri migratsiya bo'lsa tiklash uchun nuqta bor.
if compose ps --status running --services 2>/dev/null | grep -qx db; then
  "$REPO_DIR/deploy/backup.sh" backup
fi

git fetch --tags --force origin
git checkout --detach "refs/tags/${TAG}"

export MLAB_VERSION="$TAG"
compose up -d --build --remove-orphans
compose ps

if "$REPO_DIR/deploy/smoke.sh"; then
  echo "Deploy muvaffaqiyatli: ${TAG}"
else
  echo "Smoke test yiqildi. Oldingi versiyaga qaytish: deploy/deploy.sh <oldingi good-* teg> (${PREVIOUS})" >&2
  exit 1
fi
