# Custom User, DB cheklovlari va Argon2

## Bu nima (2–3 gap, oddiy tilda)
Django'da tayyor `User` modeli bor, lekin unda login — `username`. Bizda login — **Hemis ID**, qo'shimcha
FIO, rol va yo'nalish kerak, shuning uchun o'z `User` modelimiz yozildi. Parollar **Argon2** bilan xeshlanadi:
bazada parolning o'zi emas, undan hisoblangan, orqaga qaytarib bo'lmaydigan "barmoq izi" saqlanadi.

## Nega aynan u tanlandi (va muqobillari)
- **Custom User loyiha boshida.** Django rasmiy hujjati: `AUTH_USER_MODEL`ni birinchi migratsiyadan
  oldin belgilang — keyin almashtirish juda qiyin. Shuning uchun R0-01 da `admin` ham qo'shilmagan edi.
- **Argon2** — SRS talabi (AUTH-03, NFR-10). Muqobillari: PBKDF2 (Django default'i, sekinroq himoya),
  bcrypt (72 bayt chegarasi). Argon2 xotirani ham talab qiladi — GPU bilan buzish qimmatlashadi.
  Kutubxona: `argon2-cffi` (`django[argon2]` rasmiy qo'shimchasi).
- **Faker** — testlarda soxta FIO va Hemis ID (haqiqiy shaxsiy ma'lumot taqiqlangan, CLAUDE.md 5.3).
  `factory_boy` sinab ko'rildi, lekin uning tiplari `mypy --strict` bilan ishlamadi — oddiy funksiyalar yetarli.

## Bizning loyihada qayerda ishlatilgan
- `backend/apps/accounts/models.py` — `User`, `Direction`, `Role`, normalizatsiya funksiyalari.
- `backend/apps/accounts/migrations/0001_initial.py` — loyihaning birinchi migratsiyasi.
- `backend/config/settings/base.py` — `AUTH_USER_MODEL`, `PASSWORD_HASHERS`.
- `backend/tests/accounts/` — testlar va `factories.py`.

## Asosiy tushunchalar
1. **Invariant bazada.** "Hemis ID — 12 raqam", "talabaning yo'nalishi bor", "rol — 4 tadan biri" kabi
   qoidalar PostgreSQL `CHECK` cheklovi bilan yozilgan. Kod xato qilsa ham baza noto'g'ri qatorni qabul qilmaydi.
2. **`on_delete=PROTECT`.** Yo'nalishga talaba bog'langan bo'lsa, yo'nalishni o'chirib bo'lmaydi.
3. **`is_staff` — rol'dan hisoblanadi**, alohida bayroq emas: ikkita maydon bir-biriga zid bo'lib qolmaydi.
4. **Unicode NFC.** "ó" ikki xil bayt ketma-ketligi bilan yozilishi mumkin; NFC ularni bitta shaklga keltiradi.
   Apostrof variantlari (`'`, `ʻ`, `ʼ`, `‘`) esa o'zgartirilmaydi — talaba nima yozgan bo'lsa, shuni ko'radi.
5. **Testlarda tez xesh.** Argon2 ataylab sekin; testlarda MD5 ishlatiladi, Argon2 esa alohida testda tekshiriladi.

## Rasmiy hujjat va yaxshi manbalar
- Django: "Customizing authentication" — Substituting a custom User model.
- Django: "Password management" — Using Argon2.
- OWASP Password Storage Cheat Sheet.

## Kichik mashq
`cd backend && uv run python manage.py sqlmigrate accounts 0001 --settings=config.settings.test` ni ishga
tushiring va `CHECK` qatorlarini toping. Har biri qaysi qoidani himoya qilishini o'zingizga tushuntiring.
