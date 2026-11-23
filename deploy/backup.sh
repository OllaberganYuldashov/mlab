#!/usr/bin/env bash
# deploy/backup.sh (R0-16; ADM-04, NFR-08) — kunlik PostgreSQL zaxirasi va tiklash.
#   deploy/backup.sh backup                  — zaxira oladi, eskilarini (MLAB_BACKUP_KEEP_DAYS, default 14) o'chiradi
#   deploy/backup.sh list                    — mavjud zaxiralar
#   deploy/backup.sh restore <fayl> --yes    — bazani shu zaxiradan TIKLAYDI (joriy ma'lumot ustiga yoziladi)
# RPO <= 24 soat (kuniga bir zaxira), RTO <= 4 soat (tiklash bosqichlari docs/learn/server.md da).
# Media fayllar: hozir yo'q (talaba fayl yuklamaydi). Media paydo bo'lganda shu yerga qo'shiladi (R1 I5, sertifikatlar).
set -euo pipefail
# shellcheck source=deploy/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

BACKUP_DIR="${MLAB_BACKUP_DIR:-/opt/mlab/backups}"
KEEP_DAYS="${MLAB_BACKUP_KEEP_DAYS:-14}"
[[ "$KEEP_DAYS" =~ ^[0-9]+$ ]] && [ "$KEEP_DAYS" -ge 1 ] || die "MLAB_BACKUP_KEEP_DAYS musbat butun son bo'lishi kerak"

do_backup() {
  require_env_file
  umask 077
  mkdir -p "$BACKUP_DIR"
  local stamp out part
  stamp="$(TZ=Asia/Tashkent date +%Y%m%d-%H%M%S)"
  out="${BACKUP_DIR}/db-${stamp}.dump"
  part="${out}.part"
  # Avval vaqtinchalik faylga: yarim yozilgan zaxira hech qachon haqiqiy zaxira bo'lib qolmaydi.
  if ! compose exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' >"$part"; then
    rm -f -- "$part"
    die "pg_dump muvaffaqiyatsiz"
  fi
  [ -s "$part" ] || { rm -f -- "$part"; die "zaxira bo'sh chiqdi"; }
  mv -- "$part" "$out"
  # Eski zaxiralar: faqat shu katalogdagi db-*.dump fayllar, KEEP_DAYS dan eski; hech qachon eng oxirgisini emas.
  find "$BACKUP_DIR" -maxdepth 1 -type f -name 'db-*.dump' -mtime "+${KEEP_DAYS}" ! -newer "$out" -delete
  echo "Zaxira tayyor: ${out} ($(du -h "$out" | cut -f1))"
}

do_list() {
  ls -1t "$BACKUP_DIR"/db-*.dump 2>/dev/null || echo "Zaxira yo'q"
}

do_restore() {
  local file="${1:-}" confirm="${2:-}"
  [ -n "$file" ] && [ -f "$file" ] || die "zaxira fayli topilmadi: '${file}'"
  [ "$confirm" = "--yes" ] || die "tiklash joriy bazani O'ZGARTIRADI. Tasdiqlash uchun oxiriga --yes qo'shing"
  require_env_file
  echo "Tiklashdan oldin joriy holatning zaxirasi olinadi..."
  do_backup
  echo "web va caddy to'xtatiladi (foydalanuvchilar uchun texnik tanaffus)..."
  compose stop caddy web
  compose exec -T db sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <"$file"
  compose up -d web caddy
  "$REPO_DIR/deploy/smoke.sh"
  echo "Tiklash tugadi: ${file}"
}

case "${1:-backup}" in
  backup) do_backup ;;
  list) do_list ;;
  restore) shift; do_restore "${1:-}" "${2:-}" ;;
  *) die "noma'lum buyruq '${1}'. Foydalanish: backup | list | restore <fayl> --yes" ;;
esac
