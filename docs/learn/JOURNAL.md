# JOURNAL — har run yozuvi

> Har run oxirida Claude qo'shadi. Eng yangisi yuqorida.

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
