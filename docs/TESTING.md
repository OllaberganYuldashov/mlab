# TESTING — L1 · MLab test strategiyasi

> Manba: `docs/SRS.md` 10-bo'lim. Har test nomida talab ID'si bo'ladi (`test_acc_06_autosave_on_close`).

## Test darajalari va vositalar

| Daraja | Nima | Vosita | Qayerda |
| --- | --- | --- | --- |
| Unit | Ball hisobi, daraja tanlash, kirish oynalari, ruxsatlar, variant deterministikligi | pytest, Vitest | Bulut sessiyasi, CI |
| Integration | API, PostgreSQL, Redis, Celery (eager emas — haqiqiy worker test rejimida), WebSocket | pytest-django, channels testing | Bulut sessiyasi, CI service containers |
| Avtobaholovchi | Har variant uchun namunaviy to'g'ri va noto'g'ri yechim: to'g'risi 100%, noto'g'risi < 100% | pytest + sandbox image | CI |
| Kontent | `content/` sxemasi, havolalar, Aiken fayllari, variantlar soni (A1–A15 × 3 × 5) | pytest | CI |
| E2E | Ro'yxatdan o'tish → guruh → oyna → topshirish → ball; o'qituvchi monitoringi | Playwright | CI |
| Yuklama | 100 bir vaqtdagi talaba, NFR-01..04 | k6 yoki Locust | Reliz oxirida, staging |
| Xavfsizlik | Sandbox chiqishi, IDOR, XSS, secret oqishi | Qo'lda sinov + security-reviewer, gitleaks, pip-audit | Har reliz |
| Foydalanuvchi | Kompyuter xonasida sinov darsi | So'rovnoma | I5 |

## Secret'larsiz test qilish qoidasi

- Testlar hech qachon haqiqiy parol yoki tokenga bog'liq emas; `APP_ENV=test`, `AI_PROVIDER=fake`.
- Gemini doim `fake` provayder bilan; haqiqiy chaqiruv faqat deploy'dan keyingi smoke testda.
- Pyodide frontend unit testlarida mock worker bilan; haqiqiy Pyodide faqat Playwright testida.
- Ilova ishga tushganda majburiy sozlamalar yo'qligini darhol aniqlaydi (fail fast) — buning testi bor.

## Muhim invariantlar (har biri alohida test)

- Yopiq oynada rasmiy topshirish rad etiladi (ACC-06), kechikish muddatida "kechikkan" belgisi (ACC-07).
- Talaba bir vaqtda bitta faol guruhda (SEC-07).
- Topshiriq AI rejimi guruh chegarasidan oshmaydi (SET-01).
- Eng yuqori urinish ball hisoblanadi (AGR-06); noto'g'ri tushunish javobi ballni 50% bilan cheklaydi (INT-02).
- Variant talaba ID bo'yicha deterministik (AGR-08).
- Yashirin test tarkibi hech bir API javobida yo'q (AGR-05).
- Sertifikat faqat tasdiqlangan 90+ ballda (GRD-05); tekshirish sahifasida Hemis ID yo'q (GRD-06).
- Gemini so'rovida FIO va Hemis ID yo'q (AI-04).

## Coverage

- Eng past chegara: 85% (backend va frontend alohida). Reliz oxirida mutation testing (`grading`, `sections`, `accounts`).
