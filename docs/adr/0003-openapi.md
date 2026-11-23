# ADR-0003: OpenAPI sxemasi — drf-spectacular

- **Sana:** 2026-11-23
- **Holat:** Qabul qilindi

## Kontekst
DoD: har yangi endpoint bilan OpenAPI yangilanadi. R0-06 — loyihaning birinchi API endpoint'i. Frontend
(R0-10) va keyingi tasklar API shartnomasiga tayanadi; shartnoma o'zgarishi PR diff'ida ko'rinishi kerak.

## Variantlar
| Variant | Afzallik | Kamchilik |
| --- | --- | --- |
| A. drf-spectacular | DRF uchun de-fakto standart, OpenAPI 3, faol yuritiladi, `--validate` | Yangi bog'liqlik |
| B. DRF'ning o'z `rest_framework.schemas.openapi` | Bog'liqliksiz | DRF hujjatida eskirgan deb belgilangan, imkoniyati kam |
| C. Qo'lda yozilgan `openapi.yaml` | To'liq nazorat | Kod bilan tez ajralib qoladi, tekshiruvsiz |

## Qaror
**A.** Sxema koddan generatsiya qilinadi va repoda `docs/openapi.yaml` sifatida saqlanadi. Test
(`test_openapi_committed_schema_is_up_to_date`) generatsiya natijasini repodagi fayl bilan solishtiradi:
API o'zgarib, fayl yangilanmasa — CI qizil. Yangilash:
`cd backend && uv run python manage.py spectacular --validate --file ../docs/openapi.yaml`.
Jonli `/api/schema/` faqat super admin va admin uchun (yopiq platforma — API xaritasi ochiq emas).
Swagger UI qo'shilmadi (tashqi CDN'dan skript yuklaydi).

## Oqibatlar
- Har API PR'ida `docs/openapi.yaml` diff'i — shartnoma o'zgarishi ko'rib chiqiladi (expand-contract).
- Deploy usuli ADR'i (R0-15) **ADR-0004** bo'ladi.
