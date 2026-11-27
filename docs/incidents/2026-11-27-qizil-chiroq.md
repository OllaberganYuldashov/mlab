# Qizil chiroq — 2026-11-27: GitHub Actions job'larni ishga tushirmayapti

> Tartib: `docs/RECOVERY.md`. Issue: `alert:red-light` (shu PR tavsifida havola), oldingi xabar: #191.

## Nima bo'ldi
2026-11-26 taxminan 18:53 UTC dan boshlab **har bir** workflow job'i (`ci` backend/frontend, `secret-scan`,
`merge-gate`) 3–4 soniyada `failure` bilan tugaydi:
- birorta qadam (step) bajarilmaydi, log yo'q (API: 404), check-run `output` bo'sh;
- runner yorlig'i `ubuntu-latest` — GitHub'ning o'z runner'lari.

Dalillar:
- PR #189 tekshiruvlari 18:42 UTC da **yashil** (backend 1 daq 22 s, frontend ~10 daq) — xuddi shu commit
  (`a93b67e`) main'ga merge bo'lgach 18:53 da `ci` darhol qizil: https://github.com/OllaberganYuldashov/mlab/actions/runs/45879445055
- Qayta ishga tushirish: 1-urinish 19:00 UTC, 2-urinish 22:24 UTC — ikkalasi ham 4 s da qizil.
- Shu vaqtdan keyingi barcha PR'lar (#190, #192) ham bir xil.
- Lokal (bulut sessiyasida, main = `a93b67e`): backend **937 passed** (coverage 96.6%); #190 shoxida
  backend 950, frontend 167, e2e 48 — yashil.

## Qachondan beri
- Oxirgi yashil nuqta (teg): `good-2026-11-26-0412-78a52bc` (PR #187 dan keyin). Undan keyin merge bo'lgan
  #188 (#158) va #189 (#159) ham o'z PR tekshiruvlarida **yashil** o'tgan.
- Muammoli PR yo'q: sabab kodda emas (bisect kerak emas — bir xil commit 11 daqiqa ichida yashil va qizil).

## Sabab haqida taxmin
GitHub hisobining Actions limiti: private repo uchun oylik bepul daqiqalar tugagan yoki spending limit /
to'lov bloki (bunday holatda GitHub job'ni boshlamaydi va qadamlarsiz "failure" ko'rsatadi). Repo'da 1090+
workflow run bo'lgan; frontend e2e job'i ~10 daqiqa. Billing'ni Claude API orqali ko'ra olmaydi — tasdiqlash
egasida (Settings → Billing and plans → Actions).

## Variantlar (RECOVERY zinapoyasi) va nima yo'qoladi
| Variant | Nima qilinadi | Nima yo'qoladi | Yordam beradimi |
| --- | --- | --- | --- |
| **A. Oldinga tuzatish (tavsiya)** | Egasi Actions limitini tiklaydi: spending limit (masalan, oyiga 5–10 $) yoki 1-dekabrgacha kutish. Kod o'zgarmaydi | Hech narsa | Ha — sabab shu bo'lsa |
| A′. Self-hosted runner | Egasining kompyuterida runner; workflow'larda `runs-on` o'zgaradi (`needs:owner`) | Hech narsa; sozlash vaqti | Ha, lekin ko'proq ish |
| B–D. Revert / yashil nuqtaga qaytish | #188, #189 ni bekor qilish yoki `good-2026-11-26-0412-78a52bc` ga qaytish | #158, #159 ishi | **Yo'q** — kod sabab emas, CI baribir ishlamaydi |
| E. Zaxiradan tiklash | — | — | Kerak emas (tarix buzilmagan) |

## Tavsiya
**A**: Actions billing'ni tekshirib, limitni tiklash. Ortga qaytish (B–E) tavsiya etilmaydi.
Ruxsat/javobdan keyin: main CI qayta ishga tushiriladi; yashil bo'lsa — #190 (INT-02) va hujjat PR'lari
`scripts/merge-if-green.sh` orqali merge qilinadi, shu hisobot `docs/LESSONS.md` ga qisqa xulosa bilan yopiladi.

## Qizil holatda Claude nima qilmaydi
Yangi funksiya boshlamaydi, kodni o'zgartirmaydi, hech narsani merge qilmaydi, tekshiruvlarni chetlab o'tmaydi.
Har run boshida holatni tekshiradi va shu hisobotni yangilaydi.
