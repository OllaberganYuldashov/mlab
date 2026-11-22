# React va TypeScript (Vite bilan)

## Bu nima (2–3 gap, oddiy tilda)

**React** — interfeysni kichik qismlardan (komponentlardan) yig'ish uchun kutubxona: har komponent
funksiya bo'lib, ma'lumotga qarab sahifaning bir qismini chizadi. **TypeScript** — JavaScript'ning
turlar qo'shilgan versiyasi: xatolarni brauzerda emas, kod yozish paytida ko'rsatadi. **Vite** —
dasturlash paytida sahifani bir zumda yangilaydigan va prod uchun kichik fayllar yig'adigan vosita.

## Nega aynan u tanlandi (va muqobillari)

| Variant | Nima uchun |
| --- | --- |
| **React + TypeScript + Vite** | Tanlandi: notebook va jonli monitoring paneli kabi murakkab, tez o'zgaradigan interfeyslar uchun; eng katta ekotizim (CodeMirror 6, Testing Library) |
| Django shablonlari + HTMX | Sodda sahifalar uchun yaxshi, lekin notebook va jonli panel uchun yetarli emas |
| Next.js | Server rendering kerak emas (yopiq platforma, SEO yo'q); qo'shimcha server jarayoni RAM sarflaydi |
| Vue | Yaxshi muqobil; React'da kerakli kutubxonalar ko'proq |

To'liq asoslash: `docs/adr/0001-stack.md`.

## Bizning loyihada qayerda ishlatilgan

| Fayl | Nima qiladi |
| --- | --- |
| `frontend/index.html` | Yagona HTML sahifa (`lang="uz"`), React shu yerga "o'rnatiladi" |
| `frontend/src/main.tsx` | Kirish nuqtasi: `<App />` ni `#root` ga chizadi |
| `frontend/src/App.tsx` | Bosh komponent |
| `frontend/src/i18n/uz.json` | **Hamma** interfeys matnlari (o'zbekcha) |
| `frontend/src/i18n/index.ts` | `t("kalit")` — matnni tarjima faylidan oladi |
| `frontend/src/**/*.test.tsx` | Vitest + Testing Library unit testlari |
| `frontend/e2e/smoke.spec.ts` | Playwright: haqiqiy brauzerda sahifani ochib tekshiradi |
| `frontend/vite.config.ts`, `tsconfig*.json`, `eslint.config.js` | Yig'ish, turlar, lint sozlamalari |

## Asosiy tushunchalar

1. **Komponent va JSX.** `function App() { return <h1>...</h1>; }` — HTML'ga o'xshash yozuv aslida
   JavaScript. Komponentlar bir-birining ichiga qo'yiladi.
2. **Props va state.** Props — komponentga tashqaridan beriladigan qiymat; state — komponentning
   o'z xotirasi (`useState`). State o'zgarsa, React faqat kerakli joyni qayta chizadi.
3. **Turlar (TypeScript).** `t()` faqat `uz.json` dagi kalitlarni qabul qiladi: `t("yoq.kalit")`
   deb yozsangiz, kod yig'ilmaydi. Shu tarzda tarjimasiz matn xatosi brauzerga yetmasdan ushlanadi.
4. **i18n (tarjima).** Komponentda hech qachon matn qattiq yozilmaydi — faqat `t("app.title")`.
   `App.test.tsx` dagi test sahifadagi har bir matn `uz.json` da borligini tekshiradi. R3 da `ru.json`
   qo'shilganda komponentlar o'zgarmaydi.
5. **Test piramidasi.** Ko'p tez unit testlar (Vitest, jsdom — "soxta brauzer"), kam, lekin haqiqiy
   brauzerdagi e2e testlar (Playwright). E2E prod yig'masi (`vite build` + `vite preview`) ustida ishlaydi.
6. **Lockfile.** `package-lock.json` hamma (CI ham) aynan bir xil versiyalarni o'rnatishini ta'minlaydi:
   `npm ci` faqat lockfile bo'yicha o'rnatadi.

## Rasmiy hujjat va yaxshi manbalar

- React: <https://react.dev/learn>
- TypeScript qo'llanmasi: <https://www.typescriptlang.org/docs/handbook/intro.html>
- Vite: <https://vite.dev/guide/>
- Testing Library tamoyillari: <https://testing-library.com/docs/guiding-principles>
- Playwright: <https://playwright.dev/docs/intro>

## Kichik mashq (o'zingiz bajarib ko'rish uchun)

1. Frontend'ni ishga tushiring:
   ```bash
   cd frontend && npm ci
   ```
   ```bash
   cd frontend && npm run dev
   ```
   Brauzerda `http://localhost:5173` ni oching.
2. `src/i18n/uz.json` da `"app.status"` matnini o'zgartiring — sahifa saqlash bilanoq yangilanadi.
3. `App.tsx` ga `<p>Salom</p>` qo'shing va `npm test -- --run` ni ishga tushiring. Qaysi test
   yiqilganini va nega yiqilganini o'qing. Keyin uni `uz.json` ga kalit qo'shib, `t()` orqali tuzating.
4. `App.tsx` da `t("app.titel")` deb xato yozing va `npm run typecheck` ni ishga tushiring —
   TypeScript xatoni qanday ko'rsatishini ko'ring.
