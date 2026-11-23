# PROGRESS — L1 · MLab holati

> Har sessiya oxirida Claude yangilaydi. Yangi sessiya ishni shu fayldan davom ettiradi.

## Sog'liq
- Holat: **Yashil** (2026-11-23, kunduzgi run 1/3 boshida va oxirida): main `ci` yashil, backend 220 → 296 test,
  frontend 8 test; bug va rad etilgan PR yo'q. `alert:main-guard` #34 — yolg'on signal (PR #33 commit'lari),
  izoh yozildi; yopish egasida.
- Oxirgi yashil nuqta: `good-2026-11-22-2341-4e4f41c` (PR #31 dan keyingisi `known-good` tomonidan qo'yiladi)
- Tuzatish urinishlari: 0
- Ochiq `alert:main-guard` / `alert:red-light`: yo'q

## Hozirgi holat
- Reliz: R0 — Poydevor (I0)
- TZ: SRS v2 tasdiqlangan → `docs/SRS.md`
- GitHub: label'lar va R0-01..R0-17 issue'lari (#5–#21), "📋 Kunlik hisobotlar" (#4) yaratildi
- Oxirgi tugagan tasklar: R0-06 (#10) — PR #37; R0-07 (#11) — PR #39 (kunduzgi run 1/3). Run 2/2: R0-05 (#9) — PR #33; R0-13 (#17) — PR #35. Run 1/2: R0-04 (#8) — PR #28; R0-03 (#7) — PR #29; R0-14 (#18) — PR #30; R0-12 (#16) — PR #31
  (hammasi `merge-if-green.sh` bilan). Oldin: R0-01 (#5) — PR #22, R0-02 (#6) — PR #23.

## Tezlik va MVP prognozi
> Har yakshanba haftalik review to'ldiradi (`docs/prompts/weekly-review.md` 5b). Ball: M = 2, S = 1.

| Hafta | Yopilgan ball | Runlar | Qoldiq (taxmin) | MVP prognozi |
| --- | --- | --- | --- | --- |
| 2026-11-22 (boshlang'ich) | 4 (R0-01, R0-02) | 1 interaktiv | ~394 (R0 24 + R1 kodi 240 + kontent 130) | 8–10 hafta (2027 yanvar oxiri – fevral boshi) |

## Keyingi task
- Tayyor (bog'liqligi yopilgan): R0-08 (#12), R0-09 (#13), R0-10 (#14), R0-11 (#15), R0-17 (#21), R0-15 (#19, ADR-0004).

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
- Ruxsatlar faqat rol bo'yicha: `apps/accounts/permissions.py` (DRF) va `admin_access.RoleAccessAdmin` (admin).
  `User.has_perm*` doim `False`, `Group` admin yo'q. Rolni o'zgartiradigan har yangi yo'l audit yozishi shart
  (hozir faqat admin `save_model` yozadi) — bitta servis funksiyasi orqali.
- Kontent: `apps/courses/content.py` (ADR-0002). Mavzu fayldan o'chsa bazadan ham o'chadi — R1 da progress FK
  qo'shilganda `PROTECT` + aniq xato.
- Auth: yagona login yo'li `apps/accounts/backends.py` (API + admin); lockout `lockout.py` (atomik INCR);
  IP qoidasi `net.py` (throttle, lockout, audit uchun bir xil). R0-08 da admin `password_change` → `PASSWORD_CHANGED` audit.
- OpenAPI: API o'zgarsa `cd backend && uv run python manage.py spectacular --validate --file ../docs/openapi.yaml`
  (test eskirgan faylni ushlaydi). ADR-0003 — OpenAPI; deploy ADR'i — 0004.
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
| 2026-11-23 | Kunduzgi run 1/3 | Yashil; R0-06 (#37), R0-07 (#39) merge — 4 ball |
| 2026-11-22 | Tungi run 2/2 | Yashil; R0-05 (#33), R0-13 (#35) merge — 4 ball |
| 2026-11-22 | Tungi run 1/2 | Yashil; R0-04 (#28), R0-03 (#29), R0-14 (#30), R0-12 (#31) merge — 5 ball |
| 2026-11-22 | Tayyorgarlik (chat) | SRS v2 tasdiqlandi, L1 loyiha fayllari tayyorlandi |
| 2026-11-21 | Birinchi sessiya (interaktiv) | Label'lar, issue'lar #4–#21; R0-01 → PR #22; R0-02 → PR #23; PR #24 (hujjat) skript bilan merge |
