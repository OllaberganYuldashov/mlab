# Django REST Framework (DRF)

## Bu nima (2–3 gap, oddiy tilda)
Django veb-sahifalar yasaydi; **DRF** esa uning ustida **API** yasaydi — brauzerdagi React ilovasi
serverdan ma'lumotni JSON ko'rinishida oladi va yuboradi. DRF kirish ma'lumotini tekshiradi, kimga ruxsat
borligini aniqlaydi va javobni bir xil formatda qaytaradi.

## Nega aynan u tanlandi (va muqobillari)
ADR-0001: Django bilan eng yetuk va keng tarqalgan API kutubxonasi. Muqobillar: **Django Ninja** (zamonaviy,
lekin ekotizimi kichikroq), **FastAPI** (alohida freymvork — Django admin, ORM va auth'dan voz kechish kerak bo'lardi).

## Bizning loyihada qayerda ishlatilgan
- `backend/config/settings/base.py` — `REST_FRAMEWORK`: default ruxsat `IsAuthenticated`, faqat JSON, sessiya auth.
- `backend/apps/accounts/serializers.py` — kirish ma'lumotini tekshirish (ro'yxatdan o'tish, login, parol).
- `backend/apps/accounts/views.py` — endpoint'lar (`/api/auth/...`, `/api/users/{id}/reset-password`, `/api/instructors`).
- `backend/apps/accounts/permissions.py` — rol ruxsatlari (`IsAdmin`, `IsInstructor`, ...).
- `docs/openapi.yaml` — barcha endpoint'lar ro'yxati (drf-spectacular, ADR-0003).

## Asosiy tushunchalar
1. **Serializer** — "ichkariga kiradigan ma'lumot to'g'rimi?" (validatsiya) va "tashqariga nima chiqadi?"
   (javob shakli). Rol kabi xavfli maydonlar serializer'da umuman bo'lmaydi — mass assignment imkonsiz.
2. **View (APIView)** — bitta manzil va uning metodlari (`get`, `post`, `patch`).
3. **Permission** — kim bu amalni qila oladi. Default: faqat tizimga kirganlar; ochiq endpoint aniq `AllowAny`.
4. **Obyekt darajasidagi ruxsat** — "bu o'qituvchi aynan shu talabani ko'ra oladimi?" (`apps/accounts/policies.py`).
   Begona obyekt uchun 404 — mavjudligi ham oshkor qilinmaydi (IDOR'ga qarshi).
5. **Throttle** — so'rovlar sonini cheklash (ro'yxatdan o'tish, login, parol tiklash).

## Rasmiy hujjat va yaxshi manbalar
- https://www.django-rest-framework.org/ — Tutorial (1–6 qismlar).
- OWASP API Security Top 10 (ayniqsa API1: BOLA/IDOR).

## Kichik mashq
`backend/apps/accounts/serializers.py` dagi `RegisterSerializer` ni o'qing: qaysi maydonlar bor va qaysi
maydon ataylab yo'q? So'ng `backend/tests/accounts/test_auth_01_register_api.py` dagi
`test_auth_01_mass_assignment_ignored` testi buni qanday tekshirishini toping.
