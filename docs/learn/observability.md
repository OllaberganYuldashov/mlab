# Kuzatuvchanlik: JSON loglar, request id, /healthz va /readyz

## Bu nima (2–3 gap, oddiy tilda)
Server ishlayotganda nima bo'layotganini bilish uchun u **log** yozadi. Bizning loglar — har qatorda bitta
JSON obyekt: vaqt, daraja, qaysi so'rov (`request_id`) va xabar. `/healthz` va `/readyz` — serverning
"tirikmisan?" va "ishlashga tayyormisan?" degan savollarga javobi.

## Nega aynan u tanlandi (va muqobillari)
- **JSON** — qidirish va filtrlash oson (`jq`, keyinchalik Loki/Grafana). Oddiy matnli log katta bo'lganda
  "qum"ga aylanadi.
- Yangi kutubxona qo'shilmadi: Python'ning standart `logging` moduli yetarli (muqobillari: `structlog`,
  `python-json-logger` — keyin kerak bo'lsa ADR bilan).
- **Maskalash formatter'da** — har log qatori shu yerdan o'tadi, shuning uchun dasturchi "unutib qo'ysa" ham
  parol yoki to'liq Hemis ID logga tushmaydi (SECURITY.md, NFR-11).

## Bizning loyihada qayerda ishlatilgan
- `backend/config/observability.py` — `RequestIdMiddleware`, `JsonFormatter`, `mask_text`, `readiness()`.
- `backend/config/views.py` — `/healthz` (liveness) va `/readyz` (readiness).
- `backend/config/settings/base.py` — `LOGGING`, `LOG_LEVEL`.

## Asosiy tushunchalar
1. **Request ID.** Har so'rovga noyob id beriladi (yoki Caddy yuborganini oladi) va javobdagi
   `X-Request-ID` sarlavhasiga qo'yiladi. Talaba "xato chiqdi" desa, shu id bo'yicha hamma log qatorini topasiz.
2. **Liveness va readiness farqi.** `/healthz` faqat "jarayon tirik" deydi — bazaga bormaydi. `/readyz`
   bazani (`SELECT 1`) va Redis'ni (`PING`) tekshiradi: 200 — tayyor, 503 — tayyor emas. Baza bir lahza
   uzilsa, serverni qayta ishga tushirish emas, unga trafik yubormaslik kerak.
3. **Maskalash.** Hemis ID `********9012`, IP `192.168.10.x` ko'rinishida; `password`, `token`, `cookie`,
   `Authorization` qiymatlari `[REDACTED]`.
4. **Shovqinni kamaytirish.** Muvaffaqiyatli `/healthz`/`/readyz` chaqiruvlari loglanmaydi (Docker ularni
   har necha soniyada chaqiradi). URL'ning `?` dan keyingi qismi ham yozilmaydi.
5. **Javobda tafsilot yo'q.** `/readyz` faqat `ok`/`fail` qaytaradi; xato turi (masalan, `ConnectionError`)
   faqat logda.

## Rasmiy hujjat va yaxshi manbalar
- Django: "Logging" bo'limi.
- Python: `logging` — Logging Cookbook.
- Kubernetes hujjatidagi liveness/readiness probe tushunchalari (g'oya Docker va Caddy uchun ham bir xil).

## Kichik mashq
`cd backend && uv run python manage.py runserver`, keyin `curl -i localhost:8000/readyz` va
`curl -i localhost:8000/yoq` — terminaldagi JSON qatorlarda `request_id` javobdagi `X-Request-ID` bilan
bir xil ekanini tekshiring. Redis'ni to'xtatib (`service redis-server stop`), `/readyz` 503 qaytarishini ko'ring.
