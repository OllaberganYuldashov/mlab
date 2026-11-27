# PROGRESS — L1 · MLab holati

> Har sessiya oxirida Claude yangilaydi. Yangi sessiya ishni shu fayldan davom ettiradi.

## Sog'liq
- Holat: **Yashil** (2026-11-28, tungi run 1/2): main CI yashil, ochiq `alert:*` yo'q. Qizil chiroq (#193, Actions
  daqiqalari tugagan) 27-noyabr egasining "Ruxsat: A" bilan yopildi — repo vaqtincha public, Actions bepul.
- Oxirgi yashil nuqta: `good-2026-11-27-1024-9b595d0`
- Tuzatish urinishlari: 0
- Ochiq `alert:main-guard` / `alert:red-light`: yo'q
- Actions sarfi: repo public — bepul. 1-dekabrdan private: `scripts/actions-usage.sh` (CI-BUDGET PR egasi push qilishini kutmoqda).

## Hozirgi holat
- Reliz: **R1 — MVP, I3** (I1 va I2 yopildi 2026-11-24 — `docs/iterations/I1.md`, `I2.md`) (R0 kodi yopildi 2026-11-23; serverga bog'liq qism — birinchi deploy, smoke, tiklash sinovi — server tayyor bo'lganda)
- TZ: SRS v2 tasdiqlangan → `docs/SRS.md`
- GitHub: label'lar va R0-01..R0-17 issue'lari (#5–#21), "📋 Kunlik hisobotlar" (#4) yaratildi
- Oxirgi tugagan tasklar: tungi run 1/2 (28-noyabr): #164 → PR #196 (A06–A10 topshiriqlari, A02 variant xatosi tuzatildi), #162 → PR #197 (shubhali holatlar, tab qaydi). 27-noyabr kunduzi: #161 → PR #190 + PR #195 (INT-02 — ball yarmiga), #192, #194 (qizil chiroq hisoboti). Tungi run 1/2 (27-noyabr): #158 → PR #188 (moslashuvchan daraja), #159 → PR #189 (challenge); #161 → PR #190 tayyor, Actions tufayli merge kutmoqda (#191). Tungi run 2/2 (26-noyabr): #157 → PR #185 (laboratoriyada Topshirish, navbat, natija), #163 → PR #186 (A01–A05 topshiriqlari, `check_lab_solutions`). Tungi run 1/2 (25-noyabr kechasi): #155 → PR #182 (Topshirish API, navbat o'rni, real vaqt holati), #156 → PR #183 (qadamlar bo'yicha natija, eng yuqori ball, o'qituvchi ko'rinishi). Tungi run 2/2 (25-noyabr): #152 → PR #179 ("Tekshirish" — brauzerda ko'rinadigan testlar), #154 → PR #180 (Celery baholash navbati, `Submission`). Tungi run 1/2 (24-noyabr): #151 → PR #176 (deterministik variant), #153 → PR #177 (sandbox image va runner). #173 → PR #174 (lokal demo: `docker compose up --build` → http://localhost:8080, `docs/learn/local-run.md`); PR #131 (Caddy CSP) egasi tomonidan merge qilingan. Custom run 11: #150 → PR #170 (topshiriq formati, `apps.grading`), #160 → PR #171 (paste cheklovi). Custom run 10: #116 → PR #148 (I2 yakuni), #149 → PR #168 (ADR-0007); I3 19 issue'ga bo'lindi (#149–#167). Custom run 9: #107 → PR #144 (M16–M22), #95 → PR #145, #115 → PR #146. Custom run 8: #105 → PR #141 (M02–M08), #106 → PR #142 (M09–M15). Custom run 7: #114 → PR #138 (datasetlar), #100 → PR #139 (vizual qadam). Custom run 6: #109 → PR #134 (notebook), #113 → PR #135 (laboratoriya sahifasi), #112 → PR #136 (avtosaqlash). Custom run 5: #108 → PR #129 (Pyodide), #104 → PR #130 (admin), #110 → PR #132 (to'xtatish); PR #131 `needs:owner`. Custom run 4/4: #102 → PR #125 (mavzu testi), #103 → PR #127 (test sahifasi). Custom run 3/4: #111 → PR #123 (avtosaqlash API), #99 → PR #124 (ma'ruza sahifalari). Custom run 2/4: #101 → PR #120 (Aiken), #98 → PR #121 (ma'ruza API). Custom run 1/4 (24-noyabr kunduzi): #71 → PR #94 (I1 yakuni), #96 → PR #117 (ADR-0006), #97 → PR #118; I2 issue'larga bo'lindi (#96–#116). Tungi run 2/2 (24-noyabr): #69 → PR #91, #70 → PR #92. Tungi run 1/2 (24-noyabr): #67 → PR #87 (+#88 `needs:owner` — Caddy `/ws/*`), #68 → PR #89. I1 custom run'lar (2026-11-23 kechqurun): #57 → PR #73, #58 → #74, #59 → #75, #60 → #76 (+#77 xavfsizlik), #61 → #78, #62 → #79, #63 → #80, #64 → #81 (14 ball); run 4: #65 → #83, #66 → #84 (4 ball). R0-15 (#19) — PR #53 va R0-16 (#20) — PR #54 (`needs:owner`, egasi merge qiladi; custom run). R0-10 (#14) — PR #48; R0-11 (#15) — PR #49 (kunduzgi run 3/3). R0-08 (#12) — PR #44; R0-09 (#13) — PR #45; R0-17 (#21) — PR #46 (kunduzgi run 2/3).
  Run 1/3: R0-06 (#10) — PR #37; R0-07 (#11) — PR #39. Run 2/2: R0-05 (#9) — PR #33; R0-13 (#17) — PR #35. Run 1/2: R0-04 (#8) — PR #28; R0-03 (#7) — PR #29; R0-14 (#18) — PR #30; R0-12 (#16) — PR #31
  (hammasi `merge-if-green.sh` bilan). Oldin: R0-01 (#5) — PR #22, R0-02 (#6) — PR #23.

## Tezlik va MVP prognozi
> Har yakshanba haftalik review to'ldiradi (`docs/prompts/weekly-review.md` 5b). Ball: M = 2, S = 1.

| Hafta | Yopilgan ball | Runlar | Qoldiq (taxmin) | MVP prognozi |
| --- | --- | --- | --- | --- |
| 2026-11-22 (boshlang'ich) | 4 (R0-01, R0-02) | 1 interaktiv | ~394 (R0 24 + R1 kodi 240 + kontent 130) | 8–10 hafta (2027 yanvar oxiri – fevral boshi) |

## Keyingi task
- I3: tayyor — #149–#164, #173. Qoldi: **#165** (kontent A11–A15), #167 (I3 yakuni), #166 (deploy, `needs:owner`).
- Egasini kutmoqda: CI daqiqalarini tejash o'zgarishlari (`claude/ci-minutes`, lokal stash; avto-rejim push'ni bloklaydi —
  egasi `!` buyrug'i bilan push qiladi, keyin `needs:owner` PR).
- #108 da `deploy/Caddyfile` CSP (`'wasm-unsafe-eval'`) va `/pyodide/` keshi — alohida `needs:owner` PR bo'ladi.
- R0: faqat serverga bog'liq qism ochiq (birinchi deploy, smoke, tiklash sinovi — `docs/learn/server.md`).

## Egasining qarorlari (2026-11-27, sessiyada)
- INT-02: noto'g'ri javobda ball **yarmiga** kamayadi (100 → 50, 40 → 20) — PR #195.
- #193: "Ruxsat: A" — Actions tiklandi (repo vaqtincha public; 1-dekabrda yana private).
- GitHub'ga pul to'lanmaydi; bepul limitdan samarali foydalanish — sifat va tezlik pasaymasligi shart (docs/CI-BUDGET.md).
- Har doim o'zbek tilida javob berish.
- Ish tartibi — **gibrid ("C")**: kechasi avtomatik tungi run'lar (har biri yangi sessiyada), kunduzi egasi haftalik
  limit sarfiga qarab 0–2 ta `/kunduzgi-run` sessiyasini boshqaradi (`docs/prompts/day-run.md`; `run:day` label'i).
  Maqsad: MVP kodi ~7–9-dekabr.

## Egasining qarorlari (2026-11-23, sessiyada)
- #38 (Hemis ID tasdiqlash): MVP uchun **A** — hozirgi oqim (o'qituvchi I1 da a'zolikni tasdiqlaydi, nizoda admin
  tuzatadi); **R3 da B** — ro'yxat + bir martalik faollashtirish kodi (#41).
- Deploy: R0 dan keyin server tayyor bo'lishini **kutmasdan R1 ga o'tiladi**. R0-15 (Dockerfile, compose.prod,
  Caddyfile) serversiz qilinadi va tekshiriladi; R0-16 dan serverga bog'liq qism (birinchi deploy, haqiqiy
  smoke test, zaxira sinovi) server tayyor bo'lganda R1 orasida bajariladi. R0 shu qism bilan ochiq qoladi.
- Monobloklar (NFR-02 sinov profili): Intel Core i5 10–12-avlod, **8 GB RAM**, Windows 10/11, **Chrome**.
  I2 dagi Pyodide laboratoriyasi shu profilda sinaladi: xotira byudjeti (brauzer tabi ~1–1,5 GB),
  paketlar soni va yuklanish vaqti shunga qarab tanlanadi; Playwright e2e — Chromium.
- Rozilik matni (SRS 7-bo'lim, Claude taklifi) **yurist tomonidan ma'qullandi** — SRS 12-bo'limdagi bu ochiq
  savol yopildi; matn o'zgarmaydi (`PRIVACY_POLICY_VERSION = 2026-11-22`).
- #34: egasi hammasi avtomatlashgan bo'lishini xohlaydi; main-guard tuzatishi egasi tomonidan qo'llanadi
  (himoyalangan fayl). Claude main-guard ogohlantirishlarini o'zi yopmaydi.

## Egasining qarorlari (2026-11-21/22, sessiyada)
- Lockout kaliti — Hemis ID + IP (#11 izohi).
- Hemis ID — 12 xonali, faqat raqam (#8 izohi).
- INT-02: tushunish savollari R1 da variantga bog'liq, oldindan tayyorlangan (I3).
- Merge (2026-11-22, "B"): oddiy PR'larni Claude `merge-if-green.sh` bilan merge qiladi; `needs:owner` PR'larni egasi.
  ("A" — hamma merge Claude'da — rad etildi: auto-mode xavfsizlik tekshiruvi o'z-o'zini merge qilishni bloklagan.)
- Run'lar: har tunda 2 ta (23:23 har kuni, 03:23 dush–shan; yakshanba 03:23 — haftalik review). Hajm: ≥ 2 M yoki 4 S.
- Egasi kunlik hisobotni o'qiydi, savollarga javob beradi va `needs:owner` PR'larni merge qiladi.
- Scheduled task'lar "MLab tungi runlar" sessiyasiga (session_016ErEP48sYh335V6WwbWk5T) xabar yuboradi:
  connector'siz trigger yangi sessiyada repo'ga kira olmaydi, shuning uchun doimiy sessiya ishlatiladi.

## Bloklar (egasining javobi kerak)
- #34 — main-guard yolg'on signali: tuzatish kodi #34 izohida; `main-guard.yml` Claude uchun taqiqlangan —
  egasi veb-muharrirda qo'llaydi va issue'ni yopadi.
- Server, domen va HTTPS — server boshqa lokal tarmoqdan ko'chirilmoqda (muddati noma'lum). Deploy shu
  tayyor bo'lgach (R1 orasida); HSTS `includeSubDomains`/preload ham domenga bog'liq.
- Sertifikatda universitet logotipidan foydalanish ruxsati (I5 gacha).
- Setup skript: sessiya boshida PostgreSQL/Redis ishlamayotgan bo'lishi mumkin — har run boshida
  `service postgresql start && service redis-server start` (yangilangan skript `docs/prompts/setup-script.sh`).

## Eslatmalar keyingi sessiya uchun
- Frontend: talaba `next` qaytishi faqat `/join/<token>` (`src/nav.ts`); vaqt ko'rinishi `src/datetime.ts` (Asia/Tashkent). Testdagi soxta token literal gitleaks beradi — `.gitleaksignore` yoki runtime'da yasash.
- WebSocket: `config/asgi.py`, `apps/sections/consumers.py` (15 daqiqa umr, a'zolik o'zgarsa `force.close`). Testda `channels.testing` emas, `asgiref.testing.ApplicationCommunicator` (daphne kerak emas).
- Frontend: QR `src/qr.ts` (ADR-0005). `userEvent.setup()` o'z clipboard'ini o'rnatadi — testda stub undan keyin.
- Topshirish holati faqat `apps/sections/policy.submission_policy` dan; qo'lda yopilgan ochiq oyna `closes_at=now` saqlaydi (kechikish/mashq uchun). Ball — `Decimal`, `apply_late_penalty`.
- Bulut sessiyasida PostgreSQL vaqti-vaqti bilan to'xtaydi — testlar `Connection refused` bersa `service postgresql start`.
- Sections: yozuvlar faqat `apps/sections/services.py` orqali; qulflar `select_for_update(no_key=True)`, tartib o'qituvchi → guruh(lar, id bo'yicha) → a'zolik (oddiy FOR UPDATE FK tekshiruvi bilan deadlock bergan). Vaqt — DB `Now()`. Talaba ishlari (I2+) talabaga bog'lanadi, guruhga emas (SEC-07: o'tkazishda saqlanadi).
- Ustma-ust (stacked) PR ochilmaydi: #54 R0-15 branch'iga merge bo'lib qolgan, #56 bilan tuzatildi. Zarur bo'lsa — pastki PR merge bo'lgach base'ni `main` ga qo'lda ko'chirish va tekshirish.
- Prod: `deploy/` (compose, Caddyfile, deploy/smoke/backup skriptlari), ADR-0004. Bulutda docker daemon yo'q: image build va `caddy validate` sinalmagan; skriptlar soxta docker bilan testlangan. Celery worker va sandbox I3 da compose'ga qo'shiladi.
- Frontend: `src/api.ts` (CSRF, `fieldErrors`), kichik router `src/router.ts` + `Link.tsx` (react-router faqat ADR bilan). E2E soxta API bilan (`e2e/auth.spec.ts`) — frontend CI job'ida backend yo'q; backend oqimi `backend/tests` da. Testda parol literali yozma: gitleaks `generic-api-key` beradi — `crypto.randomUUID()` dan yasa.
- `/policy` "Mas'ul shaxs" aloqa ma'lumoti: kafedra email'i (egasi bergan, 2026-11-23), `policy.s1.body` da.
- Ruxsatlar faqat rol bo'yicha: `apps/accounts/permissions.py` (DRF) va `admin_access.RoleAccessAdmin` (admin).
  `User.has_perm*` doim `False`, `Group` admin yo'q. Rolni o'zgartiradigan har yangi yo'l audit yozishi shart
  (hozir faqat admin `save_model` yozadi) — bitta servis funksiyasi orqali.
- Kontent: `apps/courses/content.py` (ADR-0002). Mavzuga `PROTECT` FK bor bo'lsa (kirish oynasi, keyin progress) import uni o'chirmaydi — `ContentError` bilan to'xtaydi.
- Auth: yagona login yo'li `apps/accounts/backends.py` (API + admin); lockout `lockout.py` (atomik INCR);
  IP qoidasi `net.py` (throttle, lockout, audit uchun bir xil). R0-08 da admin `password_change` → `PASSWORD_CHANGED` audit.
- OpenAPI: API o'zgarsa `cd backend && uv run python manage.py spectacular --validate --file ../docs/openapi.yaml`
  (test eskirgan faylni ushlaydi). ADR-0003 — OpenAPI; deploy ADR'i — 0004.
- Draft PR "ready" qilinganda draft paytidagi merge-gate natijasi qizil qoladi — `merge-if-green.sh` ni
  qayta ishga tushirish kerak (yangi merge-gate yashil bo'lgach o'tadi).
- SQL CHECK'da NULL: `x >= 1` NULL bo'lsa CHECK o'tib ketadi — `IS NOT NULL` aniq yoziladi (R0-09).
- Bash'da `sleep` bloklangan; merge skripti tekshiruvlarni o'zi kutadi.
- gitleaks: testda `secret = "..."` kabi nom ham `generic-api-key` beradi — o'zgaruvchiga boshqa nom va `uuid`/`secrets`.
- Foydalanuvchi API'da URL'ga chiqsa, tashqi `public_id` (UUIDv7) kerakmi — R0-05/R0-06 da hal qilinadi (schema-reviewer tavsiyasi).
- Audit: tarixi bor foydalanuvchi o'chirilmaydi (`PROTECT`), trigger UPDATE/DELETE'ni bloklaydi — ma'lumot o'chirish
  siyosati (SRS 7) kelganda alohida migratsiya.
- Loglar: `config/observability.py` — maskalash formatter'da; audit `record()` secret kalitlarni tashlaydi.
- Testlar: Faker yordamchilari `backend/tests/accounts/factories.py` (`make_user`, `make_direction`); factory_boy mypy strict bilan ishlamadi.
- Parallel PR'lar `docs/CHANGELOG.md` ning bir qatorida konflikt beradi: merge'dan oldin main'ni branch'ga merge qilish
  (force push auto-mode'da rad etiladi — rebase emas, merge).
- Run davomida Redis to'xtab qolgan (sabab noma'lum) — testdan oldin `redis-cli ping`, kerak bo'lsa `service redis-server start`.
- R0-01 da `django.contrib.admin` va loyiha migratsiyasi ataylab yo'q: custom User (R0-04) birinchi migratsiya.
  Lokal bazada `auth` migratsiyalari qo'llangan bo'lsa, R0-04 dan oldin baza qayta yaratiladi (dev/test ma'lumoti).
- `@playwright/test` bulutdagi Chromium bilan mos versiyada pin qilingan (1.63.0) — `playwright install` qilinmaydi.
- gitleaks: soxta kalitlar testlarda `secrets.token_urlsafe()` bilan yaratiladi; literal yozilmaydi.
- `scripts/merge-if-green.sh` bulutda ishlaydi: `gh auth status` "token invalid" desa ham `gh api` so'rovlari
  proxy orqali o'tadi (PR #24 shu skript bilan merge qilindi). `gh` boshqa maqsadda ishlatilmaydi.
- `UV_NATIVE_TLS` eskirgan — ogohlantirishni o'chirish uchun `UV_SYSTEM_CERTS=1` ishlatiladi.

## Tarix
| Sana | Sessiya | Natija |
| --- | --- | --- |
| 2026-11-23 | Kunduzgi run 2/3 | Yashil; R0-08 (#44), R0-09 (#45), R0-17 (#46) merge — 4 ball |
| 2026-11-23 | Kunduzgi run 1/3 | Yashil; R0-06 (#37), R0-07 (#39) merge — 4 ball |
| 2026-11-22 | Tungi run 2/2 | Yashil; R0-05 (#33), R0-13 (#35) merge — 4 ball |
| 2026-11-22 | Tungi run 1/2 | Yashil; R0-04 (#28), R0-03 (#29), R0-14 (#30), R0-12 (#31) merge — 5 ball |
| 2026-11-22 | Tayyorgarlik (chat) | SRS v2 tasdiqlandi, L1 loyiha fayllari tayyorlandi |
| 2026-11-21 | Birinchi sessiya (interaktiv) | Label'lar, issue'lar #4–#21; R0-01 → PR #22; R0-02 → PR #23; PR #24 (hujjat) skript bilan merge |
