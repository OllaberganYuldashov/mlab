# Celery va Django Channels — fon vazifalari va real vaqt

## Bu nima (2–3 gap, oddiy tilda)
**Celery** — uzoq davom etadigan ishlarni (masalan, talaba kodini sandbox'da baholash yoki AI tutorga
so'rov) foydalanuvchini kuttirmasdan "orqada" bajaradi. **Django Channels** — WebSocket orqali real vaqt:
o'qituvchining jonli paneli, guruh chati, "kirish oynasi ochildi" xabari sahifani yangilamasdan keladi.
Ikkalasi ham **Redis** orqali ishlaydi.

## Nega aynan u tanlandi (va muqobillari)
ADR-0001. Celery muqobillari: **RQ** (soddaroq, lekin qayta urinish va jadval imkoniyati kam), **Dramatiq**,
yoki PostgreSQL'dagi navbat (oddiy, lekin bizda Redis baribir bor). Channels muqobillari: alohida Node.js
WebSocket serveri (ikkinchi til va auth), Server-Sent Events (faqat bir tomonlama).

## Bizning loyihada qayerda ishlatiladi
- **Channels (I1-11, ACC-05):** `backend/config/asgi.py` (HTTP + WebSocket), `apps/sections/consumers.py`
  (`/ws/student`: faqat tasdiqlangan talaba, faqat o'z guruhi kanali `section-<id>`), `apps/sections/realtime.py`
  (xabar `transaction.on_commit` bilan; Redis ishlamasa HTTP amali buzilmaydi). Kanal qatlami — Redis (`CHANNEL_LAYERS`).
  Prod'da uvicorn WebSocket'ni `websockets` paketi bilan qabul qiladi; Caddy `/ws/*` ni Django'ga uzatishi kerak.
- Redis yana: kesh, lockout hisoblagichi (`backend/apps/accounts/lockout.py`), so'rov cheklovlari, `/readyz`.
- **Celery** — I3: avtobaholovchi (sandbox konteyneri, navbat, 2 ta parallel), I4: AI tutor chaqiruvlari.
  Talaba kodi hech qachon Django yoki Celery jarayonida bajarilmaydi — faqat sandbox'da (CLAUDE.md 5.5).
- **Channels** — I1: kirish oynasi xabari (tayyor); I4: jonli monitoring paneli, yordam navbati, guruh chati.

## Asosiy tushunchalar
1. **Navbat (queue).** Vazifa Redis'ga yoziladi, worker uni oladi va bajaradi; foydalanuvchi darhol javob oladi.
2. **Idempotentlik.** Vazifa ikki marta bajarilsa ham natija bir xil bo'lishi kerak (qayta urinishlar bo'ladi).
3. **Qayta urinish va chegara.** Tashqi xizmat (Gemini) ishlamasa — kechikish bilan qayta urinish, cheksiz emas.
4. **WebSocket.** Server va brauzer o'rtasida ochiq qoladigan ulanish — server o'zi xabar yubora oladi.
5. **Guruh (channel group).** Masalan, "guruh 12 ning o'qituvchisi" — xabar shu guruhdagi barcha ulanishlarga.
6. **Avtorizatsiya WebSocket'da ham.** HTTP'dagi kabi: kim ulanyapti, qaysi guruhga ruxsati bor; vaqtinchalik
   parol bilan kirgan foydalanuvchi (`must_change_password`) WebSocket'ga ham ulana olmaydi (I4 da).

## Amalda: baholash navbati (I3-06)

Birinchi haqiqiy Celery vazifasi — `apps/grading/tasks.py` `grade_submission`. Mantiq `apps/grading/service.py` da
(Celery'siz testlanadi), vazifa faqat qayta urinish siyosatini qo'shadi.

- **Commit'dan keyin navbatga** (`transaction.on_commit`): aks holda worker hali yozilmagan yozuvni qidiradi.
  Commit va navbat orasida broker yiqilsa — yozuv `queued` bo'lib qoladi; `requeue_stale()` uni qayta qo'yadi.
- **`acks_late` + `reject_on_worker_lost`:** xabar vazifa *tugagandan keyin* tasdiqlanadi — worker o'lsa, xabar
  boshqa worker'ga qaytadi. Narxi: bitta vazifa ikki marta kelishi mumkin. Shuning uchun —
- **idempotentlik:** yozuv `SELECT … FOR UPDATE` bilan "egallanadi" (`queued → running`, `attempts += 1`);
  takroriy xabar `running`/`done` ni ko'rib chiqib ketadi. Natija faqat `attempts` mos kelsa yoziladi
  (`UPDATE … WHERE attempts = N`) — kech qolgan eski worker yangisining natijasini bosib ketmaydi.
- **Qayta urinish faqat infratuzilma xatosida** (sandbox javob bermadi), 3 martagacha, `5·2ⁿ` s (60 s gacha) +
  tasodifiy jitter. Talaba kodi xatosi — oddiy natija (0 ball): uni qayta urinish faqat navbatni to'ldiradi.
- **`prefetch_multiplier=1`, `concurrency=2`:** har worker jarayoni bittadan vazifa oladi — bir vaqtda ko'pi bilan
  2 ta sandbox konteyneri (AGR-04).
- **Navbat holati real vaqtda (I3-07):** worker holatni o'zgartirgach `submission.status` xabarini talabaning
  `user-<id>` guruhiga yuboradi (Channels + Redis — worker va veb-server bir xil kanal qatlamini ishlatadi). Xabar
  yo'qolishi mumkin (Redis qisqa uzilishi) — shuning uchun manba baza: qayta ulangan sahifa `GET /api/submissions/{id}`
  bilan holatni oladi. Xabar commit'dan keyin ketadi (`on_commit`): bekor qilingan tranzaksiya haqida xabar bo'lmaydi.
- Kuzatuv: `grading.queued|done|retry|failed|requeued` log qatorlari (`queued`/`running` soni, davomiylik, urinish).

## Rasmiy hujjat va yaxshi manbalar
- https://docs.celeryq.dev/ — "First steps with Celery", "Tasks" (retry, acks_late).
- https://channels.readthedocs.io/ — Tutorial (chat ilovasi).

## Kichik mashq
`backend/apps/accounts/lockout.py` ni o'qing: Redis'dagi `INCR` nima uchun "atomik" deyiladi va 20 ta
parallel so'rov testida (`test_auth_02_parallel_guesses_cannot_exceed_5_attempts`) nima tekshiriladi?
Xuddi shu fikr I3 dagi baholash navbatida ham kerak bo'ladi.
