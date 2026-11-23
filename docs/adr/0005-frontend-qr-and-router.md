# ADR-0005: QR kodi kutubxonasi va frontend router

- **Sana:** 2026-11-24
- **Holat:** Qabul qilindi

## Kontekst
SEC-02: o'qituvchi guruh havolasini QR sifatida proyektorga chiqaradi. Token maxfiy, shuning uchun QR
**brauzerda** yasaladi (tashqi QR xizmatiga havola yuborilmaydi). I1 dagi sahifalar ko'payib, router
masalasi ham qayta ko'rildi (R0-10 eslatmasi: "react-router faqat ADR bilan").

## Variantlar

**QR**
| Variant | Afzallik | Kamchilik |
| --- | --- | --- |
| A. `qrcode-generator` 2.0.4 (MIT) | Bog'liqliksiz, ~50 KB (gzip ~12 KB), TS tiplari, SVG chiqaradi | Kam funksiyali (bizga yetarli) |
| B. `qrcode` (node-qrcode) | Mashhur, ko'p format | Bog'liqliklari bor, kattaroq |
| C. Tashqi QR API | Kod yo'q | Token begona serverga ketadi — taqiqlangan |

**Router**
| Variant | Afzallik | Kamchilik |
| --- | --- | --- |
| A. O'zimizning `router.ts` (History API) + oddiy regex | Bog'liqliksiz, 30 qator, yetarli | Murakkab yo'llar ko'paysa qo'lda |
| B. `react-router` | Standart, ichki marshrutlar | Katta API, hozircha keraksiz |

## Qaror
- QR: **A** — `qrcode-generator`; SVG `data:` URL ichida `<img>` ga beriladi (innerHTML yo'q).
- Router: **A** — o'zimizniki qoladi (`/sections/<id>` regex bilan). I4 dagi jonli panel bilan yo'llar
  10 tadan oshsa yoki ichki marshrut kerak bo'lsa — react-router uchun yangi ADR.

## Oqibatlar
- `npm audit` yashil; yangi bog'liqlik bitta, runtime'da tarmoqqa chiqmaydi.
- Router qarori I4 boshida qayta ko'riladi.
