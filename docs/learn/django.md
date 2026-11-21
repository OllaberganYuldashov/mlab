# Django

## Bu nima (2–3 gap, oddiy tilda)

Django — Python'da veb-ilova yozish uchun "batareyalari bilan" keladigan framework. Unda ma'lumotlar
bazasi bilan ishlash (ORM), migratsiyalar, foydalanuvchilar va parollar, admin panel, xavfsizlik
himoyalari (CSRF, XSS, clickjacking) tayyor holda bor. MLab'da Django backend'ning asosi: API,
admin panel va (keyinroq) WebSocket'lar shu ustiga quriladi.

## Nega aynan u tanlandi (va muqobillari)

| Variant | Nega tanlanmadi / tanlandi |
| --- | --- |
| **Django + DRF** | Tanlandi: auth, admin, ORM, migratsiyalar tayyor; MVP tezroq; hujjati juda yaxshi |
| FastAPI | Tez va zamonaviy, lekin admin, auth, migratsiyalarni qo'lda yig'ish kerak |
| Node.js (NestJS) | Ikkinchi asosiy til paydo bo'ladi; ML fani esa Python'da |

To'liq asoslash: `docs/adr/0001-stack.md`.

## Bizning loyihada qayerda ishlatilgan

| Fayl | Nima qiladi |
| --- | --- |
| `backend/manage.py` | Django buyruqlarini ishga tushiradi (`migrate`, `runserver`, `check` ...) |
| `backend/config/settings/base.py` | Umumiy sozlamalar: ilovalar, middleware, til, vaqt zonasi, xavfsizlik |
| `backend/config/settings/{dev,test,prod}.py` | Muhitga xos farqlar (masalan, prod'da cookie faqat HTTPS orqali) |
| `backend/config/env.py` | Muhit o'zgaruvchilarini qat'iy o'qish — yo'q bo'lsa ilova to'xtaydi |
| `backend/config/urls.py` | URL → view jadvali |
| `backend/config/views.py` | `/healthz` — "ilova tirikmi?" tekshiruvi |
| `backend/config/asgi.py`, `wsgi.py` | Server (uvicorn/gunicorn) ilovani shu yerdan oladi |
| `backend/tests/` | pytest testlari |

## Asosiy tushunchalar

1. **Loyiha va ilovalar (apps).** Loyiha (`config/`) — sozlamalar va URL'lar. Ilova (`apps/accounts`,
   `apps/grading` ...) — bitta mavzu bo'yicha model, view va testlar. MLab'da ilovalar ro'yxati
   CLAUDE.md'da qat'iy belgilangan; yangisi faqat ADR bilan.
2. **Sozlamalar muhitdan (12-factor).** Parol, kalit, baza manzili kodda yozilmaydi — ular muhit
   o'zgaruvchisidan (`SECRET_KEY`, `DATABASE_URL` ...) o'qiladi. Majburiysi yo'q bo'lsa, ilova
   ishga tushmasdan aniq xato beradi (**fail fast**): "yarim sozlangan" ilova jimgina noto'g'ri
   ishlashidan ko'ra darhol to'xtagani yaxshi. Prod sozlamasi dev kaliti (`dev-only-...`) bilan ham
   ishga tushmaydi.
3. **Request → middleware → view → response.** Har so'rov middleware'lar zanjiridan o'tadi
   (xavfsizlik header'lari, sessiya, CSRF, foydalanuvchini aniqlash), keyin URL bo'yicha view
   funksiyasiga boradi va javob qaytadi.
4. **ORM va migratsiyalar.** Jadval Python klassi (model) sifatida yoziladi; `makemigrations`
   o'zgarishdan migratsiya fayli yaratadi, `migrate` uni bazaga qo'llaydi. Migratsiyalar Git'da
   saqlanadi — baza tuzilmasi tarixi ham kod kabi ko'riladi.
5. **Custom User modeli.** Django standart `User`ini keyin almashtirish juda qiyin. Shuning uchun
   R0-04 da o'z `User`imizni (login — Hemis ID) **birinchi migratsiya** qilib yaratamiz. Shu sababli
   R0-01 da `django.contrib.admin` hali yoqilmagan.
6. **Vaqt.** `USE_TZ = True`: bazada vaqt `timestamptz` (UTC) saqlanadi, ko'rsatishda
   `Asia/Tashkent` ga o'giriladi.
7. **Liveness va readiness.** `/healthz` faqat "jarayon tirik" deydi va bazaga tegmaydi.
   "Baza va Redis tayyormi?" savoliga `/readyz` javob beradi (R0-14).

## Rasmiy hujjat va yaxshi manbalar

- Django rasmiy tutoriali: <https://docs.djangoproject.com/en/5.2/intro/tutorial01/>
- Sozlamalar ma'lumotnomasi: <https://docs.djangoproject.com/en/5.2/ref/settings/>
- Deploy oldidan tekshiruv: <https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/>
- The Twelve-Factor App, "Config": <https://12factor.net/config>
- pytest-django: <https://pytest-django.readthedocs.io/>

## Kichik mashq (o'zingiz bajarib ko'rish uchun)

1. Backend'ni ishga tushiring:
   ```bash
   cd backend && uv sync
   ```
   ```bash
   cd backend && SECRET_KEY=dev-only-change-me DATABASE_URL=postgres://mlab:mlab@localhost:5432/mlab REDIS_URL=redis://localhost:6379/0 ALLOWED_HOSTS=localhost uv run python manage.py runserver
   ```
   Brauzerda `http://localhost:8000/healthz` ni oching — `{"status": "ok"}` chiqishi kerak.
2. Endi `SECRET_KEY=...` qismini olib tashlab qayta ishga tushiring. Xato xabarida qaysi
   o'zgaruvchi yetishmayotgani yozilganini ko'ring — bu fail fast.
3. Testlarni ishga tushiring va coverage hisobotini o'qing:
   ```bash
   cd backend && uv run pytest
   ```
4. Savol o'zingizga: nega `/healthz` bazaga murojaat qilmasligi kerak? (Maslahat: baza vaqtincha
   ishlamay qolsa, Docker butun ilovani qayta ishga tushirishi kerakmi?)
