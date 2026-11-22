# Haftalik review prompti (scheduled task)

> Jadval: scheduled task "MLab haftalik review" — `CRON_TZ=Asia/Tashkent 23 3 * * 0` (yakshanba 03:23).
> Shu kuni 2-tungi run ishlamaydi (`23 3 * * 1-6`); 1-run (23:23) har kuni ishlaydi.
> Model: sessiya modeli.

```text
Bu haftalik review run. Yangi funksiya yozma.

1. CLAUDE.md, docs/PLAYBOOK.md, docs/PROGRESS.md'ni o'qi.
2. Oxirgi 7 kunda merge bo'lgan o'zgarishlarni code-review qil (xavfsizlik, test sifati,
   N+1, xatolarni boshqarish). Topilgan har muammo uchun status:ready issue yarat.
2b. merge-gate orqali avtomatik merge bo'lgan PR'larni alohida tekshir: test o'chirilmaganmi, skip/xfail
   qo'shilmaganmi, coverage tushmaganmi, talab ID'lari to'g'rimi. Shubha bo'lsa — alert:red-light emas,
   status:ready tuzatish issue'si va hisobotda alohida qator.
3. tech-debt bo'yicha eng muhim 3 ta qarzni issue qilib yoz.
4. Sog'liq tendensiyasini yoz: bug'lar soni, rad etilgan PR'lar, qizil/sariq holatlar,
   oxirgi good-* teg sanasi. Tendensiya yomonlashsa, buni xulosada alohida ko'rsat.
5. Iteratsiya holati: docs/BACKLOG.md'dagi joriy iteratsiya (iter:I*) bo'yicha nechta issue yopildi,
   nechtasi qoldi, muddatga ulguriladimi. Iteratsiya tugagan bo'lsa (2 hafta), docs/iterations/<I>.md
   hisobotini yoz: natija, demo uchun ko'rsatiladigan oqimlar, kechikish sababi, keyingi iteratsiya rejasi.
5b. MVP prognozi (egasining 2026-11-22 qarori). Ball: size:M = 2, size:S = 1.
   - Tezlik: oxirgi 7 kunda yopilgan issue'lar bo'yicha ball (va runlar soni); docs/PROGRESS.md "Tezlik" jadvaliga qator qo'sh.
   - Qoldiq: R0 va R1 ning ochiq issue'lari + hali bo'linmagan epik va kontent tasklari bahosi
     (boshlang'ich baho 2026-11-22: R0 ~24, R1 kodi ~240, R1 kontenti ~130 ball).
   - Prognoz: qoldiq / oxirgi 2 haftaning o'rtacha tezligi → taxminiy MVP sanasi (hafta oralig'i bilan).
   - Limit: run'lar limit tufayli qisqarganmi (7 kunlik limit ogohlantirishi, to'xtab qolgan run'lar).
   - Egasiga bog'liq to'siqlar: domen/HTTPS, monoblok sinovi, yurist, sinov darsi — holati va qachongacha kerakligi.
   Kunlik hisobotlar issue'sidagi xulosada alohida qator: "Tezlik: X ball/hafta · Qoldiq: Y · MVP: <sana oralig'i>".
6. docs/LESSONS.md'ga haftalik retro yoz: yaxshi ishladi, muammo, sabab, yangi qoida,
   runlar soni.
7. Yangi qoida chiqqan bo'lsa, CLAUDE.md'ga qo'shish uchun alohida PR och.
8. Egasi uchun haftalik xulosani docs/learn/JOURNAL.md'ga yoz: nimalar qurildi,
   qaysi texnologiyalarni o'rganish kerak, keyingi hafta rejasi.
```
