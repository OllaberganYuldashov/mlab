# PROGRESS — L1 · MLab holati

> Faqat joriy holat (docs/prompts/nightly-run.md, 8-qadam): Sog'liq, Hozirgi holat, Keyingi task, Bloklar,
> Egasining qarorlari, Tezlik. "Oxirgi tugagan tasklar" — faqat oxirgi 3 run. Tarix — `docs/CHANGELOG.md`,
> `docs/learn/JOURNAL.md` (eski yozuvlar "Arxiv" bo'limida) va "📋 Kunlik hisobotlar" (#4).

## Sog'liq
- Holat: **Yashil** (2026-11-28, tungi run 1/2): main CI yashil, ochiq `alert:*` yo'q. Qizil chiroq (#193, Actions
  daqiqalari tugagan) 27-noyabr egasining "Ruxsat: A" bilan yopildi — repo vaqtincha public, Actions bepul.
- Oxirgi yashil nuqta: `good-2026-11-27-1024-9b595d0`
- Tuzatish urinishlari: 0
- Ochiq `alert:main-guard` / `alert:red-light`: yo'q
- Actions sarfi: repo public — bepul. 1-dekabrdan private: `scripts/actions-usage.sh` (CI-BUDGET PR egasi push qilishini kutmoqda).

## Hozirgi holat
- Reliz: **R1 — MVP, I3** (I1 va I2 yopildi 2026-11-24 — `docs/iterations/I1.md`, `I2.md`) (R0 kodi yopildi 2026-11-23; serverga bog'liq qism — birinchi deploy, smoke, tiklash sinovi — server tayyor bo'lganda)
- Oxirgi tugagan tasklar: tungi run 1/2 (28-noyabr): #164 → PR #196 (A06–A10 topshiriqlari, A02 variant xatosi tuzatildi), #162 → PR #197 (shubhali holatlar, tab qaydi). 27-noyabr kunduzi: #161 → PR #190 + PR #195 (INT-02 — ball yarmiga), #192, #194 (qizil chiroq hisoboti). Tungi run 1/2 (27-noyabr): #158 → PR #188 (moslashuvchan daraja), #159 → PR #189 (challenge); #161 → PR #190 tayyor, Actions tufayli merge kutmoqda (#191).

## Keyingi task
- I3: tayyor — #149–#164, #173. Qoldi: **#165** (kontent A11–A15), #167 (I3 yakuni), #166 (deploy, `needs:owner`).
- Egasini kutmoqda: CI daqiqalarini tejash o'zgarishlari (`claude/ci-minutes`, lokal stash; avto-rejim push'ni bloklaydi —
  egasi `!` buyrug'i bilan push qiladi, keyin `needs:owner` PR).
- #108 da `deploy/Caddyfile` CSP (`'wasm-unsafe-eval'`) va `/pyodide/` keshi — alohida `needs:owner` PR bo'ladi.
- R0: faqat serverga bog'liq qism ochiq (birinchi deploy, smoke, tiklash sinovi — `docs/learn/server.md`).

## Bloklar (egasining javobi kerak)
- #34 — main-guard yolg'on signali: tuzatish kodi #34 izohida; `main-guard.yml` Claude uchun taqiqlangan —
  egasi veb-muharrirda qo'llaydi va issue'ni yopadi.
- Server, domen va HTTPS — server boshqa lokal tarmoqdan ko'chirilmoqda (muddati noma'lum). Deploy shu
  tayyor bo'lgach (R1 orasida); HSTS `includeSubDomains`/preload ham domenga bog'liq.
- Sertifikatda universitet logotipidan foydalanish ruxsati (I5 gacha).
- Setup skript: sessiya boshida PostgreSQL/Redis ishlamayotgan bo'lishi mumkin — har run boshida
  `service postgresql start && service redis-server start` (yangilangan skript `docs/prompts/setup-script.sh`).

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

## Tezlik va MVP prognozi
> Har yakshanba haftalik review to'ldiradi (`docs/prompts/weekly-review.md` 5b). Ball: M = 2, S = 1.

| Hafta | Yopilgan ball | Runlar | Qoldiq (taxmin) | MVP prognozi |
| --- | --- | --- | --- | --- |
| 2026-11-22 (boshlang'ich) | 4 (R0-01, R0-02) | 1 interaktiv | ~394 (R0 24 + R1 kodi 240 + kontent 130) | 8–10 hafta (2027 yanvar oxiri – fevral boshi) |
