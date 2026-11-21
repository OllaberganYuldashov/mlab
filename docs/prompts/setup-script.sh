#!/bin/bash
# L1 · MLab — Claude Code bulut muhiti uchun setup skript.
# Muhit sozlamalaridagi "Setup script" maydoniga to'liq qo'yiladi.
# Har yangi sessiyadan oldin ishlaydi, natija taxminan 7 kun keshlanadi.
# Qoidalar: secret yo'q; har qadam qayta ishga tushirilsa ham xavfsiz; oxirida 0 kod bilan tugaydi.

# 1) Python paket menejeri uv (odatda oldindan o'rnatilgan bo'ladi)
command -v uv >/dev/null 2>&1 || pip install --quiet uv || true

# 2) PostgreSQL 16 va Redis 7 bulutda oldindan o'rnatilgan — ishga tushiramiz
service postgresql start || true
service redis-server start || true

# 3) Faqat test uchun lokal baza va foydalanuvchi (soxta parol, tashqariga ochiq emas)
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='mlab'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER mlab WITH PASSWORD 'mlab' CREATEDB;" || true
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='mlab'" | grep -q 1 \
  || sudo -u postgres createdb -O mlab mlab || true

# 4) Python 3.12 (loyiha versiyasi) va bog'liqliklar — sessiya boshida tayyor bo'lsin.
#    Skript repo papkalari turgan joyda ishga tushadi; repo yo'q bo'lsa qadam o'tkazib yuboriladi.
uv python install 3.12 || true
if [ -d mlab/backend ]; then (cd mlab/backend && uv sync --frozen) || true; fi
if [ -d mlab/frontend ]; then (cd mlab/frontend && npm ci --no-audit --no-fund) || true; fi

# Eslatma: Playwright uchun Chromium bulut muhitida oldindan o'rnatilgan (/opt/pw-browsers).
# frontend/package.json'da @playwright/test o'rnatilgan versiyaga mos qilib pin qilingan;
# "playwright install" kerak emas. Versiya o'zgarsa — shu yerga eslatma va CHANGELOG.

exit 0
