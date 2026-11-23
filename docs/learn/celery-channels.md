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
- Hali kodda yo'q. Redis allaqachon ishlatiladi: kesh, lockout hisoblagichi (`backend/apps/accounts/lockout.py`),
  so'rov cheklovlari va `/readyz` tekshiruvi.
- **Celery** — I3: avtobaholovchi (sandbox konteyneri, navbat, 2 ta parallel), I4: AI tutor chaqiruvlari.
  Talaba kodi hech qachon Django yoki Celery jarayonida bajarilmaydi — faqat sandbox'da (CLAUDE.md 5.5).
- **Channels** — I1: kirish oynasi xabari; I4: jonli monitoring paneli, yordam navbati, guruh chati.

## Asosiy tushunchalar
1. **Navbat (queue).** Vazifa Redis'ga yoziladi, worker uni oladi va bajaradi; foydalanuvchi darhol javob oladi.
2. **Idempotentlik.** Vazifa ikki marta bajarilsa ham natija bir xil bo'lishi kerak (qayta urinishlar bo'ladi).
3. **Qayta urinish va chegara.** Tashqi xizmat (Gemini) ishlamasa — kechikish bilan qayta urinish, cheksiz emas.
4. **WebSocket.** Server va brauzer o'rtasida ochiq qoladigan ulanish — server o'zi xabar yubora oladi.
5. **Guruh (channel group).** Masalan, "guruh 12 ning o'qituvchisi" — xabar shu guruhdagi barcha ulanishlarga.
6. **Avtorizatsiya WebSocket'da ham.** HTTP'dagi kabi: kim ulanyapti, qaysi guruhga ruxsati bor; vaqtinchalik
   parol bilan kirgan foydalanuvchi (`must_change_password`) WebSocket'ga ham ulana olmaydi (I4 da).

## Rasmiy hujjat va yaxshi manbalar
- https://docs.celeryq.dev/ — "First steps with Celery", "Tasks" (retry, acks_late).
- https://channels.readthedocs.io/ — Tutorial (chat ilovasi).

## Kichik mashq
`backend/apps/accounts/lockout.py` ni o'qing: Redis'dagi `INCR` nima uchun "atomik" deyiladi va 20 ta
parallel so'rov testida (`test_auth_02_parallel_guesses_cannot_exceed_5_attempts`) nima tekshiriladi?
Xuddi shu fikr I3 dagi baholash navbatida ham kerak bo'ladi.
