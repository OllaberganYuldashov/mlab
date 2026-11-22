# Haftalik review prompti (scheduled task)

> Jadval: scheduled task "MLab haftalik review" — `CRON_TZ=Asia/Tashkent 23 3 * * 0` (yakshanba 03:23).
> Shu kuni 2-tungi run ishlamaydi (`23 3 * * 1-6`); 1-run (23:23) har kuni ishlaydi.
> Model: sessiya modeli.

```text
Bu haftalik review run. Yangi funksiya yozma.

1. CLAUDE.md, docs/PLAYBOOK.md, docs/PROGRESS.md'ni o'qi.
2. Oxirgi 7 kunda merge bo'lgan o'zgarishlarni code-review qil (xavfsizlik, test sifati,
   N+1, xatolarni boshqarish). Topilgan har muammo uchun status:ready issue yarat.
2b. Claude merge qilgan PR'larni alohida tekshir (merge-if-green va, ayniqsa, merge-protected bilan merge
   qilingan needs:owner PR'lar — ci.yml, CLAUDE.md, deploy/ o'zgarishlari): test o'chirilmaganmi, skip/xfail
   qo'shilmaganmi, coverage tushmaganmi, talab ID'lari to'g'rimi. Shubha bo'lsa — alert:red-light emas,
   status:ready tuzatish issue'si va hisobotda alohida qator.
3. tech-debt bo'yicha eng muhim 3 ta qarzni issue qilib yoz.
4. Sog'liq tendensiyasini yoz: bug'lar soni, rad etilgan PR'lar, qizil/sariq holatlar,
   oxirgi good-* teg sanasi. Tendensiya yomonlashsa, buni xulosada alohida ko'rsat.
5. Iteratsiya holati: docs/BACKLOG.md'dagi joriy iteratsiya (iter:I*) bo'yicha nechta issue yopildi,
   nechtasi qoldi, muddatga ulguriladimi. Iteratsiya tugagan bo'lsa (2 hafta), docs/iterations/<I>.md
   hisobotini yoz: natija, demo uchun ko'rsatiladigan oqimlar, kechikish sababi, keyingi iteratsiya rejasi.
6. docs/LESSONS.md'ga haftalik retro yoz: yaxshi ishladi, muammo, sabab, yangi qoida,
   runlar soni.
7. Yangi qoida chiqqan bo'lsa, CLAUDE.md'ga qo'shish uchun alohida PR och.
8. Egasi uchun haftalik xulosani docs/learn/JOURNAL.md'ga yoz: nimalar qurildi,
   qaysi texnologiyalarni o'rganish kerak, keyingi hafta rejasi.
```
