# Pyodide: Python brauzerda qanday ishlaydi

> Kim uchun: loyiha egasi. Maqsad: laboratoriyada talaba kodi qayerda va qanday bajarilishini tushunish.
> Qaror: ADR-0006. O'qish vaqti: ~10 daqiqa.

## 1. Nima bu?

Pyodide — CPython interpretatorining **WebAssembly** (wasm) ga kompilyatsiya qilingan nusxasi. Brauzer wasm'ni deyarli
mashina kodi tezligida bajaradi, shuning uchun Python va hatto numpy, pandas, scikit-learn kabi C kengaytmali
paketlar to'g'ridan-to'g'ri talabaning kompyuterida ishlaydi. Server faqat fayllarni beradi — **kodni bajarmaydi**
(AGR-03). Bu bizga ikki narsa beradi: server yuklanmaydi (100 talaba = 100 ta o'z kompyuteri) va talaba kodi serverga
zarar yetkaza olmaydi.

## 2. Nega Web Worker'da?

Brauzerda sahifaning asosiy oqimi (UI) bitta. Agar Python shu oqimda `while True:` bajarsa, sahifa qotib qoladi.
**Web Worker** — alohida oqim: Python o'sha yerda ishlaydi, sahifa esa xabarlar orqali gaplashadi:

```text
Sahifa (React)                         Worker (Pyodide)
  run(id=7, code) ───────────────────►  kodni bajaradi
                  ◄─────────────────── stdout "salom"
                  ◄─────────────────── figure (PNG)
                  ◄─────────────────── result / error (traceback)
```

"To'xtatish" tugmasi worker'ni butunlay o'ldiradi (`terminate()`) va yangisini ochadi — shu sababli o'zgaruvchilar
yo'qoladi. Bu oddiy va ishonchli usul.

## 3. Fayllar qayerdan keladi?

Pyodide yadrosi ~12 MB, kerakli paketlar bilan ~40–50 MB. Ularni har safar internetdan (CDN) olish universitet
tarmog'ida sekin bo'lishi mumkin, shuning uchun (LAB-03):

1. Build vaqtida skript fayllarni yuklab oladi va har birining **SHA-256 xeshini** repodagi ro'yxat bilan solishtiradi.
   Xesh mos kelmasa — build to'xtaydi (kimdir CDN'dagi faylni almashtirgan bo'lsa ham bizga yetib kelmaydi).
2. Fayllar frontend image'iga kiradi va Caddy ularni `/pyodide/314.0.7/...` manzilidan beradi.
3. Yo'lda versiya bor, shuning uchun brauzerga "bu fayl hech qachon o'zgarmaydi" (`immutable`) deymiz —
   ikkinchi ochilishda hammasi keshdan, tarmoqsiz.

## 4. Paketlar talab bo'yicha

Worker ishga tushganda faqat Python yadrosi yuklanadi. Kod `import pandas` desa — pandas va uning bog'liqliklari
o'shanda yuklanadi. Ma'ruzadagi `print(2 + 2)` uchun scikit-learn'ni kutish shart emas.

**seaborn** alohida: u Pyodide to'plamida yo'q, lekin sof Python bo'lgani uchun PyPI'dagi wheel faylini (0,3 MB)
o'zimiz beramiz.

## 5. Xavfsizlik chegarasi

- Talaba kodi faqat o'z brauzerida. U platforma API'sini **o'z nomidan** chaqira oladi (xuddi brauzerda sahifani
  ochganday) — boshqa talabaning ma'lumotini emas, chunki server har so'rovda ruxsatni tekshiradi.
- Yashirin testlar va yechimlar brauzerga umuman yuborilmaydi (AGR-05) — ular faqat server sandbox'ida (I3).
- CSP'ga faqat `'wasm-unsafe-eval'` qo'shiladi (wasm kompilyatsiyasi uchun); umumiy `eval` ruxsat etilmaydi.

## 6. Monoblokda nimani tekshirish kerak (NFR-02)

Egasi I2 oxirida bitta monoblokda (8 GB RAM, Chrome) tekshiradi:

1. Chrome'da "Ko'rib chiqish" → Network → **Disable cache** belgilab laboratoriyani oching: tayyor bo'lguncha vaqt
   (talab: ≤ 2 daqiqa).
2. Belgini olib, sahifani qayta oching (talab: ≤ 15 soniya).
3. `import pandas, sklearn` katagini ishlating va Chrome **Task Manager** (Shift+Esc) da tab xotirasini yozing
   (byudjet: ≤ 1–1,5 GB).
4. Natijalarni `docs/iterations/I2.md` dagi jadvalga yoki kunlik hisobot issue'siga yozing.

## 7. Atamalar

| Atama | Ma'nosi |
| --- | --- |
| WebAssembly (wasm) | Brauzer bajaradigan ixcham binar kod formati |
| Web Worker | Sahifadan alohida JavaScript oqimi |
| wheel (`.whl`) | Python paketining tayyor arxivi |
| lock fayl | Aniq versiyalar va xeshlar ro'yxati — har build bir xil natija |
| CSP | Brauzerga "bu sahifa qaysi manbalardan kod yuklashi mumkin" degan qoida |
