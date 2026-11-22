# Rollar, DRF ruxsatlari va Django Admin

## Bu nima (2–3 gap, oddiy tilda)
Har foydalanuvchining bitta **roli** bor: super admin, admin, o'qituvchi yoki talaba (SRS 2.2). Server har
so'rovda "bu odam bu amalni qila oladimi?" deb tekshiradi — buni **ruxsat (permission)** sinflari qiladi.
**Django Admin** — tayyor boshqaruv paneli (`/admin/`), unga faqat super admin va admin kiradi.

## Nega aynan u tanlandi (va muqobillari)
- DRF'ning o'z `BasePermission` mexanizmi — yangi kutubxona kerak emas. Muqobillari: `django-guardian`
  (obyekt ruxsatlari jadvalda — bizga ortiqcha), `django-rules` (qoidalar kutubxonasi — hozircha kerak emas).
- Django'ning `Group`/`Permission` jadvallari ishlatilmaydi: rol bitta maydonda, qoidalar kodda — tushunish va
  test qilish oson.

## Bizning loyihada qayerda ishlatilgan
- `backend/apps/accounts/permissions.py` — `IsSuperAdmin`, `IsAdmin`, `IsInstructor`, `IsStudent`.
- `backend/apps/accounts/admin_access.py` — `RoleAccessAdmin`: har model uchun kim ko'radi/o'zgartiradi.
- `backend/apps/accounts/admin.py`, `backend/apps/audit/admin.py` — foydalanuvchilar, yo'nalishlar, audit.

## Asosiy tushunchalar
1. **Autentifikatsiya va avtorizatsiya farqi.** Birinchisi — "sen kimsan?" (login), ikkinchisi — "senga
   mumkinmi?" (ruxsat). Default: har API faqat tizimga kirganlarga (`IsAuthenticated`).
2. **Ierarxiya yo'q.** Super admin avtomatik ravishda talaba yoki o'qituvchi amallarini qila olmaydi.
   Ikki rolga ruxsat kerak bo'lsa: `permission_classes = [IsAdmin | IsSuperAdmin]`.
3. **Rol darajasi yetarli emas.** O'qituvchi "o'qituvchi" bo'lgani uchun hamma guruhni ko'rmaydi — faqat
   o'zinikini. Bu **obyekt darajasidagi** tekshiruv har endpoint'da alohida yoziladi va "begona foydalanuvchi"
   testi bilan tekshiriladi (IDOR — birovning ma'lumotini id'ni almashtirib olish).
4. **Admin'da parol yo'q.** Formada `password` maydoni umuman yo'q — xesh ham ko'rinmaydi.
5. **Rol o'zgarishi — audit.** Rolni faqat super admin o'zgartiradi; har o'zgarish "kim, kimni, nimadan nimaga"
   ko'rinishida audit jurnaliga yoziladi.

## Rasmiy hujjat va yaxshi manbalar
- DRF: "Permissions" bo'limi.
- Django: "The Django admin site" — `has_*_permission` metodlari.
- OWASP: Broken Object Level Authorization (API Security Top 10, API1).

## Kichik mashq
`backend/tests/accounts/test_srs_2_2_roles_permissions.py` dagi `MATRIX` ro'yxatini o'qing va jadval chizing:
qatorlar — ruxsat sinflari, ustunlar — rollar, kataklarda 200 yoki 403.
