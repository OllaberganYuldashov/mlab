# CODEMAP — kod xaritasi

> Avtomatik: `python3 scripts/codemap.py`. Qo'lda tahrirlanmaydi. Har qator — fayl izohining birinchi qatori.
> Run boshida kerakli faylni shu yerdan toping va faqat o'shani o'qing (docs/prompts/nightly-run.md).

## backend/apps/accounts

- `backend/apps/accounts/admin.py` — Django Admin: foydalanuvchilar va yo'nalishlar (R0-05, SRS 2.2).
- `backend/apps/accounts/admin_access.py` — Django Admin'da rolga asoslangan kirish (SRS 2.2).
- `backend/apps/accounts/apps.py`
- `backend/apps/accounts/backends.py` — Yagona autentifikatsiya backend'i: API va Django Admin login'i shu yerdan o'tadi (lockout).
- `backend/apps/accounts/limits.py` — SEC-08: o'qituvchi bo'yicha umumiy talaba limiti (I1 guruhlari a'zolikni tasdiqlashdan oldin).
- `backend/apps/accounts/lockout.py` — AUTH-02: 5 ta xato urinish → 15 daqiqa blok. Kalit — Hemis ID + IP (egasining qarori, #11).
- `backend/apps/accounts/middleware.py` — AUTH-04: vaqtinchalik parol bilan kirgan foydalanuvchi parolni almashtirmaguncha boshqa
- `backend/apps/accounts/models.py` — Foydalanuvchi va yo'nalish (AUTH-01, AUTH-03; SRS 2.2 rollar).
- `backend/apps/accounts/net.py` — Mijoz IP manzilini aniqlash (Caddy ortida — `X-Forwarded-For`, `TRUSTED_PROXY_COUNT`).
- `backend/apps/accounts/permissions.py` — Rolga asoslangan DRF ruxsatlari (SRS 2.2).
- `backend/apps/accounts/policies.py` — Obyekt darajasidagi qoidalar (CLAUDE.md 5.6): kim kimning parolini tiklaydi (AUTH-04, SRS 2.2).
- `backend/apps/accounts/serializers.py` — Ro'yxatdan o'tish (AUTH-01) va yo'nalishlar ro'yxati serializer'lari.
- `backend/apps/accounts/signals.py` — Kirish hodisalari audit jurnaliga (ADM-02): API va Django Admin login'i uchun bir xil.
- `backend/apps/accounts/urls.py`
- `backend/apps/accounts/views.py` — Ochiq (autentifikatsiyasiz) accounts endpoint'lari — har biri aniq `AllowAny` (CLAUDE.md 5.6).

## backend/apps/audit

- `backend/apps/audit/admin.py` — Django Admin: audit jurnali — faqat super admin ko'radi (SRS 2.2), hech kim o'zgartirmaydi.
- `backend/apps/audit/apps.py`
- `backend/apps/audit/models.py` — Audit jurnali (ADM-02): kim, nima, qachon, qaysi obyekt, oldingi va yangi qiymat.

## backend/apps/courses

- `backend/apps/courses/admin.py` — Django Admin: kurs kontenti (I2-09; CNT-07, ADM-02).
- `backend/apps/courses/aiken.py` — Aiken formatidagi test fayllarini o'qish (CNT-05). Sof funksiya — bazaga tegmaydi.
- `backend/apps/courses/apps.py`
- `backend/apps/courses/content.py` — `content/` papkasini o'qish, tekshirish va bazaga yuklash (CNT-01, ADR-0002).
- `backend/apps/courses/management/commands/import_content.py` — `manage.py import_content <papka>` — kurs kontentini bazaga yuklaydi (CNT-01, ADR-0002).
- `backend/apps/courses/models.py` — Kurs kontenti (CNT-01, ADR-0002): Course → Topic → Lecture → LectureStep.
- `backend/apps/courses/quiz.py` — Mavzu testi (I2-07; CNT-06): urinish boshlash, topshirish, muddati o'tganini yakunlash.
- `backend/apps/courses/quiz_views.py` — Mavzu testi API (I2-07; CNT-06). Faqat kursga a'zo talaba; boshqa talabaning urinishi — 404.
- `backend/apps/courses/urls.py`
- `backend/apps/courses/views.py` — Ma'ruza API (I2-03; CNT-02, ACC-01, SEC-05).

## backend/apps/grading

- `backend/apps/grading/apps.py`
- `backend/apps/grading/content.py` — `content/labs/` — amaliy topshiriqlar importi (AGR-07, AGR-05; I3-02).
- `backend/apps/grading/levels.py` — Moslashuvchan daraja (I3-10; ADP-01).
- `backend/apps/grading/management/commands/check_lab_solutions.py` — `manage.py check_lab_solutions ../content --python <venv python>` yoki `--docker <image>`.
- `backend/apps/grading/models.py` — Amaliy topshiriqlar (AGR-07; I3-02). Manba — `content/labs/<A##>-<slug>/`.
- `backend/apps/grading/results.py` — Talabaga ko'rsatiladigan natija (I3-08; AGR-05, AGR-06).
- `backend/apps/grading/sandbox.py` — Sandbox chaqiruvi interfeysi (ADR-0007; AGR-03, I3-06).
- `backend/apps/grading/service.py` — Baholash navbati (I3-06; AGR-02, AGR-04, AGR-06; ADR-0007).
- `backend/apps/grading/solutions.py` — Kontent yechimlari tekshiruvi (I3-15; AGR-07): har variantda yechim barcha testlardan o'tadimi.
- `backend/apps/grading/tasks.py` — Celery vazifalari (I3-06; AGR-04).
- `backend/apps/grading/urls.py`
- `backend/apps/grading/variants.py` — Deterministik variant tanlash (AGR-08, INT-03; I3-03).
- `backend/apps/grading/views.py` — Talabaning topshirig'i (I3-04; AGR-01, AGR-05, LAB-07).

## backend/apps/labs

- `backend/apps/labs/apps.py`
- `backend/apps/labs/integrity.py` — Shubhali holatlar (I3-14; INT-04, INT-05, ACC-09).
- `backend/apps/labs/models.py` — Laboratoriya ishi (LAB-05): talaba x guruh x mavzu uchun bitta yozuv.
- `backend/apps/labs/notebook.py` — Notebook holatining shakli (LAB-01, LAB-05).
- `backend/apps/labs/urls.py`
- `backend/apps/labs/views.py` — Laboratoriya ishi API (I2-16; LAB-05, ACC-06).

## backend/apps/sections

- `backend/apps/sections/access.py` — Kursga kirish (SEC-05): tasdiqlangan a'zo kursga avtomatik yozilgan — alohida obuna yo'q.
- `backend/apps/sections/apps.py`
- `backend/apps/sections/consumers.py` — Talabaning WebSocket ulanishi (ACC-05). Faqat serverdan xabar; mijoz yozgani o'qilmaydi.
- `backend/apps/sections/deadline_views.py` — Mustaqil topshiriq muddatlari API (I1-10; ACC-10). Begona guruh — 404, talaba — 403.
- `backend/apps/sections/join_views.py` — Havola orqali qo'shilish (I1-04; SEC-03, SEC-06, SEC-07) va talabaning a'zolik holati.
- `backend/apps/sections/management/commands/seed_demo.py` — Lokal demo ma'lumot (#173): `docker compose up` dan keyin darhol kirib ko'rish uchun.
- `backend/apps/sections/member_views.py` — A'zolar ro'yxati va qaror (I1-05; SEC-04, SEC-06, SEC-08).
- `backend/apps/sections/models.py` — Guruhlar va a'zolik (SEC, I1-01).
- `backend/apps/sections/planning.py` — ACC-04: takroriy jadval yordamchisi — haftalik slotlar bo'yicha mavzularni joylashtirish.
- `backend/apps/sections/policy.py` — Topshirish siyosati (I1-10; ACC-06..08, ACC-10). I3 topshirish va baholash shuni chaqiradi.
- `backend/apps/sections/realtime.py` — Real vaqt xabarlari (ACC-05). Xabar tranzaksiya tasdiqlangandan keyin ketadi (`on_commit`).
- `backend/apps/sections/routing.py`
- `backend/apps/sections/serializers.py` — Guruh API serializer'lari (I1-02).
- `backend/apps/sections/services.py` — Guruh a'zoligi bo'yicha servis funksiyalari (I1-04 dan). Yozuvlar faqat shu yerdan o'tadi.
- `backend/apps/sections/settings.py` — Ikki darajali sozlamalar (SET-01..05, ARCHITECTURE): kurs default → guruh override.
- `backend/apps/sections/settings_views.py` — Guruh sozlamalari API (I1-07; SET-01..05). Begona guruh — 404, talaba — 403.
- `backend/apps/sections/signals.py` — #95: akkaunt nofaol qilinganda yoki paroli o'zgarganda (tiklash) ochiq WebSocket darhol yopiladi.
- `backend/apps/sections/tokens.py` — Qo'shilish tokeni (SEC-02, I1-03).
- `backend/apps/sections/urls.py`
- `backend/apps/sections/views.py` — Guruh API (I1-02; SEC-01, SEC-08, SET-03).
- `backend/apps/sections/window_views.py` — Kirish oynalari API (I1-08; ACC-02, ACC-03, ACC-09, ACC-11). Begona guruh — 404, talaba — 403.
- `backend/apps/sections/windows.py` — Kirish oynalari holati (ACC-01..03). Sof funksiyalar: vaqt tashqaridan beriladi (test va soat).

## backend/config

- `backend/config/api.py` — API darajasidagi umumiy yordamchilar.
- `backend/config/asgi.py` — ASGI: HTTP (Django) va WebSocket (Channels, ACC-05). uvicorn shu `application` ni ishlatadi.
- `backend/config/celery.py` — Celery ilovasi (ADR-0001, ADR-0007; I3-06).
- `backend/config/env.py` — Muhit o'zgaruvchilarini qat'iy o'qish (NFR-16, fail fast).
- `backend/config/observability.py` — Kuzatuvchanlik (NFR-17) va loglarda maxfiylik (NFR-11, docs/SECURITY.md).
- `backend/config/settings/base.py` — Umumiy sozlamalar. Muhitga xos fayllar: dev.py, test.py, prod.py.
- `backend/config/settings/dev.py` — Lokal ishlab chiqish. Qiymatlar .env.example asosida (soxta).
- `backend/config/settings/prod.py` — Prod sozlamalari: universitet serveri, Caddy ortida (HTTPS Caddy'da tugaydi).
- `backend/config/settings/test.py` — Test sozlamalari (pytest).
- `backend/config/urls.py`
- `backend/config/views.py` — Tizim darajasidagi endpoint'lar (biznes mantiqisiz).
- `backend/config/wsgi.py`

## backend/tests

- `backend/tests/` — 8 fayl
- `backend/tests/accounts/` — 7 fayl
- `backend/tests/audit/` — 2 fayl
- `backend/tests/courses/` — 11 fayl
- `backend/tests/grading/` — 11 fayl
- `backend/tests/labs/` — 3 fayl
- `backend/tests/sandbox/` — 2 fayl
- `backend/tests/sections/` — 14 fayl

## frontend/src

- `frontend/src/App.tsx`
- `frontend/src/Link.tsx`
- `frontend/src/Markdown.view.tsx` — Ma'ruza Markdown'i komponenti — qoidalar va xavfsizlik `markdown.tsx` da.
- `frontend/src/api.ts` — Backend bilan aloqa (ARCHITECTURE: sessiya cookie + CSRF).
- `frontend/src/datetime.ts` — Vaqtlar Asia/Tashkent'da ko'rsatiladi (SRS); server ISO (offset bilan) qaytaradi.
- `frontend/src/i18n/index.ts` — Interfeys matnlari (NFR-14). Hamma ko'rinadigan matn faqat shu yerdan olinadi.
- `frontend/src/lab/AssignmentPanel.tsx` — Topshiriq paneli (I3-04; AGR-01, LAB-07): shart (talaba varianti bilan), qadamlar va "Tekshirish".
- `frontend/src/lab/CodeEditor.tsx` — CodeMirror'ni dangasa yuklaydigan muharrir. Boshqaruv bir tomonlama: boshlang'ich qiymat, keyin `onChange`.
- `frontend/src/lab/Notebook.tsx` — Chiqish 1 MB dan oshsa qisqartiriladi (ADR-0006: xotira byudjeti).
- `frontend/src/lab/RunnableCode.tsx` — CNT-02 "O'zing sinab ko'r": kod brauzerdagi Pyodide'da bajariladi (LAB-02, AGR-03).
- `frontend/src/lab/SubmitPanel.tsx` — "Topshirish" paneli (I3-09; AGR-02, AGR-04, AGR-05, AGR-06): kod serverga, navbatdagi o'rin va holat real vaqtda,
- `frontend/src/lab/autosave.ts` — Laboratoriya avtosaqlashi (I2-17; LAB-05). Server: `PUT /api/labs/{code}/work` (optimistik `version`).
- `frontend/src/lab/checker.ts` — "Tekshirish" (I3-04; AGR-01, LAB-07): ko'rinadigan testlar brauzerdagi Python'da (Pyodide worker).
- `frontend/src/lab/codemirror.ts` — CodeMirror 6 sozlamasi (ADR-0006). Faqat laboratoriya sahifasida dinamik `import()` bilan yuklanadi.
- `frontend/src/lab/notebook.ts` — Notebook holati (LAB-01) — server `apps/labs/notebook.py` bilan bir xil shakl: faqat kataklar manbasi.
- `frontend/src/lab/paste.ts` — INT-01, ACC-09: laboratoriyadagi paste qoidalari (server `GET /api/labs/{code}/work` beradi).
- `frontend/src/lab/protocol.ts` — Sahifa ↔ Pyodide worker xabarlari (I2-13; LAB-02). Kod faqat worker'da bajariladi (AGR-03 — serverda emas).
- `frontend/src/lab/pyodide.worker.ts` — Pyodide Web Worker (I2-13; LAB-02, LAB-03, ADR-0006). Python shu oqimda ishlaydi — sahifa qotmaydi.
- `frontend/src/lab/runtime.ts` — Sahifa tomonidagi Python muhiti (I2-13). Bitta worker — bitta Python (NFR-02: bir tab, bir interpretator).
- `frontend/src/lab/submissions.ts` — "Topshirish" (I3-09; AGR-02, AGR-04, AGR-05, AGR-06): server API va urinish holatini kuzatish.
- `frontend/src/main.tsx`
- `frontend/src/markdown.tsx` — Ma'ruza matni uchun kichik Markdown renderer (CNT-02). Natija — React elementlari, `innerHTML` yo'q:
- `frontend/src/nav.ts` — Kirish/ro'yxatdan keyin qaytish manzili: faqat ichki yo'l (open redirect'ga qarshi).
- `frontend/src/pages/ChangePasswordPage.tsx`
- `frontend/src/pages/DatasetsPage.tsx` — DAT-02: datasetlar — tavsif, ustunlar, rasmiy manba va litsenziya; `mlab.load()` namunasi.
- `frontend/src/pages/JoinPage.tsx` — SEC-03: havola yoki QR orqali qo'shilish. Token URL'da; javobda faqat guruh nomi va o'qituvchi.
- `frontend/src/pages/LabPage.tsx` — LAB-07: laboratoriya sahifasi — chapda topshiriq sharti va qadamlar, o'rtada notebook, o'ngda AI tutor joyi (I4).
- `frontend/src/pages/LecturePage.tsx` — CNT-02 tezkor savol: baholanmaydi, javob darhol tekshiriladi.
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/pages/PolicyPage.tsx` — SRS 7-bo'lim siyosat tarkibi. Matn faqat `uz.json` da; versiya backend'dan (`Consent` bilan bir manba).
- `frontend/src/pages/QuizPage.tsx` — CNT-06: mavzu testi — boshlash, taymer (server vaqti bilan), topshirish, natija.
- `frontend/src/pages/RegisterPage.tsx`
- `frontend/src/pages/SectionIntegrityPanel.tsx` — INT-04, INT-05: guruh x mavzu bo'yicha shubhali holatlar. Avtomatik jazo yo'q — qaror o'qituvchida.
- `frontend/src/pages/SectionPage.tsx`
- `frontend/src/pages/SectionSettingsPanel.tsx` — SET-01..05: kurs qiymati ko'rinadi; "Kurs qiymati" tanlansa override olib tashlanadi (null).
- `frontend/src/pages/SectionWindowsPanel.tsx` — ACC-03, ACC-04, ACC-09, ACC-10: mavzular bo'yicha oynalar, haftalik jadval va mustaqil muddatlar.
- `frontend/src/pages/SectionsPage.tsx`
- `frontend/src/pages/StudentHome.tsx` — ACC-05: a'zolik holati va laboratoriya vaqti. Soat farqi server vaqti bilan tuzatiladi.
- `frontend/src/pages/TopicsPage.tsx` — CNT-02, ACC-01: mavzular ro'yxati — ma'ruzalar doim ochiq, laboratoriya holati talabaga ko'rinadi.
- `frontend/src/qr.ts` — Qo'shilish havolasi uchun QR (ADR-0005: qrcode-generator). SVG `data:` URL — innerHTML ishlatilmaydi.
- `frontend/src/router.ts` — Kichik router (history API): bitta bog'liqlik kam. Sahifalar soni ko'paysa ADR bilan react-router'ga o'tiladi.
- `frontend/src/test-setup.ts`
- `frontend/src/test-utils.ts` — Testlar uchun soxta backend: `fetch` ni almashtiradi va so'rovlarni yozib boradi.
- `frontend/src/time.ts` — Qolgan vaqt matni (uz.json formatlari). Manfiy — 0.
- `frontend/src/visual/Knn.tsx` — CNT-03 `knn`: k slayderi — qaror hududlari qanday o'zgaradi (kichik k — shovqinga sezgir, katta k — silliq).
- `frontend/src/visual/LineFit.tsx` — CNT-03 `line-fit`: qiyalik (w) va siljish (b) slayderlari, chiziq va o'rtacha kvadrat xato (MSE).
- `frontend/src/visual/VisualBlock.tsx` — CNT-03: ```visual bloki (backend importda tekshirib JSON qilgan) → mos vidjet.
- `frontend/src/visual/math.ts` — Vizual qadamlar uchun sof hisoblar (CNT-03). Pyodide kerak emas — hammasi TS'da, darhol.

## frontend/e2e

- `frontend/e2e/auth.spec.ts` — AUTH-01/02: ro'yxatdan o'tish → chiqish → kirish. Backend'ning o'zi `backend/tests` da real PostgreSQL bilan
- `frontend/e2e/autosave.spec.ts` — LAB-05: ishga tushirishda saqlanadi; tarmoq uzilsa — "oflayn", qaytganda yuboriladi; sahifa yangilansa ish joyida.
- `frontend/e2e/check.spec.ts` — AGR-01, LAB-07 (I3-04): "Tekshirish" — ko'rinadigan testlar haqiqiy Pyodide'da. Talaba kodi numpy import
- `frontend/e2e/content-code.spec.ts` — CNT-04: `content/topics/*` dagi har bir "O'zing sinab ko'r" (```python try) bloki haqiqiy Pyodide'da xatosiz
- `frontend/e2e/flow.spec.ts` — I1 uchidan-uchiga oqimi (SEC-01..04, ACC-01/05/07): o'qituvchi guruh yaratadi → talaba havola orqali
- `frontend/e2e/i2-flow.spec.ts` — I2 uchidan-uchiga (CNT-02, CNT-06, LAB-01, LAB-04, LAB-05): talaba mavzular ro'yxatidan ma'ruzani ochadi, "O'zing
- `frontend/e2e/integrity.spec.ts` — INT-04, INT-05 (I3-14): o'qituvchi mavzu bo'yicha shubhali holatlarni ko'radi va izoh qoldiradi.
- `frontend/e2e/join.spec.ts` — SEC-03/04: havola → kirish → shu havolaga qaytish → so'rov → bosh sahifada "kutilmoqda". Soxta API.
- `frontend/e2e/labs-content.spec.ts` — AGR-07 (I3-15): kontentdagi haqiqiy topshiriqlarning ko'rinadigan testlari brauzerdagi Python'da (Pyodide) ham
- `frontend/e2e/lecture.spec.ts` — CNT-02: talaba mavzular ro'yxatidan ma'ruzani ochadi, klaviatura bilan qadamlarni o'tadi va tezkor savolga javob beradi.
- `frontend/e2e/notebook.spec.ts` — LAB-01: haqiqiy CodeMirror va Pyodide — yozish, Shift+Enter, o'zgaruvchi kataklar orasida, grafik, matn katagi.
- `frontend/e2e/paste.spec.ts` — INT-01, ACC-09: haqiqiy CodeMirror'da paste ushlanadi — chegaradan katta rad etiladi, har paste qayd qilinadi.
- `frontend/e2e/perf.spec.ts` — NFR-02 (I2-20): laboratoriya ochilishi (taxminiy o'lchov). Sahifa ochilgandan pandas bilan birinchi katak natijasigacha:
- `frontend/e2e/pyodide.spec.ts` — LAB-02, LAB-03, ADR-0006: haqiqiy Pyodide (o'z serverdan, `/pyodide/<versiya>/`) prod CSP ostida — chiqish,
- `frontend/e2e/quiz.spec.ts` — CNT-06: talaba mavzu testini boshlaydi, javob beradi, topshiradi va natijani ko'radi. Holatli soxta API.
- `frontend/e2e/sections.spec.ts` — SEC-01, SEC-02, SEC-04: o'qituvchi guruh yaratadi → havola va QR → so'rovni tasdiqlaydi.
- `frontend/e2e/smoke.spec.ts`
- `frontend/e2e/submit.spec.ts` — AGR-02, AGR-04, AGR-05, AGR-06 (I3-09): "Topshirish" oqimi soxta backend bilan. WebSocket ataylab yopiq —
- `frontend/e2e/windows.spec.ts` — ACC-03/04: haftalik slot bilan rejalashtirish va bitta mavzuni "Hozir ochish". Holatli soxta API.

## sandbox

- `sandbox/launcher.py` — sandbox-launcher (ADR-0007 2-band; AGR-03, I3-18a): Docker'ga kiradigan yagona xizmat.
- `sandbox/mlab.py` — Sandbox'dagi `mlab` moduli: brauzerdagi (Pyodide worker) bilan bir xil API, tarmoqsiz.
- `sandbox/runner.py` — Sandbox runner (ADR-0007 4-band; AGR-03, AGR-05; I3-05).

## scripts

- `scripts/codemap.py` — docs/CODEMAP.md ni yasaydi: har modul uchun bitta qator (fayl izohining birinchi qatori).
- `scripts/sync_status.py` — Dashboard holatini GitHub Issues'dan oladi va `docs/status/build.py` ni chaqiradi.
