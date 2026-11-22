# CHANGELOG

Format: [Keep a Changelog](https://keepachangelog.com/), versiyalar: [SemVer](https://semver.org/).

## [Unreleased]
### Added
- Kuzatuvchanlik (R0-14; NFR-17, NFR-11): `X-Request-ID` middleware, stdout'ga JSON loglar (`LOG_LEVEL`), formatter'da Hemis ID va IP maskalash, parol/token/cookie/Authorization hech qachon yozilmaydi; `GET /readyz` (DB va Redis: 200/503); `docs/learn/observability.md`.
- Custom User (R0-04; AUTH-01, AUTH-03, NFR-10): `accounts.User` (login — 12 xonali Hemis ID), `Direction`, rollar (`super_admin`, `admin`, `instructor`, `student`), Argon2 xesh; DB CHECK cheklovlari; loyihaning birinchi migratsiyasi `accounts.0001`; testlarda Faker; `docs/learn/custom-user-argon2.md`.
- Ish tartibi (egasining 2026-11-22 qarori): har tunda 2 run (23:23, 03:23), run hajmi 2× (≥ 2 M yoki 4 S), oddiy PR'larni Claude merge qiladi, `needs:owner` PR'lar egasida; kunlik hisobotda savollar variant va tavsiya bilan.
- Frontend skeleti (R0-02): Vite + React 19 + TypeScript, `src/i18n/uz.json` va `t()`, Vitest + Testing Library (coverage ≥ 85%), ESLint, Playwright smoke test; `ci` ga `frontend` job; `docs/learn/react-typescript.md`; setup skriptga `uv sync` va `npm ci`.
- Backend skeleti (R0-01): Django 5.2 + DRF, `config/settings/{base,dev,test,prod}`, env'dan sozlama va fail fast, `/healthz`; ruff, mypy, pytest (coverage ≥ 85%); CI workflow `ci` (PostgreSQL 16, Redis 7, pip-audit); `docs/learn/django.md`.
- Nazorat ostidagi avtomatik merge: `merge-gate` workflow, `scripts/merge-if-green.sh`, kunlik hisobot (egasining 2026-11-22 qarori).
- L1 · MLab loyiha fayllari: CLAUDE.md, SRS v2, PRD, ARCHITECTURE, ADR-0001, BACKLOG, SECURITY, TESTING.
- Nazorat workflow'lari: secret-scan, main-guard, weekly-backup, known-good.
- `content/` tuzilmasi va mavzular ro'yxati (M01–M22, A1–A15).
