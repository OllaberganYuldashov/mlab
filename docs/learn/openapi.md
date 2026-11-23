# OpenAPI va drf-spectacular

## Bu nima (2–3 gap, oddiy tilda)
**OpenAPI** — API'ning "pasporti": qaysi manzillar bor, qanday ma'lumot qabul qiladi va qaytaradi.
**drf-spectacular** bu pasportni Django REST Framework kodidan avtomatik yaratadi. Bizda u
`docs/openapi.yaml` faylida saqlanadi va har API o'zgarishida yangilanadi.

## Nega aynan u tanlandi (va muqobillari)
ADR-0003: DRF uchun eng keng tarqalgan va yuritiladigan vosita. Muqobillar: DRF'ning eski o'z generatori
(eskirgan), qo'lda yozish (kod bilan tez farqlanib qoladi).

## Bizning loyihada qayerda ishlatilgan
- `docs/openapi.yaml` — repodagi shartnoma (PR diff'ida ko'rinadi).
- `backend/config/settings/base.py` — `SPECTACULAR_SETTINGS`; `/api/schema/` faqat super admin va admin.
- `backend/tests/accounts/test_auth_01_register_api.py` — fayl eskirgan bo'lsa test yiqiladi.

## Asosiy tushunchalar
1. **Shartnoma (contract).** Frontend va backend shu fayl bo'yicha kelishadi.
2. **Generatsiya + tekshiruv.** `spectacular --validate` sxema OpenAPI standartiga mosligini tekshiradi.
3. **Diff — ko'rib chiqish.** API javobi o'zgarsa, PR'da `openapi.yaml` ham o'zgaradi: buni sezmaslik qiyin.
4. **Yopiq sxema.** Platforma yopiq, shuning uchun jonli sxema faqat xodimlarga ko'rinadi.

## Rasmiy hujjat va yaxshi manbalar
- https://drf-spectacular.readthedocs.io/
- https://spec.openapis.org/oas/latest.html

## Kichik mashq
`docs/openapi.yaml` dan `/api/auth/register` ni toping: qaysi maydonlar majburiy (`required`)?
So'ng https://editor.swagger.io saytiga faylni qo'yib (faqat bu ochiq fayl — secret yo'q), sahifada ko'ring.
