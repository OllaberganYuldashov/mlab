# CLAUDE.md — L1 · MLab

> Bu faylni Claude har bir sessiya boshida o'qiydi. To'liq ish qoidalari: `docs/PLAYBOOK.md`.
> Talablarning yagona manbai: `docs/SRS.md` (SRS v2, egasi tomonidan 2026-11-22 da tasdiqlangan).

## 1. Loyiha

- **ID va nom:** L1 · MLab — Machine Learning fanini o'qitish uchun interaktiv platforma.
- **Maqsad:** bakalavr talabalariga ML fanini brauzerdagi laboratoriya, avtomatik baholanadigan topshiriqlar,
  moslashuvchan variantlar va real vaqt monitoringi orqali o'qitadigan yopiq (private) platforma.
- **Foydalanuvchilar:** super admin, admin, o'qituvchi (instructor), talaba, mehmon (faqat sertifikat tekshirish).
- **Hozirgi reliz:** R0 — Poydevor, keyin R1 — MVP (`docs/SRS.md` 9-bo'lim, `docs/BACKLOG.md`).
- **Stack:** `docs/adr/0001-stack.md`. Qisqasi: Django 5 + DRF, Django Channels + Redis, Celery, PostgreSQL 16;
  React + TypeScript (Vite), CodeMirror 6, Pyodide (Web Worker); Docker sandbox; Caddy; Gemini API (almashtiriladigan qatlam).
- **Asosiy hujjatlar:** `docs/SRS.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/BACKLOG.md`, `docs/PROGRESS.md`.

## 2. Til

- Hujjatlar, PR tavsifi, `docs/learn/` darslari va izohlar **o'zbek tilida** (lotin).
- Interfeys matnlari o'zbek tilida, alohida tarjima fayllarida (`frontend/src/i18n/uz.json`, backend `locale/`) — R3 da rus tili qo'shiladi.
- Kod, identifikatorlar va commit sarlavhasi **ingliz tilida** (Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`).
- Talab ID'lari (masalan, `AUTH-02`) commit, PR va testlarda ko'rsatiladi: `test_auth_02_lockout_after_5_failures`.

## 3. Repo tuzilmasi

```text
backend/            Django loyihasi (config/, apps/*), pyproject.toml (uv)
frontend/           React + TypeScript (Vite), npm
sandbox/            Avtobaholovchi konteyner image'i va runner
content/            Kurs kontenti kod sifatida: course.yaml, topics/, labs/, quizzes/, datasets/
deploy/             compose.prod.yaml, Caddyfile, backup skriptlari
compose.yaml        Lokal servislar (PostgreSQL, Redis)
docs/               Hujjatlar (SRS, PRD, ARCHITECTURE, adr/, learn/ ...)
```

Django ilovalari (`backend/apps/`): `accounts`, `sections`, `courses`, `labs`, `grading`, `monitoring`,
`chat`, `tutor`, `integrity`, `certificates`, `reports`, `audit`. Yangi ilova faqat ADR bilan.

## 4. Buyruqlar

| Vazifa | Buyruq |
| --- | --- |
| Backend bog'liqliklari | `cd backend && uv sync` (Python 3.12 — `.python-version`; yo'q bo'lsa uv o'zi o'rnatadi) |
| Frontend bog'liqliklari | `cd frontend && npm ci` (Node 22; lockfile bo'yicha) |
| Lokal servislar | Bulutda: `service postgresql start && service redis-server start` (setup skript ham qiladi). Kompyuterda: `docker compose up -d db redis` (R0-03) |
| Migratsiyalar | `cd backend && uv run python manage.py migrate` (env o'zgaruvchilari kerak, pastga qarang) |
| Migratsiya to'liqligi | `cd backend && uv run python manage.py makemigrations --check --dry-run` |
| Backend testlari | `cd backend && uv run pytest` (coverage ≥ 85% shu yerda tekshiriladi; `config.settings.test` soxta default'lar bilan) |
| Frontend testlari | `cd frontend && npm test -- --run --coverage` (coverage ≥ 85% `vite.config.ts` da) |
| E2E | `cd frontend && npx playwright test --trace off` (o'zi `build` + `preview` ni ishga tushiradi; bulutda Chromium oldindan o'rnatilgan) |
| Frontend build | `cd frontend && npm run build` |
| Lint va format | `cd backend && uv run ruff check . && uv run ruff format --check .`; `cd frontend && npm run lint` |
| Type check | `cd backend && uv run mypy .`; `cd frontend && npm run typecheck` |
| Zaifliklar | `cd backend && uv run pip-audit --skip-editable`; `cd frontend && npm audit --audit-level=high` |
| Deploy tekshiruvi | `cd backend && uv run python manage.py check --deploy --settings=config.settings.prod` (prod env bilan) |
| Kontent importi | `cd backend && uv run python manage.py import_content ../content` (R0-13) |
| Ishga tushirish | `cd backend && uv run python manage.py runserver` va `cd frontend && npm run dev` |

> `manage.py` default `config.settings.dev` ni ishlatadi va majburiy env'siz ishga tushmaydi (fail fast):
> `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `ALLOWED_HOSTS` — soxta qiymatlari `.env.example`da.
> CI: `.github/workflows/ci.yml` (nomi `ci`), job'lar `backend` va `frontend`.

## 5. Qat'iy qoidalar

1. **main'ga hech qachon push qilma.** Har task `claude/` bilan boshlanadigan branch'da, natija PR.
   **Hamma merge'ni Claude qiladi** (egasining 2026-11-22 qarori: "merge'larni to'liq o'zingga topshiraman"), faqat ikki skript orqali:
   - oddiy PR → `scripts/merge-if-green.sh <PR>` (merge-gate, ci, secret-scan va boshqa barcha tekshiruvlar yashil);
   - `needs:owner` PR (himoyalangan fayllar: `ci.yml` va boshqa workflow'lar, `CLAUDE.md`, `docs/SRS.md`, `docs/RECOVERY.md`,
     `deploy/`) → **main'dagi nusxadan**: `git fetch origin main && git show origin/main:scripts/merge-protected.sh | bash -s -- <PR>`.
     Shartlar: ci, secret-scan va boshqa barcha tekshiruvlar yashil, merge-gate faqat `needs:owner` sababli qizil, `hold`/`alert:*` yo'q.
     Oldin diff'ni o'zing qayta ko'rib chiq va PR tavsifiga "Nega himoyalangan fayl o'zgardi" bo'limini yoz.
   Boshqa yo'l bilan merge qilish (`gh api .../merge`, `gh pr merge`, MCP merge, veb) taqiqlangan. **Himoya mexanizmining o'zi**
   (`.claude/settings.json`, `scripts/merge-*.sh`, merge-gate/main-guard/known-good/secret-scan/weekly-backup workflow'lari)
   o'zgargan PR'ni faqat egasi merge qiladi — skript uni rad etadi; bunday PR kerak bo'lsa `status:blocked` va savol.
   `docs/SRS.md` faqat egasining yozma javobi (issue izohi) asosida o'zgaradi (12-qoida).
   Tekshiruvni o'tkazish uchun testni o'chirish, `skip`/`xfail` qo'shish yoki coverage chegarasini tushirish — qoidabuzarlik.
2. **Secret'lar bilan ishlamaysan.** `.env`ni o'qima, yozma, chiqarma. Yangi sozlama: kodda muhit o'zgaruvchisidan o'qi, `.env.example`ga faqat nomi va soxta qiymat, `docs/SECURITY.md` jadvaliga qator. Ilova majburiy sozlama yo'q bo'lsa darhol to'xtaydi (fail fast).
3. **Haqiqiy shaxsiy ma'lumot ishlatilmaydi.** FIO va Hemis ID testlarda faqat factory/Faker bilan. Haqiqiy talaba ro'yxati, baholar yoki loglar repoga, bulut sessiyasiga va promptga tushmaydi.
4. **Gemini'ga shaxsiy ma'lumot yuborilmaydi** (AI-04): faqat savol, kod va mavzu konteksti. Testlarda AI provayderi doim `fake`.
5. **Talaba kodi hech qachon Django, Celery yoki boshqa servis jarayonida bajarilmaydi** — faqat brauzerda (Pyodide) yoki sandbox konteynerida (AGR-03). Yashirin testlar brauzerga yuborilmaydi.
6. **Avtorizatsiya har endpoint'da obyekt darajasida:** o'qituvchi faqat o'z guruhlarini, talaba faqat o'z ishlarini ko'radi. Har yangi endpoint uchun "begona foydalanuvchi" testi majburiy (IDOR).
7. **Muhim harakatlar audit jurnaliga yoziladi** (ADM-02): rol, baho, parol tiklash, kirish oynasi o'zgarishi.
8. **Yangi texnologiya faqat ADR bilan** (`docs/adr/`), muqobillar solishtirilgandan keyin.
9. **Bitta task — bitta PR.** Task bitta sessiyaga sig'masa, kod yozishdan oldin subtask'larga bo'l.
10. **Yarim ish qoldirma.** Yangi task faqat oldingisi Definition of Done bo'yicha yopilgandan keyin.
11. **Qaror egasiga tegishli bo'lsa** (talabni o'zgartirish, arxitektura, pul, xavfsizlik, ma'lumot o'chirish): issue'ni `status:blocked` qil, savolni issue va `docs/PROGRESS.md`ga yoz, keyingi ready issue'ga o't.
12. **SRS'dan chetga chiqma.** Talab noaniq yoki noto'g'ri bo'lsa — o'zgartirma, `status:blocked` va savol.

## 6. Definition of Done

- [ ] Avval test yozilgan; unit va integration testlar yashil (real PostgreSQL va Redis bilan).
- [ ] Foydalanuvchi oqimi o'zgargan bo'lsa, Playwright e2e test bor.
- [ ] Lint, type check, gitleaks va `pip-audit`/`npm audit` (high) yashil.
- [ ] Coverage kamida 85% (backend va frontend alohida).
- [ ] Yangi endpoint: ruxsat testi (begona foydalanuvchi 403/404), OpenAPI yangilangan.
- [ ] Migratsiya bo'lsa: `migration-safety` bo'yicha tekshirilgan, orqaga qaytariladigan.
- [ ] Bug tuzatilganda uni takrorlaydigan test qo'shilgan.
- [ ] Interfeys matnlari tarjima faylida, o'zbek tilida.
- [ ] `docs/CHANGELOG.md`, `docs/PROGRESS.md` yangilangan; muhim qaror uchun ADR.
- [ ] Yangi texnologiya uchun `docs/learn/<texnologiya>.md` darsi.
- [ ] PR tavsifi shablon bo'yicha, bajarilgan talab ID'lari bilan.

## 7. Run protokoli

1. `git pull`, keyin shu fayl va `docs/PROGRESS.md`. Ochiq `alert:main-guard` yoki `alert:red-light` issue bo'lsa — birinchi navbatda o'sha.
2. `docs/RECOVERY.md` bo'yicha sog'liq tekshiruvi; natija PROGRESS.md'ga.
3. `status:ready` label'li, bog'liqligi yopilgan eng kichik issue olinadi va `status:in-progress` qilinadi.
   Boshqa run'ning `status:in-progress` issue'si (oxirgi yangilanishi 6 soatdan yangi) olinmaydi — har tunda 2 run bor.
4. Issue katta bo'lsa: kod yozilmaydi, subtask issue'larga bo'linadi — bu o'sha sessiyaning to'liq ishi.
5. `claude/<issue-raqami>-<qisqa-nom>` branch, darhol draft PR.
6. Test → kod → testlar, lint, xavfsizlik yashil → hujjatlar → commit va push. Har tugagan bosqich alohida commit.
7. **Run hajmi** (egasining 2026-11-22 qarori, 2× oshirilgan): har run kamida **2 ta `size:M` yoki 4 ta `size:S`**
   (M = 2 ball, S = 1 ball; maqsad ≥ 4 ball). Maqsadga yetgach ham limit qolsa — keyingi issue. Limit tugasa —
   yangi issue boshlanmaydi, boshlangani DoD bilan yopiladi yoki draft PR va PROGRESS.md'da aniq to'xtash nuqtasi.
8. PR "ready for review" → merge (5.1-qoida: `merge-if-green.sh` yoki `needs:owner` uchun `merge-protected.sh`).
   Kod 0: merge bo'ldi, issue yopiladi (`Closes #`), keyingi task yangilangan main'dan boshlanadi.
   Kod 1: qizil — sababini tuzat (Sariq qoidasi, ko'pi bilan 2 urinish). Kod 2: tekshiruvlar tugamadi — keyingi taskka o't,
   oxirida qayta urin. Run oxirida ham merge bo'lmagan PR — kunlik hisobotda sababi bilan.
9. Yakunda: `docs/PROGRESS.md` va `docs/learn/JOURNAL.md` yangilanadi (ular ham PR orqali) va **kunlik hisobot** yoziladi (11-bo'lim).

## 8. Vazifalar (GitHub Issues)

- Holat: `status:ready`, `status:in-progress`, `status:blocked`, `status:review`.
- Tur: `type:feature`, `type:bug`, `type:chore`, `type:docs`, `type:content`. Hajm: `size:S`, `size:M` (L bo'lmaydi — bo'linadi).
- Reliz va iteratsiya: `release:R0`, `release:R1`, `iter:I1` ... `iter:I5`. Talab ID issue sarlavhasida: `[AUTH-02] Login lockout`.
- Holat faqat label orqali (bulut sessiyasi GitHub Projects taxtasini yangilay olmaydi).

## 9. Skill jadvali

| Qachon | Skill |
| --- | --- |
| Har task | think-before-coding, testing-with-discernment, security-discipline |
| Model, migratsiya | data-modeling-discipline, migration-safety, index-design (+ schema-reviewer agenti R0 va I1 oxirida) |
| So'rovlar, ro'yxatlar | query-discipline, /hunt-n-plus-one, keyset-pagination |
| Auth, rollar, guruh ruxsatlari | auth-and-authorization + security-reviewer agenti |
| Sandbox, kod bajarish | security-discipline, algorithmic-complexity-attacks, docker-build-strategies + security-reviewer |
| Celery, navbat, AI chaqiruvi | idempotency-and-side-effects, retry-amplification, database-queues, error-handling-as-design |
| WebSocket, jonli panel | performance-and-scaling, queueing-and-utilization, observability-by-default |
| Vaqt, jadval, kirish oynalari | clocks-and-time (Asia/Tashkent, `timestamptz`) |
| Ball va vaznlar | floating-point (ball `Decimal` yoki butun son) |
| O'zbek matni, FIO | unicode-pitfalls (oʻ, gʻ, apostrof variantlari) |
| Dockerfile, compose | docker-build-strategies, docker-compose-patterns, docker-destructive-guardrails |
| API javobi o'zgardi | expand-contract, hyrums-law |
| Bug | debugging-discipline |
| Yangi texnologiya | boring-by-default + ADR |
| Reliz oxiri | mutation-testing, code-hotspots, security-reviewer, performance-and-scaling |

Agentlar (`security-reviewer`, `schema-reviewer`, `incident-thinker`) faqat auth, sandbox, katta migratsiya va reliz oxirida — ular limitni ko'p sarflaydi.

## 10. Qizil chiroq va ortga qaytish

To'liq tartib: `docs/RECOVERY.md`. Qisqasi:

- Har run boshida **sog'liq tekshiruvi**: main CI, testlar, ilova ishga tushishi, regressiyalar, rad etilgan PR'lar, urinishlar soni, main-guard. Natija PROGRESS.md'ga: Yashil / Sariq / Qizil.
- **Sariq:** yangi funksiya olinmaydi, avval tuzatiladi (ko'pi bilan 2 urinish).
- **Qizil:** to'xta, tashxis (good-* teglarda bisect), `alert:red-light` issue va `docs/incidents/` hisoboti, variantlar (A–E) va nima yo'qolishi, **egasining ruxsatini kut**.
- Ortga qaytish eng kichik darajadan va faqat PR orqali; tarix o'chirilmaydi, D/E dan oldin `claude/archive-<sana>` branch.
- **Hech qachon o'zing "Ruxsat" yozma va `approved:*` label qo'yma.** Qizil holatda hech narsa merge qilinmaydi;
  egasi "Ruxsat: X" yozgandan keyin faqat o'sha tiklash PR'i skript orqali merge qilinadi.

## 11. Hisobot

- **Kunlik hisobot** — har run oxirida "📋 Kunlik hisobotlar" issue'siga bitta izoh (issue bo'lmasa yaratiladi, `report` label bilan):
  sog'liq (Yashil/Sariq/Qizil), merge bo'lgan PR'lar va bajarilgan talab ID'lari (Claude merge qilgan `needs:owner` PR'lar
  alohida qatorda — qaysi himoyalangan fayl va nega), merge bo'lmagan PR'lar va sababi,
  javob kutayotgan savollar (`status:blocked`), keyingi tasklar, egasi o'qishi kerak bo'lgan dars. 10–15 qator, oddiy tilda.
  Ikkala tungi run ham yozadi: sarlavhada sana va run (`1/2` yoki `2/2`).
- **Egasi faqat kunlik hisobotni o'qiydi va savollarga javob beradi** (2026-11-22 qarori). Shuning uchun har savol hisobotda
  issue havolasi, qisqa kontekst, 2–3 variant va Claude tavsiyasi bilan yoziladi; javob kutilayotganda ish boshqa issue bilan davom etadi.
- Run boshida draft PR, har tugagan bosqichda tushunarli commit.
- PR tavsifi shablon bo'yicha, o'zbek tilida, bajarilgan talab ID'lari bilan.
- `docs/learn/JOURNAL.md`: har run uchun qisqa yozuv — nima qilindi, qaysi skill nima uchun ishlatildi, egasi nimani o'rganishi kerak.
