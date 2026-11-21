# BACKLOG — L1 · MLab

> Birinchi sessiyada Claude shu fayldagi R0 tasklaridan GitHub Issue'lar yaratadi
> (shablon: `.github/ISSUE_TEMPLATE/task.md`, label'lar: `status:ready`, `type:*`, `size:*`, `release:R0`).
> R1 epiklari iteratsiya boshlanishida mayda issue'larga bo'linadi. Manba: `docs/SRS.md` 9-bo'lim.

## Reliz rejasi

| Reliz | Iteratsiyalar (2 hafta) | Maqsad |
| --- | --- | --- |
| R0 — Poydevor | I0 | Xavfsiz, avtomatlashtirilgan asos: skelet, CI/CD, auth, kontent formati, server |
| R1 — MVP | I1–I5 | Bir guruh bilan to'liq semestr |
| R2 — Faollik va o'yin | 3 | Jamoaviy estafeta, mastery, playback, RAG, tahlil |
| R3 — Kengayish | 3 | Google kirish, email, rus tili, kontent muharriri, 250 foydalanuvchi |
| R4 — Ilg'or ML va mahsulot | — | TF.js CNN/RNN, pullik AI, bir nechta OTM |

## R0 — Poydevor (I0)

Tartib bog'liqlik bo'yicha. Har task bitta tungi run'ga sig'adi; sig'masa run uni bo'ladi.

| # | Task | Talablar | Hajm | Qabul mezoni (qisqa) |
| --- | --- | --- | --- | --- |
| R0-01 | Backend skeleti: Django 5 loyihasi `backend/`, `config/settings/{base,dev,test,prod}.py`, env'dan sozlama va fail-fast, `/healthz`, ruff, mypy, pytest; CI workflow `ci` (backend job, PostgreSQL va Redis service containers) | NFR-16, NFR-17 | M | `ci` yashil; sozlama yo'q bo'lsa ilova ishga tushmaydi (test bilan) |
| R0-02 | Frontend skeleti: Vite + React + TS `frontend/`, ESLint, Vitest, Playwright bitta smoke test, `uz.json` i18n; `ci` ga frontend job; setup skriptga Playwright brauzeri | NFR-14, NFR-15 | M | `npm test`, `npm run lint`, `typecheck` CI'da yashil |
| R0-03 | `compose.yaml` (PostgreSQL 16, Redis 7) va `docs/learn/docker.md` | — | S | `docker compose up -d db redis` bilan testlar o'tadi |
| R0-04 | Custom User modeli (Hemis ID login, FIO, yo'nalish, rol), Argon2, birinchi migratsiya. **Boshqa migratsiyalardan oldin** | AUTH-01, AUTH-03 | M | Argon2 xesh testi; Hemis ID unikal (case-insensitive) |
| R0-05 | Rollar va ruxsatlar asosi (super admin, admin, instructor, student), DRF permission sinflari, Django Admin | 2.2 | M | Har rol uchun ruxsat matritsasi testi |
| R0-06 | Ro'yxatdan o'tish API + rozilik (siyosat versiyasi va vaqti saqlanadi), yo'nalishlar ro'yxati | AUTH-01, 7-bo'lim | M | Roziliksiz ro'yxatdan o'tish rad etiladi |
| R0-07 | Kirish va chiqish (session + CSRF), 5 urinish → 15 daqiqa blok | AUTH-02 | M | Lockout testi; xato xabari foydalanuvchi bor-yo'qligini oshkor qilmaydi |
| R0-08 | Parolni tiklash: bir martalik vaqtinchalik parol, birinchi kirishda majburiy almashtirish, audit | AUTH-04, ADM-02 | M | O'qituvchi faqat o'z guruhi talabasini tiklaydi; parol hech qayerda ko'rinmaydi |
| R0-09 | Admin o'qituvchi akkauntini yaratadi va talaba limitini belgilaydi | AUTH-05, SEC-08 | S | Limitdan oshganda rad |
| R0-10 | Frontend: kirish, ro'yxatdan o'tish, rozilik, parol almashtirish sahifalari | AUTH-01..04 | M | Playwright: ro'yxatdan o'tish → kirish |
| R0-11 | Foydalanish va maxfiylik siyosati sahifalari (SRS 7-bo'lim matni) | 7-bo'lim | S | Ro'yxatdan o'tish formasidan havola |
| R0-12 | AuditLog modeli va yozish yordamchisi | ADM-02 | S | Rol va parol tiklash hodisalari yoziladi |
| R0-13 | Kontent formati ADR-0002 va `import_content` buyrug'i: Course, Topic, Lecture, Step; namuna `content/topics/M01` | CNT-01 | M | Import idempotent; noto'g'ri YAML aniq xato bilan |
| R0-14 | Strukturali JSON loglar, request id, `/readyz` (DB va Redis), loglarda Hemis ID va IP maskalash | NFR-17, SECURITY | S | Log testida maxfiy maydonlar yo'q |
| R0-15 | Prod: Dockerfile'lar (backend, frontend build → Caddy), `deploy/compose.prod.yaml`, `Caddyfile`; deploy usuli ADR-0003 (SSH yoki self-hosted runner) | NFR-08 | M | `docker compose -f deploy/compose.prod.yaml config` toza; image'lar root'siz |
| R0-16 | Deploy workflow + smoke test; kunlik `pg_dump` zaxira skripti va tiklash yo'riqnomasi `docs/learn/server.md` | ADM-04, NFR-08 | M | Egasi serverda yo'riqnoma bo'yicha birinchi deploy qiladi |
| R0-17 | Darslar: `docs/learn/django.md`, `drf.md`, `react-typescript.md`, `caddy.md`, `celery-channels.md` | — | S | Har dars: nima, nega, qanday ishlaydi, mashq |

## R1 — MVP epiklari

| Iteratsiya | Epik | Talablar |
| --- | --- | --- |
| I1 | Guruhlar, qo'shilish havolasi va QR, a'zolik so'rovlari va tasdiq | SEC-01..08 |
| I1 | Guruh sozlamalari (ikki darajali) | SET-01..05 |
| I1 | Kirish oynalari: rejimlar, jadval, takroriy slot, yopilganda saqlash, kechikish, nazorat rejimi, real vaqt xabari | ACC-01..11 |
| I2 | Kontent: 22 ma'ruza qadamlari (minimal), interaktiv vizual qadam, Aiken importi, mavzu testlari | CNT-02..07 |
| I2 | Laboratoriya: notebook, Pyodide worker, paketlar o'z serverdan, `mlab.load()`, avtosaqlash, to'xtatish | LAB-01..07 |
| I2 | Datasetlar va litsenziyalar | DAT-01..03 |
| I2 | Monoblokda erta sinov (NFR-02) | NFR-02 |
| I3 | Avtobaholovchi: ko'rinadigan testlar, sandbox image, navbat, natija | AGR-01..06 |
| I3 | A1–A15 topshiriqlari: umumiy, 3 daraja × 5 variant, challenge, mustaqil; deterministik variantlar | AGR-07..08 |
| I3 | Moslashuvchan daraja va challenge | ADP-01..03 |
| I3 | Akademik halollik: paste cheklovi, tushunish savollari, belgilar, tab qaydi | INT-01..05 |
| I4 | Jonli monitoring paneli, plitkalar, jonli kod, yordam navbati, shaxsiy xabar, guruh grafigi | MON-01..07 |
| I4 | Guruh chati, moderatsiya, e'lonlar | COM-01..03 |
| I4 | Ustoz-AI: rejimlar, cheklovlar, proksi, limitlar, log, provayder qatlami | AI-01..07 |
| I4 | A15 uchun stlite | LAB-08 |
| I5 | Baholash: 100 ball, faollik, tavsiya ball va tasdiq, jurnal va Excel | GRD-01..04 |
| I5 | Sertifikat, QR, tekshirish sahifasi, bekor qilish | GRD-05..07 |
| I5 | Hisobotlar, faollik hodisalari, "Mening ma'lumotlarim" | RPT-01..03, RPT-05 |
| I5 | Tizim holati, kunlik zaxira va tiklash sinovi | ADM-01, ADM-03, ADM-04 |
| I5 | Yuklama va xavfsizlik sinovlari, kompyuter xonasida sinov darsi, MVP qabul mezonlari | SRS 10-bo'lim |

## Kontent tasklari (har iteratsiyada parallel, `type:content`)

Ma'ruzalar M01–M22 va amaliy A1–A15 ro'yxati: `content/README.md`. Kontent kod bilan bir xil tartibda:
bitta mavzu — bitta issue — bitta PR, testlar (sxema, variantlar soni, namunaviy yechimlar) bilan.
