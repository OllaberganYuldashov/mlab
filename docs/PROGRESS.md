# PROGRESS — L1 · MLab holati

> Har sessiya oxirida Claude yangilaydi. Yangi sessiya ishni shu fayldan davom ettiradi.

## Sog'liq
- Holat: **Yashil** (2026-11-22). main'da backend va frontend skeleti, `ci` yashil.
- Oxirgi yashil nuqta: `good-2026-11-22-0850-0944fc9`
- Tuzatish urinishlari: 0
- Ochiq `alert:main-guard` / `alert:red-light`: yo'q

## Hozirgi holat
- Reliz: R0 — Poydevor (I0)
- TZ: SRS v2 tasdiqlangan → `docs/SRS.md`
- GitHub: label'lar va R0-01..R0-17 issue'lari (#5–#21), "📋 Kunlik hisobotlar" (#4) yaratildi
- Oxirgi tugagan tasklar: R0-01 (#5) — PR #22 (egasi merge qildi); R0-02 (#6) — PR #23 (Claude merge qildi, egasining ruxsati bilan)

## Tezlik va MVP prognozi
> Har yakshanba haftalik review to'ldiradi (`docs/prompts/weekly-review.md` 5b). Ball: M = 2, S = 1.

| Hafta | Yopilgan ball | Runlar | Qoldiq (taxmin) | MVP prognozi |
| --- | --- | --- | --- | --- |
| 2026-11-22 (boshlang'ich) | 4 (R0-01, R0-02) | 1 interaktiv | ~394 (R0 24 + R1 kodi 240 + kontent 130) | 8–10 hafta (2027 yanvar oxiri – fevral boshi) |

## Keyingi task
- Tayyor (bog'liqligi yopilgan): R0-03 (#7), R0-04 (#8, custom User — birinchi migratsiya, birinchi bo'lib olinsin), R0-14 (#18).
- R0-04 dan keyin: R0-05 (#9), R0-12 (#16), R0-13 (#17).

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
- Setup skript: sessiya boshida PostgreSQL/Redis ishlamayotgan va `mlab` foydalanuvchisi yo'q edi — muhitdagi
  setup skript qo'yilmagan bo'lishi mumkin. Yangilangan skript PR #23 da (`docs/prompts/setup-script.sh`).
- SRS 12-bo'lim ochiq savollari: monobloklar parametrlari (I2 gacha), domen va HTTPS (R0-15/R0-16 gacha;
  HSTS `includeSubDomains`/preload ham shunga bog'liq), rozilik matni yurist bilan (R1 oxirigacha),
  sertifikatda logotip ruxsati (I5 gacha).

## Eslatmalar keyingi sessiya uchun
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
| 2026-11-22 | Tayyorgarlik (chat) | SRS v2 tasdiqlandi, L1 loyiha fayllari tayyorlandi |
| 2026-11-21 | Birinchi sessiya (interaktiv) | Label'lar, issue'lar #4–#21; R0-01 → PR #22; R0-02 → PR #23; PR #24 (hujjat) skript bilan merge |
