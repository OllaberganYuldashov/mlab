# JOURNAL — har run yozuvi

> Har run oxirida Claude qo'shadi. Eng yangisi yuqorida.

### 2026-11-25 — tungi run 2/2
- **Bajarilgan issue'lar va PR:** #152 → PR #179 ("Tekshirish" — brauzerda ko'rinadigan testlar), #154 → PR #180
  (Celery baholash navbati). 4 ball.
- **Nima qilindi (oddiy tilda):** Laboratoriyaning chap panelida endi talabaning o'z topshirig'i chiqadi: sharti uning
  varianti raqamlari bilan, qadamlar va ballar. "✓ Tekshirish" tugmasi ko'rinadigan testlarni talabaning brauzerida
  darhol ishga tushiradi va har test uchun "o'tdi / o'tmadi" va sababini ko'rsatadi. Cheksiz sikl bo'lsa 30 soniyadan
  keyin to'xtatiladi. Yashirin testlar brauzerga umuman yuborilmaydi. Server tomonda baholash navbati tayyor: topshirilgan
  kod navbatga tushadi, bir vaqtda ko'pi bilan 2 tasi tekshiriladi; bitta urinish hech qachon ikki marta baholanmaydi;
  sandbox vaqtincha ishlamasa 3 martagacha qayta urinadi, talaba xatosi esa qayta urinilmaydi.
- **Ishlatilgan skill'lar va nima uchun:** security-discipline (yashirin testlar oshkor emas, shartni to'ldirishda
  `str.format` atribut teshigi yopildi, IDOR testi), query-discipline (Prefetch, so'rovlar soni testi),
  database-queues va idempotency-and-side-effects (qulf bilan "egallash", `attempts` tekshiruvi, commit'dan keyin
  navbat), retry-amplification (faqat infratuzilma xatosida, eksponensial kutish + jitter), error-handling-as-design.
- **Yangi texnologiya / tushuncha:** Celery amalda — `docs/learn/celery-channels.md` "Amalda: baholash navbati";
  brauzerdagi tekshiruv — `docs/learn/sandbox.md` 7-bo'lim.
- **Ertalab nimani ko'rish kerak:** ikkala dars bo'limi. Lokal demoda panel hozircha "topshiriq hali qo'shilmagan"
  deydi — topshiriqlar kontentga #163 da qo'shiladi.
- **Savollar / bloklar:** yo'q. Worker, launcher va davriy sweeper compose'ga #166 da (`needs:owner`).

### 2026-11-24 — tungi run 1/2
- **Bajarilgan issue'lar va PR:** #151 → PR #176 (variant tanlash), #153 → PR #177 (sandbox image va runner). 4 ball.
- **Nima qilindi (oddiy tilda):** Har talaba topshiriqning o'z variantini oladi: variant maxfiy kalit bilan hisoblanadi,
  qo'shnisi qaysi variant olganini taxmin qila olmaydi, va bir marta tanlangach o'zgarmaydi. Talaba kodini serverda
  tekshiradigan "quticha" (sandbox konteyner) tayyor: internet yo'q, fayl yozib bo'lmaydi, xotira va vaqt cheklangan;
  bularni ataylab buzishga urinadigan 8 ta test haqiqiy Docker'da o'tdi. Yashirin testlarning kodi va xabari talabaga
  chiqmaydi.
- **Ishlatilgan skill'lar va nima uchun:** idempotency-and-side-effects (bir vaqtda ochilganda bitta yozuv),
  security-discipline va algorithmic-complexity-attacks (fork-bomba, cheksiz sikl, katta chiqish),
  docker-build-strategies (digest va hash bilan qotirilgan image, pip'siz runtime).
- **Ertalab nimani ko'rish kerak:** `docs/learn/sandbox.md` 6-bo'lim (o'zingiz `docker build` bilan sinash mumkin).
- **Savollar / bloklar:** yo'q. Ma'lum cheklov (runner bitta jarayonda) — I3-19 ko'rigida.

### 2026-11-24 — custom run 11 (kunduzi, qo'shimcha)
- **Bajarilgan issue'lar va PR:** #150 → PR #170 (topshiriq formati), #160 → PR #171 (paste cheklovi). 4 ball.
- **Nima qilindi (oddiy tilda):** Amaliy topshiriqlar endi fayl ko'rinishida yoziladi (`content/labs/A01-.../`):
  shart, qadamlar va ballari (jami 100), har daraja uchun kamida 5 variant, ko'rinadigan va yashirin testlar. Import
  xatoni fayl va qator bilan ko'rsatadi; yechimlar papkasi bazaga yuklanmaydi. Laboratoriyada katta matnni (default
  200 belgidan ko'p) joylashtirib bo'lmaydi, nazorat rejimida umuman bo'lmaydi; har urinish hajmi qayd qilinadi —
  matnning o'zi saqlanmaydi.
- **Ishlatilgan skill'lar va nima uchun:** data-modeling-discipline (ball va daraja cheklovlari bazada, qadam tartibi
  DEFERRED unique), security-discipline (paste qarori serverda qayta hisoblanadi, IDOR testlari), unicode-pitfalls
  (hajm kod nuqtalari bo'yicha: oʻ va emoji bitta belgi).
- **Ertalab nimani ko'rish kerak:** `content/README.md` (topshiriq formati), `course.yaml` dagi `paste_limit`.
- **Savollar / bloklar:** yo'q. PR #171 CI tugashidan oldin egasi akkaunti bilan oddiy merge qilingan (skript emas) — main CI natijasi kunlik hisobotda.

### 2026-11-24 — custom run 10 (kunduzi, qo'shimcha)
- **Bajarilgan issue'lar va PR:** #116 → PR #148 (I2 yakuni), #149 → PR #168 (ADR-0007). 2 ball + I3 rejasi (19 issue, #149–#167).
  **I2 yopildi (21/21).**
- **Nima qilindi (oddiy tilda):** I2 bo'yicha mustaqil xavfsizlik ko'rigi o'tkazildi va topilganlar tuzatildi: umumiy
  kompyuterda laboratoriya qoralamasi keyingi talabaga ko'rinardi (endi chiqishda o'chadi), admin'da ishlatilgan test
  savolini o'zgartirish eski natijalarni buzardi (endi qulflanadi) va boshqalar. Avtobaholovchi (talaba kodini serverda
  yashirin testlar bilan tekshirish) arxitekturasi tanlandi: alohida kichik "launcher" xizmati — Docker huquqi faqat unda.
- **Ishlatilgan skill'lar va nima uchun:** security-reviewer agenti (I2 oxiri), security-discipline (Docker soketi = host'da
  root; socket-proxy konteyner sozlamasini cheklamasligi aniqlandi), boring-by-default (Celery — stack'da bor).
- **Ertalab nimani ko'rish kerak:** `docs/iterations/I2.md`, `docs/learn/sandbox.md`, ADR-0007.
- **Savollar / bloklar:** yo'q. PR #131 (Caddy CSP) hali egasida — yangi qo'shimchalar bilan.

### 2026-11-24 — custom run 9 (kunduzi, qo'shimcha)
- **Bajarilgan issue'lar va PR:** #107 → PR #144 (M16–M22), #95 → PR #145 (qattiqlashtirish), #115 → PR #146 (monoblok sinovi). 4 ball.
- **Nima qilindi (oddiy tilda):** Kursning 22 ta ma'ruzasi to'liq (neyron tarmoqlar va MLOps — TensorFlow'siz, numpy bilan).
  Akkaunt o'chirilsa yoki paroli tiklansa, ochiq real vaqt ulanishi darhol uziladi; bir talabaga ko'pi bilan 5 ta ulanish.
  Laboratoriya ochilish vaqti o'lchandi: pandas bilan birinchi natija ~7 s (talab ≤ 15 s); Python endi sahifa ochilishi
  bilan fonda tayyorlanadi.
- **Ishlatilgan skill'lar va nima uchun:** performance-and-scaling ("qaysi yukda?" — vaqt protsessorga ketishini o'lchab
  topdik, keshga emas), security-discipline (signal orqali har qanday yo'l bilan parol/faollik o'zgarishi), testing-with-discernment.
- **Saboq:** taxminiy o'lchov ham foydali — kesh bilan va keshsiz bir xil vaqt "muammo tarmoqda" degan taxminni rad etdi.
- **Ertalab nimani ko'rish kerak:** `docs/iterations/I2.md` — monoblokda o'lchash jadvali (sizdan).
- **Savollar / bloklar:** yo'q. PR #131 (Caddy CSP) hali egasida.

### 2026-11-24 — custom run 8 (kunduzi, qo'shimcha)
- **Bajarilgan issue'lar va PR:** #105 → PR #141 (M02–M08), #106 → PR #142 (M09–M15). 4 ball.
- **Nima qilindi (oddiy tilda):** 14 ta yangi ma'ruza: ma'lumotga ishlovdan PCA va assotsiativ qoidalargacha. Har birida
  tushuntirish, brauzerda ishlaydigan kod (Iris, Wine, Breast Cancer datasetlari bilan), tezkor savol va 3 tadan test savoli.
  Yangi avtomatik tekshiruv: kontentdagi har bir kod bloki haqiqiy Pyodide'da ishga tushiriladi — xato bo'lsa CI qizil.
- **Saboq:** tekshiruvchi birinchi ishga tushishdayoq 3 ta xatoni topdi (`score(...).round` — Python `float` da yo'q),
  import esa YAML xatosini ushladi. Kontent ham kod kabi test qilinishi kerak.
- **Ertalab nimani ko'rish kerak:** bir-ikki ma'ruzani o'qib chiqing (masalan, M07, M11) — til va soddaligi mosmi?
- **Savollar / bloklar:** yo'q. PR #131 (Caddy CSP) hali egasida.

### 2026-11-24 — custom run 7 (kunduzi, qo'shimcha)
- **Bajarilgan issue'lar va PR:** #114 → PR #138 (datasetlar va `mlab.load()`), #100 → PR #139 (vizual qadam). 4 ball.
- **Nima qilindi (oddiy tilda):** Talaba laboratoriyada `df = mlab.load("iris")` deb yozsa, platformadagi dataset pandas
  jadvali bo'lib keladi. 3 ta ochiq dataset (Iris, Wine, Breast Cancer — UCI, CC BY 4.0), har birining manbasi va
  litsenziyasi "Datasetlar" sahifasida. Ma'ruzada slayderli vizual qadam: chiziqni surib xato (MSE) qanday o'zgarishini
  ko'rish va k-NN da k ni o'zgartirib qaror chegarasini ko'rish.
- **Ishlatilgan skill'lar va nima uchun:** security-discipline (dataset faqat kurs a'zosiga, litsenziya ro'yxati importda),
  boring-by-default (vidjetlar SVG va oddiy slayder bilan, kutubxonasiz).
- **Ertalab nimani ko'rish kerak:** `/datasets` sahifasi va M01 dagi "Model qanday o'rganadi?" qadami.
- **Savollar / bloklar:** yo'q. PR #131 (Caddy CSP) hali egasida.

### 2026-11-24 — custom run 6 (kunduzi, qo'shimcha)
- **Bajarilgan issue'lar va PR:** #109 → PR #134 (notebook), #113 → PR #135 (laboratoriya sahifasi), #112 → PR #136 (avtosaqlash). 5 ball.
- **Nima qilindi (oddiy tilda):** Talaba `/labs/M01` da Jupyter'ga o'xshash notebook'da ishlaydi: kod va matn kataklari,
  Shift+Enter, grafiklar. Ish har 10 soniyada va har ishga tushirishda serverga saqlanadi; internet uzilsa kompyuterda
  saqlanib, qaytganda yuboriladi; ikki oynada ochilsa — qaysi nusxani saqlashni so'raydi. Oyna yopiq bo'lsa — ochilish vaqti.
- **Ishlatilgan skill'lar va nima uchun:** retry-amplification (qayta urinish 2 → 60 s, bitta navbat), idempotency (versiya
  bilan saqlash), boring-by-default (CodeMirror — ADR-0006 da ko'zda tutilgan, faqat laboratoriyada yuklanadi).
- **Ertalab nimani ko'rish kerak:** laboratoriya monoblokda qanday ko'rinishi — e2e 1366×768 da tekshiradi.
- **Savollar / bloklar:** yo'q. PR #131 (Caddy CSP) hali egasida.

### 2026-11-24 — custom run 5 (kunduzi, qo'shimcha)
- **Bajarilgan issue'lar va PR:** #108 → PR #129 (Pyodide worker), #104 → PR #130 (kontent admin), #110 → PR #132 (to'xtatish). 4 ball.
  PR #131 — `deploy/Caddyfile` (CSP `'wasm-unsafe-eval'`, `/pyodide/` keshi), `needs:owner`.
- **Nima qilindi (oddiy tilda):** Ma'ruzadagi "O'zing sinab ko'r" kodi endi talabaning brauzerida haqiqiy Python'da ishlaydi
  (print, xatolar, matplotlib grafiklari). Python fayllari (50 MB) o'z serverimizdan, har biri xesh bilan tekshirilgan.
  Cheksiz sikl bo'lsa — "To'xtatish". Super admin ma'ruza va test matnidagi kichik xatoni admin panelda tuzatadi (audit bilan).
- **Ishlatilgan skill'lar va nima uchun:** dependency-confusion (fayllar xesh bilan qotirilgan, uch manbadan solishtirilgan),
  security-discipline (CSP'ga faqat `'wasm-unsafe-eval'`, e2e prod siyosatida, tashqi so'rov yo'qligi tekshirildi),
  migration-safety (audit CHECK `NOT VALID` + `VALIDATE`, katta jadvalda yozish bloklanmaydi).
- **Saboq:** qo'lda yozilgan migratsiya SQL'ini avtomatik yasashda ro'yxatga ortiqcha qiymatlar tushdi — endi bazadagi CHECK
  `Action` bilan testda solishtiriladi.
- **Ertalab nimani ko'rish kerak:** PR #131 ni merge qiling — busiz serverda Python ishlamaydi.
- **Savollar / bloklar:** yo'q.

### 2026-11-24 — custom run 4/4 (kunduzi)
- **Bajarilgan issue'lar va PR:** #102 → PR #125 (mavzu testi backend), #103 → PR #127 (test sahifasi). 4 ball.
- **Nima qilindi (oddiy tilda):** Talaba mavzu testini ishlaydi: savollar bankdan tasodifiy, variantlar aralashtirilgan,
  vaqt serverda (30 soniya imtiyoz), urinishlar soni kurs sozlamasidan. Sahifa yangilansa test davom etadi, vaqt tugasa
  o'zi topshiriladi. To'g'ri javoblar faqat topshirgandan keyin ko'rinadi.
- **Ishlatilgan skill'lar va nima uchun:** clocks-and-time (muddat server soatida), isolation-anomalies (parallel "Boshlash" —
  bitta urinish, talaba qatori qulfi), error-handling-as-design (kech topshirishda urinishni yopish tranzaksiya bilan bekor
  bo'lib ketardi — testda ushlandi), testing-with-discernment (avtomatik topshirish ikki marta yuborilardi — testda ushlandi).
- **Saboq:** fonda `&` bilan ishga tushirilgan merge skripti shell yopilganda to'xtaydi — fon uchun alohida buyruq kerak.
- **Ertalab nimani ko'rish kerak:** `content/course.yaml` — `quiz_questions`, `quiz_minutes`, `quiz_attempts` qiymatlari.
- **Savollar / bloklar:** yo'q.

### 2026-11-24 — custom run 3/4 (kunduzi)
- **Bajarilgan issue'lar va PR:** #111 → PR #123 (avtosaqlash API), #99 → PR #124 (ma'ruza sahifalari). 4 ball.
- **Nima qilindi (oddiy tilda):** Laboratoriyadagi ish serverda saqlanadi: ikki oynada ochilgan bo'lsa, eski oyna yangisini
  ustidan yozmaydi (409 va serverdagi holat), javob yo'qolib qayta yuborilgan saqlash ikki marta yozilmaydi, oyna yopiq
  bo'lsa saqlanmaydi. Talaba "Ma'ruzalar" sahifasidan mavzuni ochib qadamma-qadam o'qiydi va tezkor savolga javob beradi.
- **Ishlatilgan skill'lar va nima uchun:** idempotency-and-side-effects (takroriy saqlash), isolation-anomalies (qator qulfi,
  ikki tab bir vaqtda), security-discipline (Markdown — innerHTML'siz, `javascript:` havolalar rad), boring-by-default
  (Markdown uchun yangi kutubxona qo'shilmadi).
- **Saboq:** ikki PR bir vaqtda CHANGELOG'ga yozsa, ikkinchisi konfliktga tushadi. Force-push o'rniga main'ni branch'ga merge
  qildik (tarix qayta yozilmaydi).
- **Ertalab nimani ko'rish kerak:** `docs/learn/react-typescript.md` — "Markdown'ni xavfsiz ko'rsatish".
- **Savollar / bloklar:** yo'q.

### 2026-11-24 — custom run 2/4 (kunduzi)
- **Bajarilgan issue'lar va PR:** #101 → PR #120 (Aiken importi), #98 → PR #121 (ma'ruza API). 4 ball.
- **Nima qilindi (oddiy tilda):** Egasining Moodle'dagi Aiken testlari endi `quiz.aiken` fayli sifatida mavzu savollar
  bankiga yuklanadi (xatolar qator raqami bilan). Fayldan olib tashlangan savol o'chirilmaydi — arxivlanadi, chunki keyin
  talabalarning urinishlari unga bog'lanadi. Ma'ruzalar API orqali beriladi: mavzular ro'yxati (talabaga laboratoriya
  holati bilan), qadamlar va rasmlar (xesh URL — brauzer abadiy keshlaydi).
- **Ishlatilgan skill'lar va nima uchun:** unicode-pitfalls (savol kaliti NFC xeshi, matnning o'zi o'zgarmaydi — oʻ/gʻ
  saqlanadi), data-modeling-discipline (arxiv o'rniga o'chirish yo'q), auth-and-authorization (har endpoint'da kursga ruxsat,
  begona/pending/guruhsiz o'qituvchi testlari), query-discipline (so'rovlar soni qadamlar soniga bog'liq emas).
- **Ertalab nimani ko'rish kerak:** `content/README.md` — Aiken fayli qanday yoziladi (egasi o'z testlarini qo'shishi mumkin).
- **Savollar / bloklar:** yo'q.

### 2026-11-24 — custom run 1/4 (kunduzi)
- **Bajarilgan issue'lar va PR:** #71 → PR #94 (I1 yakuni), #96 → PR #117 (ADR-0006 Pyodide), #97 → PR #118 (ma'ruza qadamlari formati). 4 ball.
  I2 21 ta issue'ga bo'lindi (#96–#116, 36 ball); qattiqlashtirish takliflari — #95.
- **Nima qilindi (oddiy tilda):** I1 yopildi: ikkita mustaqil ko'rik (sxema va xavfsizlik) o'tkazildi va topilganlar tuzatildi —
  join havolasi server loglariga ochiq yozilardi (endi yo'q), WebSocket ulanishida kichik poyga bor edi. O'qituvchi va talaba
  ikki brauzerda: guruh → havola → tasdiq → "Hozir ochish" → talabada darhol "Hozir ochiq" — bitta e2e testda.
  Laboratoriya uchun Pyodide versiyasi va yetkazish usuli tanlandi. Ma'ruzalarga rasm, "sinab ko'r" kodi va tezkor savol qo'shildi.
- **Ishlatilgan skill'lar va nima uchun:** schema-reviewer va security-reviewer agentlari (CLAUDE.md §9 — I1 oxiri),
  /hunt-n-plus-one (N+1 yo'q — so'rovlar soni testlari bilan qotirildi), boring-by-default (rasm bazada — yangi volume yo'q),
  security-discipline (SVG taqiq, fayl boshi tekshiruvi, yo'l travers'i), migration-safety (ikki tomonga sinov).
- **Saboq:** agent xulosasini ham tekshirish kerak — schema-reviewer "topic indeksi yo'q" dedi, bazada esa bor edi
  (aksincha `section` indeksi ortiqcha edi).
- **Yangi texnologiya / tushuncha:** `docs/learn/sections.md`, `docs/learn/pyodide.md`, ADR-0006.
- **Ertalab nimani ko'rish kerak:** `docs/iterations/I1.md` (talab → test matritsasi), ADR-0006 qarorlari.
- **Savollar / bloklar:** yo'q.

### 2026-11-24 — tungi run 2/2
- **Bajarilgan issue'lar va PR:** #69 → PR #91 (talaba sahifalari), #70 → PR #92 (sozlamalar va oynalar sahifasi). 4 ball.
- **Nima qilindi (oddiy tilda):** Talaba QR/havola orqali kiradi, ro'yxatdan o'tsa ham shu sahifaga qaytadi, so'rov yuboradi
  va bosh sahifada holatini hamda laboratoriya ochilishiga qolgan vaqtni ko'radi. O'qituvchi guruh sahifasida AI'ni
  bir tugmada o'chiradi, mavzularni ochadi/yopadi, haftalik jadval tuzadi va mustaqil topshiriq muddatlarini qo'yadi.
- **Ishlatilgan skill'lar va nima uchun:** security-discipline (qaytish manzili faqat `/join/<token>` — open redirect yo'q),
  clocks-and-time (server vaqti bilan soat farqi, Asia/Tashkent ko'rinishi), testing-with-discernment (xato yo'llari testda).
- **Yangi texnologiya / tushuncha:** yangi kutubxona yo'q; WebSocket qayta ulanishi (eksponensial kutish).
- **Ertalab nimani ko'rish kerak:** PR #88 (Caddy `/ws/*`) — hali egasida.
- **Savollar / bloklar:** yo'q.

### 2026-11-24 — tungi run 1/2
- **Bajarilgan issue'lar va PR:** #67 → PR #87 (real vaqt), #68 → PR #89 (o'qituvchi guruhlari sahifasi). 4 ball. PR #88 — egasida.
- **Nima qilindi (oddiy tilda):** O'qituvchi oynani ochsa, talaba ekranida xabar darhol paydo bo'ladi (WebSocket).
  O'qituvchi brauzerda guruh yaratadi, QR'ni proyektorga chiqaradi va so'rovlarni bir tugmada tasdiqlaydi.
- **Ishlatilgan skill'lar va nima uchun:** auth-and-authorization + security-reviewer (WebSocket: ruxsat faqat ulanishda
  tekshirilardi → 15 daqiqa umr va a'zolik o'zgarsa uzish), testing-with-discernment (e2e soxta API bilan), boring-by-default
  (QR — bitta kichik kutubxona, router — o'zimizniki; ADR-0005).
- **Yangi texnologiya / tushuncha:** Django Channels (`docs/learn/celery-channels.md`), ADR-0005.
- **Ertalab nimani ko'rish kerak:** PR #88 ni merge qiling (Caddy `/ws/*`).
- **Savollar / bloklar:** yo'q.

### 2026-11-23 — custom run 4 (I1)
- **Bajarilgan issue'lar va PR:** #65 → PR #83 (haftalik slot), #66 → PR #84 (topshirish siyosati, muddatlar). 4 ball.
- **Nima qilindi (oddiy tilda):** O'qituvchi "har seshanba 10:00, 80 daqiqa" deb kiritsa, mavzular avtomatik
  jadvalga joylashadi (avval ko'rib chiqib, keyin saqlanadi). Har topshiriq uchun "o'z vaqtida / kechikkan /
  mashq / yopiq" qarori bitta funksiyada; mustaqil topshiriqlarga guruh bo'yicha muddat.
- **Ishlatilgan skill'lar va nima uchun:** clocks-and-time (chegaralar soniyagacha testda, Asia/Tashkent),
  floating-point (jarima `Decimal`, 0.01, yarmi yuqoriga — float emas).
- **Yangi texnologiya / tushuncha:** yarim ochiq vaqt oralig'i [ochilish, yopilish); qo'lda yopishda lahzani saqlash.
- **Ertalab nimani ko'rish kerak:** `docs/ARCHITECTURE.md` — ACC-06 shartnomasi (I2/I3 shunga tayanadi).
- **Savollar / bloklar:** yo'q.

### 2026-11-23 — custom run'lar 1–3 (I1 boshlandi)
- **Bajarilgan issue'lar va PR:** #57 (PR #73), #58 (#74), #59 (#75), #60 (#76, #77), #61 (#78), #62 (#79), #63 (#80), #64 (#81). 14 ball.
- **Nima qilindi (oddiy tilda):** Guruhlar backend'i deyarli tayyor: o'qituvchi guruh yaratadi, havola beradi, talaba
  havola orqali so'rov yuboradi, o'qituvchi tasdiqlaydi yoki rad etadi, talabani boshqa guruhga o'tkazadi; guruh
  sozlamalari (AI tutorni bir tugma bilan o'chirish) va mavzular bo'yicha kirish oynalari (yopiq/hozir/jadval).
- **Ishlatilgan skill'lar va nima uchun:** data-modeling-discipline va schema-reviewer (bitta faol guruh — DB'da),
  auth-and-authorization va security-reviewer ×3 (IDOR, token faqat xesh, logda niqob, throttle talaba bo'yicha),
  isolation-anomalies (parallel test **deadlock** ni ushladi → `FOR NO KEY UPDATE`), clocks-and-time (DB soati
  `Now()`, oyna chegaralari).
- **Yangi texnologiya / tushuncha:** yangi kutubxona yo'q. Tushunchalar: partial unique index, `FOR NO KEY UPDATE`,
  cursor sahifalash, ikki darajali sozlamalar. Dars `docs/learn/sections.md` — #71 da.
- **Ertalab nimani ko'rish kerak:** `content/course.yaml` dagi `defaults:` (AI chegarasi `explain` — o'zgartirish mumkin).
- **Savollar / bloklar:** yangi blok yo'q.

### 2026-11-23 — custom run (R0 ni yopish)
- **Bajarilgan issue'lar va PR:** R0-15 (#19) → PR #53; R0-16 (#20) → PR #54. Ikkalasi `needs:owner` (egasi merge qiladi).
- **Nima qilindi (oddiy tilda):** Platformani serverda ishga tushirish uchun hamma narsa tayyorlandi: konteyner
  "retseptlari", eshik (Caddy), deploy skripti, kunlik zaxira va tiklash, hamda egasi uchun qadamma-qadam yo'riqnoma.
  Server yo'q bo'lgani uchun skriptlar soxta docker bilan sinaldi.
- **Ishlatilgan skill'lar va nima uchun:** docker-build-strategies va docker-compose-patterns (root'siz image, RAM limiti),
  docker-destructive-guardrails (tiklash `--yes` talab qiladi, oldin joriy holat saqlanadi), security-discipline
  (secret faqat serverdagi .env, workflow'da injection yo'q), idempotency-and-side-effects (takroriy deploy xavfsiz).
- **Yangi texnologiya / tushuncha:** `docs/learn/server.md`, `docs/learn/caddy.md`, ADR-0004 (uvicorn, deploy usuli).
- **Ertalab nimani ko'rish kerak:** PR #53 → merge, keyin #54. Kompyuteringizda `docker compose -f deploy/compose.prod.yaml --env-file <sinov env> build`.
- **Savollar / bloklar:** deploy usuli (self-hosted runner yoki SSH); zaxirani boshqa joyga nusxalash.

### 2026-11-23 — kunduzgi run 3/3 (navbatdan tashqari)
- **Bajarilgan issue'lar va PR:** R0-10 (#14) → PR #48; R0-11 (#15) → PR #49 (ikkalasi `merge-if-green.sh` bilan). 3 ball.
- **Nima qilindi (oddiy tilda):** Talaba brauzerda ro'yxatdan o'ta, kira, parolini almashtira oladi (rozilik matni va
  siyosat sahifasi bilan). Backend'ga siyosat versiyasini beruvchi kichik endpoint qo'shildi.
- **Ishlatilgan skill'lar va nima uchun:** testing-with-discernment (brauzer oqimi e2e, soxta API chegarasi aniq yozildi),
  security-discipline + security-reviewer (logout xatosi va majburiy parol almashtirish tuzatildi; Hemis ID band xabari
  ma'lum xavf sifatida SECURITY.md ga yozildi).
- **Yangi texnologiya / tushuncha:** `docs/learn/react-typescript.md` (kirish sahifalari bo'limi).
- **Ertalab nimani ko'rish kerak:** ro'yxatdan o'tish formasi va `/policy` (lokal `npm run dev`); #34 tuzatishini qo'llash.
- **Savollar / bloklar:** siyosatdagi "Mas'ul shaxs" uchun aloqa ma'lumoti kerak (PROGRESS).

### 2026-11-23 — kunduzgi run 2/3 (navbatdan tashqari)
- **Bajarilgan issue'lar va PR:** R0-08 #12 → PR #44; R0-09 #13 → PR #45; R0-17 #21 → PR #46 (4 ball: M + 2 S).
- **Nima qilindi (oddiy tilda):** Parolni tiklash (bir martalik, 24 soatlik vaqtinchalik parol; talaba yangisini
  qo'ymaguncha hech narsa ochilmaydi), admin o'qituvchi akkauntini yaratadi va talaba limitini belgilaydi,
  DRF, Caddy, Celery/Channels darslari.
- **Ishlatilgan skill'lar va nima uchun:** auth-and-authorization (kim kimni tiklaydi — `policies.py`, fail closed),
  data-modeling-discipline (NULL-xavfsiz CHECK — test xatoni topdi), security-reviewer ikki marta (qator qulfi,
  vaqtinchalik parol muddati, audit atomikligi, cheklovlar).
- **Yangi texnologiya / tushuncha:** `docs/learn/drf.md`, `caddy.md`, `celery-channels.md`.
- **Ertalab nimani ko'rish kerak:** `backend/apps/accounts/policies.py` (SRS 2.2 ga mosligi).
- **Savollar / bloklar:** yangi yo'q.

### 2026-11-23 — kunduzgi run 1/3 (navbatdan tashqari)
- **Bajarilgan issue'lar va PR:** R0-06 #10 → PR #37; R0-07 #11 → PR #39 (4 ball: 2 M). Skript bilan merge.
- **Nima qilindi (oddiy tilda):** Talaba ro'yxatdan o'tishi (rozilik bilan) va kirish/chiqish API'si tayyor.
  5 marta xato paroldan keyin 15 daqiqa blok — ham saytda, ham admin panelda. API "pasporti" (`docs/openapi.yaml`).
- **Ishlatilgan skill'lar va nima uchun:** auth-and-authorization, security-discipline, parse-dont-validate,
  clocks-and-time (soxta soat bilan blok muddati). security-reviewer ikki marta: muhim topilma — parallel so'rovlar
  bilan blokni aylanib o'tish (atomik hisoblagich bilan tuzatildi) va admin login'da IP chegarasi yo'qligi.
- **Yangi texnologiya / tushuncha:** drf-spectacular (ADR-0003) — `docs/learn/openapi.md`; `docs/learn/sessions-csrf.md`.
- **Ertalab nimani ko'rish kerak:** #38 (Hemis ID tasdiqlash — qaror), #34 (main-guard yolg'on signal).
- **Savollar / bloklar:** #38.

### 2026-11-22 — tungi run 2/2
- **Bajarilgan issue'lar va PR:** R0-05 #9 → PR #33; R0-13 #17 → PR #35 (4 ball: 2 M). Skript bilan merge.
- **Nima qilindi (oddiy tilda):** Har rol uchun ruxsat "qulflari" va `/admin/` boshqaruv paneli: unga faqat super
  admin va admin kiradi, parol xeshi ko'rinmaydi, rol o'zgarishi jurnalga yoziladi. Kurs kontenti formati (ADR-0002)
  va `import_content` buyrug'i: fayllardagi ma'ruzalar bazaga xavfsiz va takrorlansa ham bir xil natija bilan yuklanadi.
- **Ishlatilgan skill'lar va nima uchun:** auth-and-authorization (rol va obyekt darajasi ajratildi),
  security-reviewer agenti (Group admin va Django perm'lari orqali aylanib o'tish, o'zini pasaytirish, faollik auditi —
  tuzatildi), idempotency-and-side-effects (upsert tabiiy kalit bo'yicha), error-handling-as-design (`fayl:qator`).
- **Yangi texnologiya / tushuncha:** PyYAML — `docs/learn/content-format.md`; `docs/learn/roles-permissions.md`.
- **Ertalab nimani ko'rish kerak:** `.gitleaksignore` ga yangi qator (PR #35) — test markeri, secret emas.
- **Savollar / bloklar:** yo'q.

### 2026-11-22 — tungi run 1/2
- **Bajarilgan issue'lar va PR:** R0-04 #8 → PR #28; R0-03 #7 → PR #29; R0-14 #18 → PR #30; R0-12 #16 → PR #31.
  Hammasi `merge-if-green.sh` bilan merge qilindi (5 ball: 1 M + 3 S).
- **Nima qilindi (oddiy tilda):** Foydalanuvchi modeli (login — Hemis ID, parol Argon2) va loyihaning birinchi
  migratsiyasi; kompyuteringiz uchun `compose.yaml`; JSON loglar (shaxsiy ma'lumot yashiriladi) va `/readyz`;
  o'zgartirib ham, o'chirib ham bo'lmaydigan audit jurnali.
- **Ishlatilgan skill'lar va nima uchun:** data-modeling-discipline (qoidalar bazada CHECK/trigger bilan),
  migration-safety (har migratsiya `zero` gacha qaytarib sinaldi), unicode-pitfalls (oʻ/gʻ va apostrof
  variantlari, NFC), observability-by-default (liveness/readiness ajratildi, health probe shovqini o'chirildi),
  docker-compose-patterns. `schema-reviewer` agenti User sxemasida 4 ta tuzatish topdi — kiritildi.
- **Yangi texnologiya / tushuncha:** `docs/learn/custom-user-argon2.md`, `docs/learn/docker.md`, `docs/learn/observability.md`.
- **Ertalab nimani ko'rish kerak:** kompyuteringizda `docker compose up -d db redis` → `docker compose ps` (healthy).
- **Savollar / bloklar:** yangi blok yo'q (PROGRESS'dagi eski savollar o'z kuchida).

### 2026-11-21 — interaktiv (birinchi sessiya)
- **Bajarilgan issue'lar va PR:** label'lar; issue'lar #5–#21 (R0-01..R0-17), #4 (kunlik hisobotlar);
  R0-01 (#5) → PR #22; R0-02 (#6) → PR #23. Ikkalasi `needs:owner`.
- **Nima qilindi (oddiy tilda):** Backend (Django) va frontend (React) uchun bo'sh, lekin to'liq
  sozlangan "skelet" qurildi: testlar, lint, turlar tekshiruvi va GitHub'dagi `ci` avtomatik tekshiruvi.
  Backend kerakli sozlamasiz ishga tushmaydi (fail fast). Frontend'dagi hamma matn `uz.json` faylida.
- **Ishlatilgan skill'lar va nima uchun:** think-before-coding (oldin dizayn: liveness va readiness
  ajratildi), testing-with-discernment (fail fast mock bilan emas, haqiqiy alohida jarayonda tekshirildi),
  security-discipline (prod'da zaif kalit va `*` host taqiqlandi; pip-audit DRF zaifligini topdi → 3.18).
- **Yangi texnologiya / tushuncha:** `docs/learn/django.md`, `docs/learn/react-typescript.md`.
- **Ertalab nimani ko'rish kerak:** PR #22 (ci.yml, CLAUDE.md §4, `.gitleaksignore`) → merge; keyin #23.
  Setup skriptni muhitga qo'yish (`docs/prompts/setup-script.sh`, #23 dagi versiya).
- **Savollar / bloklar:** yo'q. (Avval `merge-if-green.sh` bulutda ishlamaydi deb o'ylangan edi — noto'g'ri:
  `gh auth status` xato ko'rsatsa ham `gh api` proxy orqali ishlaydi; PR #24 skript bilan merge qilindi.)

## Shablon

### YYYY-MM-DD — <run turi: tungi / interaktiv / review>
- **Bajarilgan issue'lar va PR:** #...
- **Nima qilindi (oddiy tilda):**
- **Ishlatilgan skill'lar va nima uchun:**
- **Yangi texnologiya / tushuncha:** (dars havolasi)
- **Ertalab nimani ko'rish kerak:**
- **Savollar / bloklar:**
