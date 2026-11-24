# Guruhlar, a'zolik va kirish oynalari (I1 darsi)

> Kim uchun: loyiha egasi. Maqsad: `apps/sections` qanday ishlashini va nega shunday qurilganini tushunish.
> O'qish vaqti: ~15 daqiqa.

## 1. Asosiy tushunchalar

| Model | Nima | Muhim qoida |
| --- | --- | --- |
| `Section` (guruh) | O'qituvchining talabalar guruhi: nom, yo'nalish, sig'im, qo'shilish yoqilganmi | Egasi faqat o'qituvchi; sozlamalardan faqat kursdan farqi saqlanadi |
| `Membership` (a'zolik) | Talaba ↔ guruh: `pending` → `approved` / `rejected` → `removed` | Talabada **bitta faol** a'zolik; yozuvlar o'chirilmaydi — tarix |
| `AccessWindow` (oyna) | Guruh × mavzu laboratoriyasi qachon ochiq | Yo'q bo'lsa — yopiq (ACC-02) |
| `IndependentDeadline` | Guruh × mustaqil topshiriq (`A01..A99`) muddati | Bitta guruhda bitta kodga bitta muddat |

## 2. Invariantlar bazada, kodda emas

Qoidani faqat Python'da tekshirsak, ikki parallel so'rov uni buzishi mumkin. Shuning uchun asosiylari PostgreSQL'da:

- **Bitta faol a'zolik** — *partial unique index*: `UNIQUE (student) WHERE status IN ('pending','approved')`.
  Ikki havolaga bir vaqtda bosilsa ham, bittasi `IntegrityError` oladi va servis uni "boshqa guruhdasiz" javobiga aylantiradi.
- **Qaror maydonlari holatga mos** — `CHECK`: `approved` bo'lsa `decided_at` va `decided_by` bor; `pending` bo'lsa yo'q.
- **Qaror so'rovdan oldin emas** — `CHECK (decided_at >= requested_at)`. Ikkala vaqt ham **bazaning soatidan** (`Now()`):
  Python soati va DB soati bir necha millisekund farq qilib, shu CHECK'ni buzgan edi.
- **Oyna vaqtlari rejimga mos** — `scheduled` da ikkala vaqt bor, `closed` da yo'q, yopilish ochilishdan keyin.

## 3. Qulflar va tartib (deadlock'siz)

Tasdiqlash sig'imni va o'qituvchining umumiy limitini tekshiradi. Buni "o'qi → tekshir → yoz" bilan qilsak, ikki o'qituvchi
oynasi bir vaqtda oxirgi joyni berib yuborishi mumkin. Shuning uchun qatorlar qulflanadi, **doim bir xil tartibda**:
o'qituvchi → guruh(lar) (`id` bo'yicha) → a'zoliklar. Qulf turi `FOR NO KEY UPDATE`: oddiy `FOR UPDATE` FK tekshiruvi bilan
to'qnashib deadlock bergan edi (testda ushlandi). Barcha a'zolik yozuvlari bitta joyda — `apps/sections/services.py`.

## 4. Qo'shilish tokeni

- 128 bit tasodifiy token, bazada faqat **SHA-256 xeshi** — baza sizib chiqsa ham havolalar ochilmaydi.
- To'liq token faqat yaratilgan javobda bir marta (`Cache-Control: no-store`); yangilansa eskisi darhol bekor.
- Loglarda token niqoblanadi: so'rov logida (`safe_path`), xato matnlarida (`mask_text`), uvicorn'ning o'z access log'i
  o'chirilgan (u JSON formatterdan o'tmas va tokenni ochiq yozardi — I1 yakuniy ko'rigida topildi).
- Cheklovlar: ko'rish IP bo'yicha keng (bir NAT ortidagi butun sinf), so'rov talaba bo'yicha.

## 5. Oynalar va vaqt

- Hamma vaqt `timestamptz` (UTC'da saqlanadi), ko'rsatish Asia/Tashkent'da. Oyna holati faqat bitta sof funksiyada:
  `window_state(window, at)` — `opens_at` lahzasida ochiq, `closes_at` lahzasida yopiq.
- Haftalik jadval (`plan_slots`) `zoneinfo` bilan hisoblaydi: "seshanba 10:00" har hafta Toshkent vaqti bo'yicha.
- Qo'lda yopilgan oyna yopilish lahzasini saqlaydi — kechikish muddati va mashq rejimi shu lahzadan hisoblanadi.
- Talaba sahifasi server vaqtini oladi va farqni hisobga oladi (kompyuter soati noto'g'ri bo'lsa ham to'g'ri sanaydi).

## 6. Real vaqt (WebSocket)

O'qituvchi oynani ochadi → tranzaksiya tugagach (`transaction.on_commit`) Redis orqali `section-<id>` guruhiga xabar →
talaba brauzeri `/api/me/next-window` ni qayta so'raydi. Xabarda ma'lumot yo'q, faqat "yangilan" signali — shuning uchun
ruxsat tekshiruvi HTTP endpoint'da qoladi. Ulanish 15 daqiqa yashaydi (keyin brauzer qayta ulanadi va ruxsat qayta
tekshiriladi); a'zolik bekor qilinsa soket darhol yopiladi. Ulanishda a'zolik guruhga qo'shilgandan keyin **qayta**
tekshiriladi: aks holda oradagi lahzada yuborilgan "yopil" xabari yo'qolishi mumkin edi.

## 7. Migratsiya saboqlari

- Katta jadvalga `CHECK` qo'shish butun jadvalni skanerlaydi va yozishni bloklaydi. Kichik jadvallarda (guruhlar) muammo
  emas. Audit jurnali tez o'sadi: keyingi safar `action` ro'yxati kengaytirilsa — `ADD CONSTRAINT ... NOT VALID`, keyin
  alohida `VALIDATE CONSTRAINT` (#95).
- Ortiqcha indeks — har yozishda qo'shimcha ish. `(section, topic)` unique indeksi `section` bo'yicha qidiruvni ham
  qoplaydi, shuning uchun alohida `section` indeksi olib tashlandi.

## 8. Qayerdan boshlab o'qish

`apps/sections/models.py` → `services.py` (a'zolik) → `windows.py` va `policy.py` (vaqt) → `consumers.py` (real vaqt).
Testlar talab ID'lari bilan nomlangan: `tests/sections/test_sec_*`, `test_acc_*`, `test_set_*`. To'liq matritsa —
`docs/iterations/I1.md`.
