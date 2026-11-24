# ADR-0006: Pyodide va CodeMirror — versiyalar, o'z serverdan yetkazish, xotira byudjeti

- **Sana:** 2026-11-24
- **Holat:** Qabul qilindi (I2-01, #96)

## Kontekst
ADR-0001 laboratoriya uchun Pyodide (Web Worker ichida) va CodeMirror 6 ni tanlagan. I2 da ularni amalda qo'llashdan
oldin aniq qarorlar kerak:

- LAB-02: numpy, pandas, matplotlib, seaborn, scikit-learn brauzerda ishlashi.
- LAB-03: Pyodide va paketlar **platforma serveridan** beriladi, keyingi yuklashlar keshdan (universitet tarmog'ida
  tashqi CDN sekin yoki yopiq bo'lishi mumkin; talaba kodi uchun tashqi domenga ishonmaymiz).
- NFR-02: monoblok (Intel i5, 8 GB RAM, Windows, Chrome) — birinchi ochilish ≤ 2 daqiqa, keyingilari ≤ 15 soniya;
  brauzer tabi ~1–1,5 GB dan oshmasligi kerak (2026-11-23 egasi qarori).
- AGR-03: talaba kodi hech qachon server jarayonida bajarilmaydi.

## O'lchovlar (2026-11-24, `pyodide-lock.json` va CDN javob sarlavhalaridan)

| Versiya | Sana | Python | numpy | pandas | matplotlib | scikit-learn | scipy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.29.5 (eski qator) | 2026-09-16 | 3.13.2 | 2.2.5 | 2.3.3 | 3.8.4 | 1.7.0 | 1.14.1 |
| **314.0.7** | 2026-09-14 | 3.14.2 | 2.4.6 | 3.0.2 | 3.10.8 | 1.8.0 | 1.18.0 |
| 314.0.8 | 2026-11-13 | 3.14 | — | — | — | — | — |

- Pyodide yangi versiyalash sxemasiga o'tgan: `314.x` = Python 3.14 asosida.
- Yadro: `pyodide.asm.wasm` ≈ 9,6 MB, `python_stdlib.zip` ≈ 2,5 MB. Kerakli paketlar yopilmasi (dependency closure) —
  17 paket; aniq jami hajm (taxminan 35–45 MB, siqilmagan) build skripti tomonidan o'lchanadi va `docs/iterations/I2.md` ga yoziladi.
- **seaborn** Pyodide lock'ida yo'q — u sof Python (`seaborn-0.13.2-py3-none-any.whl`, 0,3 MB), PyPI'dan olinadi.

## Variantlar

**Yetkazish**
| Variant | Afzallik | Kamchilik |
| --- | --- | --- |
| A. Ommaviy CDN (jsDelivr) | Hech narsa saqlanmaydi | LAB-03 ga zid; universitet tarmog'iga bog'liq; tashqi domen talaba sahifasida (CSP kengayadi) |
| **B. O'z server: build vaqtida yuklab olish + SHA-256 tekshiruvi, Caddy beradi** | LAB-03; versiya qat'iy; CSP `'self'` qoladi | Image hajmi ~50 MB oshadi; yangilash — PR orqali |
| C. Binar fayllarni repoga commit qilish | Oddiy | Git tarixi har yangilanishda o'n MB larga o'sadi |
| D. Service Worker'da o'z kesh | Oflayn ishlaydi | Murakkab (yangilash, kesh tozalash); brauzer HTTP keshi + `immutable` yetarli |

**Versiya**: 0.29.5 (Python 3.13, pandas 2.3) yoki 314.0.7 (Python 3.14, pandas 3.0). 314.0.8 juda yangi (2 haftadan kam).

**To'xtatish (LAB-06)**: `worker.terminate()` + yangi worker, yoki `SharedArrayBuffer` interrupt (o'zgaruvchilar saqlanadi,
lekin COOP/COEP sarlavhalari va butun saytning cross-origin isolation'i kerak).

## Qaror

1. **Versiya: Pyodide 314.0.7.** pandas 3.0 va scikit-learn 1.8 — kontentni eng yangi API bilan yozamiz (eski qatorga
   qaytish keyin qimmat). Bugfix versiyalari (314.0.x) alohida PR bilan, kamida 2 hafta o'tgach.
2. **Yetkazish: B.** `frontend/scripts/fetch-pyodide.mjs`:
   - manifest `frontend/pyodide.lock.json` (repoda): versiya, har fayl nomi va **SHA-256** — faqat kerakli fayllar
     (yadro + 17 paket + seaborn wheel), butun `full/` emas;
   - fayllar `jsDelivr`dan build vaqtida olinadi, xesh mos kelmasa build to'xtaydi (supply chain himoyasi);
   - natija `frontend/dist/pyodide/314.0.7/` ga; repoga binar fayl tushmaydi (`.gitignore`).
   - Caddy: `/pyodide/<versiya>/*` — `Cache-Control: public, max-age=31536000, immutable` (yo'lda versiya bor, shuning
     uchun abadiy kesh xavfsiz). Bu mavjud `@assets` qoidasiga qo'shiladi — `deploy/Caddyfile` o'zgarishi `needs:owner`.
3. **Paketlar talab bo'yicha:** worker ishga tushganda faqat yadro; `import pandas` va h.k. ko'rilganda
   `loadPackagesFromImports()` bilan. Ma'ruzadagi oddiy kod blokini ishlatish uchun scikit-learn yuklanmaydi.
4. **To'xtatish:** MVP'da `terminate()` + yangi worker (o'zgaruvchilar yo'qoladi — foydalanuvchiga aytiladi).
   COOP/COEP keyinroq, agar o'qituvchilar so'rasa (iframe va tashqi rasmlarga ta'sir qiladi).
5. **CSP:** `script-src 'self' 'wasm-unsafe-eval'` kerak (WebAssembly kompilyatsiyasi). `'unsafe-eval'` qo'shilmaydi;
   I2-13 da Playwright prod CSP bilan tekshiradi. `worker-src` — `default-src 'self'` dan.
6. **Xavfsizlik chegarasi:** worker sahifa bilan bir origin'da. Talaba kodi `js.fetch` bilan API'ni **o'z nomidan**
   chaqira oladi (cookie yuboriladi), lekin CSRF tokenni o'qiy olmaydi (`document` yo'q) — demak faqat o'zi ko'ra
   oladigan narsani GET qiladi. Yashirin testlar brauzerga umuman yuborilmaydi (AGR-05), shuning uchun bu chegara yetarli.
   Worker'ga sessiya yoki token uzatilmaydi.
7. **CodeMirror 6:** `codemirror` 6.0.2 (`basicSetup`), `@codemirror/lang-python` 6.2.1, `@codemirror/lang-markdown`.
   Faqat laboratoriya sahifasida dinamik `import()` — boshqa sahifalar bundle'i o'smaydi.
8. **Xotira byudjeti (NFR-02):** bitta worker (bir tab — bitta Python), paketlar talab bo'yicha; grafiklar PNG
   (`matplotlib` Agg) — DOM'da SVG to'planmaydi; chiqish bitta katakda 1 MB dan oshsa qisqartiriladi. I2-20 da
   o'lchanadi; oshsa — kontentda og'ir misollar kichraytiriladi.

## Oqibatlar
- Frontend image ~50 MB kattalashadi; birinchi ochilish uchun asosiy omil — monoblok CPU (wasm kompilyatsiyasi), tarmoq
  emas (lokal server). Keyingi ochilishlar brauzer keshidan.
- Yangi texnologiya qo'shilmadi (ADR-0001 dagi stack), lekin yangi bog'liqliklar: `pyodide` (npm, faqat TS tiplari va
  loader), `codemirror` paketlari — I2-13 va I2-14 PR'larida.
- `deploy/Caddyfile` (CSP va kesh) o'zgarishi egasi tomonidan merge qilinadi.
- Dars: `docs/learn/pyodide.md`.
