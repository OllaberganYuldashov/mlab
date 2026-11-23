# JOURNAL — har run yozuvi

> Har run oxirida Claude qo'shadi. Eng yangisi yuqorida.

### 2026-11-23 — custom run (R0 ni yopish)
- **Bajarilgan issue'lar va PR:** R0-15 (#19) → PR #53; R0-16 (#20) → PR #54. Ikkalasi `needs:owner` (egasi merge qiladi).
- **Nima qilindi (oddiy tilda):** Platformani serverda ishga tushirish uchun hamma narsa tayyorlandi: konteyner
  "retseptlari", eshik (Caddy), deploy skripti, kunlik zaxira va tiklash, hamda egasi uchun qadamma-qadam yo'riqnoma.
  Server yo'q bo'lgani uchun skriptlar soxta docker bilan sinaldi.
- **Ishlatilgan skill'lar va nima uchun:** docker-build-strategies va docker-compose-patterns (root'siz image, RAM limiti),
  docker-destructive-guardrails (tiklash `--yes` talab qiladi, oldin joriy holat saqlanadi), security-discipline
  (secret faqat serverdagi .env, workflow'da injection yo'q), idempotency-and-side-effects (takroriy deploy xavfsiz).
- **Yangi texnologiya / tushuncha:** `docs/learn/server.md`, `docs/learn/caddy.md`, ADR-0004 (uvicorn, deploy usuli).
- **Ertalab nimani ko'rish kerak:** PR #53 → merge, keyin #54. Kompyuteringizda `docker compose -f deploy/compose.prod.yaml --env-file <sinov env> build`.
- **Savollar / bloklar:** deploy usuli (self-hosted runner yoki SSH); zaxirani boshqa joyga nusxalash.

### 2026-11-23 — kunduzgi run 3/3 (navbatdan tashqari)
- **Bajarilgan issue'lar va PR:** R0-10 (#14) → PR #48; R0-11 (#15) → PR #49 (ikkalasi `merge-if-green.sh` bilan). 3 ball.
- **Nima qilindi (oddiy tilda):** Talaba brauzerda ro'yxatdan o'ta, kira, parolini almashtira oladi (rozilik matni va
  siyosat sahifasi bilan). Backend'ga siyosat versiyasini beruvchi kichik endpoint qo'shildi.
- **Ishlatilgan skill'lar va nima uchun:** testing-with-discernment (brauzer oqimi e2e, soxta API chegarasi aniq yozildi),
  security-discipline + security-reviewer (logout xatosi va majburiy parol almashtirish tuzatildi; Hemis ID band xabari
  ma'lum xavf sifatida SECURITY.md ga yozildi).
- **Yangi texnologiya / tushuncha:** `docs/learn/react-typescript.md` (kirish sahifalari bo'limi).
- **Ertalab nimani ko'rish kerak:** ro'yxatdan o'tish formasi va `/policy` (lokal `npm run dev`); #34 tuzatishini qo'llash.
- **Savollar / bloklar:** siyosatdagi "Mas'ul shaxs" uchun aloqa ma'lumoti kerak (PROGRESS).

### 2026-11-23 — kunduzgi run 2/3 (navbatdan tashqari)
- **Bajarilgan issue'lar va PR:** R0-08 #12 → PR #44; R0-09 #13 → PR #45; R0-17 #21 → PR #46 (4 ball: M + 2 S).
- **Nima qilindi (oddiy tilda):** Parolni tiklash (bir martalik, 24 soatlik vaqtinchalik parol; talaba yangisini
  qo'ymaguncha hech narsa ochilmaydi), admin o'qituvchi akkauntini yaratadi va talaba limitini belgilaydi,
  DRF, Caddy, Celery/Channels darslari.
- **Ishlatilgan skill'lar va nima uchun:** auth-and-authorization (kim kimni tiklaydi — `policies.py`, fail closed),
  data-modeling-discipline (NULL-xavfsiz CHECK — test xatoni topdi), security-reviewer ikki marta (qator qulfi,
  vaqtinchalik parol muddati, audit atomikligi, cheklovlar).
- **Yangi texnologiya / tushuncha:** `docs/learn/drf.md`, `caddy.md`, `celery-channels.md`.
- **Ertalab nimani ko'rish kerak:** `backend/apps/accounts/policies.py` (SRS 2.2 ga mosligi).
- **Savollar / bloklar:** yangi yo'q.

### 2026-11-23 — kunduzgi run 1/3 (navbatdan tashqari)
- **Bajarilgan issue'lar va PR:** R0-06 #10 → PR #37; R0-07 #11 → PR #39 (4 ball: 2 M). Skript bilan merge.
- **Nima qilindi (oddiy tilda):** Talaba ro'yxatdan o'tishi (rozilik bilan) va kirish/chiqish API'si tayyor.
  5 marta xato paroldan keyin 15 daqiqa blok — ham saytda, ham admin panelda. API "pasporti" (`docs/openapi.yaml`).
- **Ishlatilgan skill'lar va nima uchun:** auth-and-authorization, security-discipline, parse-dont-validate,
  clocks-and-time (soxta soat bilan blok muddati). security-reviewer ikki marta: muhim topilma — parallel so'rovlar
  bilan blokni aylanib o'tish (atomik hisoblagich bilan tuzatildi) va admin login'da IP chegarasi yo'qligi.
- **Yangi texnologiya / tushuncha:** drf-spectacular (ADR-0003) — `docs/learn/openapi.md`; `docs/learn/sessions-csrf.md`.
- **Ertalab nimani ko'rish kerak:** #38 (Hemis ID tasdiqlash — qaror), #34 (main-guard yolg'on signal).
- **Savollar / bloklar:** #38.

### 2026-11-22 — tungi run 2/2
- **Bajarilgan issue'lar va PR:** R0-05 #9 → PR #33; R0-13 #17 → PR #35 (4 ball: 2 M). Skript bilan merge.
- **Nima qilindi (oddiy tilda):** Har rol uchun ruxsat "qulflari" va `/admin/` boshqaruv paneli: unga faqat super
  admin va admin kiradi, parol xeshi ko'rinmaydi, rol o'zgarishi jurnalga yoziladi. Kurs kontenti formati (ADR-0002)
  va `import_content` buyrug'i: fayllardagi ma'ruzalar bazaga xavfsiz va takrorlansa ham bir xil natija bilan yuklanadi.
- **Ishlatilgan skill'lar va nima uchun:** auth-and-authorization (rol va obyekt darajasi ajratildi),
  security-reviewer agenti (Group admin va Django perm'lari orqali aylanib o'tish, o'zini pasaytirish, faollik auditi —
  tuzatildi), idempotency-and-side-effects (upsert tabiiy kalit bo'yicha), error-handling-as-design (`fayl:qator`).
- **Yangi texnologiya / tushuncha:** PyYAML — `docs/learn/content-format.md`; `docs/learn/roles-permissions.md`.
- **Ertalab nimani ko'rish kerak:** `.gitleaksignore` ga yangi qator (PR #35) — test markeri, secret emas.
- **Savollar / bloklar:** yo'q.

### 2026-11-22 — tungi run 1/2
- **Bajarilgan issue'lar va PR:** R0-04 #8 → PR #28; R0-03 #7 → PR #29; R0-14 #18 → PR #30; R0-12 #16 → PR #31.
  Hammasi `merge-if-green.sh` bilan merge qilindi (5 ball: 1 M + 3 S).
- **Nima qilindi (oddiy tilda):** Foydalanuvchi modeli (login — Hemis ID, parol Argon2) va loyihaning birinchi
  migratsiyasi; kompyuteringiz uchun `compose.yaml`; JSON loglar (shaxsiy ma'lumot yashiriladi) va `/readyz`;
  o'zgartirib ham, o'chirib ham bo'lmaydigan audit jurnali.
- **Ishlatilgan skill'lar va nima uchun:** data-modeling-discipline (qoidalar bazada CHECK/trigger bilan),
  migration-safety (har migratsiya `zero` gacha qaytarib sinaldi), unicode-pitfalls (oʻ/gʻ va apostrof
  variantlari, NFC), observability-by-default (liveness/readiness ajratildi, health probe shovqini o'chirildi),
  docker-compose-patterns. `schema-reviewer` agenti User sxemasida 4 ta tuzatish topdi — kiritildi.
- **Yangi texnologiya / tushuncha:** `docs/learn/custom-user-argon2.md`, `docs/learn/docker.md`, `docs/learn/observability.md`.
- **Ertalab nimani ko'rish kerak:** kompyuteringizda `docker compose up -d db redis` → `docker compose ps` (healthy).
- **Savollar / bloklar:** yangi blok yo'q (PROGRESS'dagi eski savollar o'z kuchida).

### 2026-11-21 — interaktiv (birinchi sessiya)
- **Bajarilgan issue'lar va PR:** label'lar; issue'lar #5–#21 (R0-01..R0-17), #4 (kunlik hisobotlar);
  R0-01 (#5) → PR #22; R0-02 (#6) → PR #23. Ikkalasi `needs:owner`.
- **Nima qilindi (oddiy tilda):** Backend (Django) va frontend (React) uchun bo'sh, lekin to'liq
  sozlangan "skelet" qurildi: testlar, lint, turlar tekshiruvi va GitHub'dagi `ci` avtomatik tekshiruvi.
  Backend kerakli sozlamasiz ishga tushmaydi (fail fast). Frontend'dagi hamma matn `uz.json` faylida.
- **Ishlatilgan skill'lar va nima uchun:** think-before-coding (oldin dizayn: liveness va readiness
  ajratildi), testing-with-discernment (fail fast mock bilan emas, haqiqiy alohida jarayonda tekshirildi),
  security-discipline (prod'da zaif kalit va `*` host taqiqlandi; pip-audit DRF zaifligini topdi → 3.18).
- **Yangi texnologiya / tushuncha:** `docs/learn/django.md`, `docs/learn/react-typescript.md`.
- **Ertalab nimani ko'rish kerak:** PR #22 (ci.yml, CLAUDE.md §4, `.gitleaksignore`) → merge; keyin #23.
  Setup skriptni muhitga qo'yish (`docs/prompts/setup-script.sh`, #23 dagi versiya).
- **Savollar / bloklar:** yo'q. (Avval `merge-if-green.sh` bulutda ishlamaydi deb o'ylangan edi — noto'g'ri:
  `gh auth status` xato ko'rsatsa ham `gh api` proxy orqali ishlaydi; PR #24 skript bilan merge qilindi.)

## Shablon

### YYYY-MM-DD — <run turi: tungi / interaktiv / review>
- **Bajarilgan issue'lar va PR:** #...
- **Nima qilindi (oddiy tilda):**
- **Ishlatilgan skill'lar va nima uchun:**
- **Yangi texnologiya / tushuncha:** (dars havolasi)
- **Ertalab nimani ko'rish kerak:**
- **Savollar / bloklar:**
