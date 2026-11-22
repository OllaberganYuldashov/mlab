# RECOVERY — qizil chiroq va ishlaydigan versiyaga qaytish

> Bu yo'riqnoma loyiha xavf ostida qolganda ishlatiladi. Asosiy qoida:
> **qizil chiroqni Claude o'zi aniqlaydi, hisobot beradi, lekin ortga qaytishni faqat egasining ruxsati bilan qiladi.**
> Ortga qaytish har doim **eng kichik** qadamdan boshlanadi va hech qachon tarixni o'chirmaydi.

## 1. Yashil nuqtalar (ishlaydigan versiyalar)

- `known-good` workflow main'dagi har commit uchun secret-scan, main-guard va ci yashil bo'lsa, unga teg qo'yadi:
  `good-YYYY-MM-DD-HHMM-<sha7>` (Toshkent vaqti).
- Har hafta `weekly-backup` reponing to'liq nusxasini saqlaydi (90 kun) — tarix buzilgan holatlar uchun.
- Deploy bosqichida: prod'ga chiqqan har versiya ham teg bilan belgilanadi va qayta deploy qilish mumkin bo'ladi.

## 2. Sog'liq tekshiruvi — har run boshida

Claude har run boshida, yangi task olishdan oldin quyidagilarni tekshiradi va natijani PROGRESS.md'dagi
"Sog'liq" qatoriga yozadi:

| Tekshiruv | Qanday |
| --- | --- |
| main'dagi oxirgi CI | GitHub Actions natijasi (REST API) |
| main'da testlar | Sessiyada to'liq test to'plamini ishga tushirish |
| Ilova ishga tushadimi | Lokal ishga tushirish yoki smoke test |
| Regressiya bug'lari | Oxirgi 7 kunda ochilgan `type:bug` issue'lar soni, qayta ochilganlar |
| Rad etilgan PR'lar | Oxirgi 7 kunda merge qilinmay yopilgan PR'lar |
| Tuzatish urinishlari | PROGRESS.md'dagi "urinishlar" hisoblagichi |
| main-guard | Ochiq `alert:main-guard` issue'lar |

## 3. Chiroqlar

### Yashil — odatdagi ish
main yashil, testlar o'tadi, ilova ishlaydi.

### Sariq — Claude o'zi tuzatadi (ko'pi bilan 2 urinish)
- main'da CI yoki test birinchi marta qizil bo'ldi;
- bitta regressiya bug topildi;
- bitta PR rad etildi.

Claude yangi funksiya olmaydi, avval tuzatish PR ochadi. Har urinish PROGRESS.md'da hisoblanadi.

### Qizil — Claude TO'XTAYDI, hisobot beradi, ruxsat kutadi
Quyidagilardan **bittasi** yetarli:

1. main 2 urinishdan keyin ham qizil (CI yoki testlar).
2. Ilova ishga tushmaydi yoki deploy'dan keyingi smoke test yiqildi va 1 urinishda tuzalmadi.
3. Oxirgi 7 kunda 5 va undan ko'p regressiya bug'i, yoki ochiq bug'lar soni 2 hafta ketma-ket o'smoqda.
4. Bir xil bug 2 marta qayta ochilgan.
5. Ketma-ket 3 PR egasi tomonidan rad etilgan yoki egasi "noto'g'ri yo'nalish" degan.
6. main-guard force push yoki tarix buzilishini aniqlagan.
7. Prod ma'lumotlari buzilishi yoki yo'qolishi xavfi (masalan, xato migratsiya).

> Secret oqib ketsa — bu alohida tartib (SECURITY.md: darhol rotate). Kod ortga qaytarilmaydi, lekin qizil chiroq hisoboti beriladi.

## 4. Qizil chiroqda Claude nima qiladi

1. **Yangi funksiya ishini to'xtatadi.** Faqat tashxis qo'yadi, kodni o'zgartirmaydi.
2. **Tashxis:** muammo qaysi PR'dan boshlanganini topadi. Buning uchun eng yaqin `good-*` teglarda testlarni ishga tushiradi (bisect).
3. **Hisobot** — `alert:red-light` issue va `docs/incidents/YYYY-MM-DD-qizil-chiroq.md`:
   - Nima bo'ldi: belgilar, dalillar (CI havolalari, test natijalari)
   - Qachondan beri: oxirgi yashil nuqta va muammoli PR'lar ro'yxati
   - Sabab haqidagi taxmin
   - **Variantlar** (pastdagi zinapoya bo'yicha) va har birida **nima yo'qoladi**
   - Tavsiya
4. **Egasining ruxsatini kutadi.** Ruxsatsiz hech qanday ortga qaytish qilinmaydi.

## 5. Ortga qaytish zinapoyasi — eng kichigidan boshlab

| Daraja | Nima qilinadi | Nima yo'qoladi |
| --- | --- | --- |
| A. Oldinga tuzatish | Muammoni yangi PR bilan tuzatish | Hech narsa |
| B. Bitta PR'ni bekor qilish | `git revert -m 1 <merge-commit>` → yangi PR | Faqat shu PR'dagi o'zgarish |
| C. Bir nechta PR'ni bekor qilish | Muammoli PR'larni teskari tartibda revert → bitta PR | Faqat shu PR'lar |
| D. Yashil nuqtaga qaytish | `claude/rollback-<teg>` branch'ida `git read-tree -u --reset <teg>` → bitta commit, kod daraxti tegdagi holatga to'liq qaytadi → PR. (`git revert <teg>..main` merge commit'lar sabab ishlamaydi) | Tegdan keyingi hamma o'zgarish (lekin tarixda va arxiv branch'da saqlanadi) |
| E. Zaxiradan tiklash | Faqat tarix buzilgan bo'lsa: `weekly-backup` bundle'dan yo'qolgan commit'lar alohida branch'ga → PR | Zaxiradan keyingi, boshqa joyda saqlanmagan ishlar |

Qoidalar:
- **Har doim PR orqali.** main'ga push, `reset --hard` + force push — hech qachon.
- D va E'dan oldin joriy holat `claude/archive-YYYY-MM-DD` branch'ida saqlanadi — hech narsa butunlay yo'qolmaydi.
- Bekor qilingan funksiyalar keyin qayta qilish uchun yangi `status:ready` issue bo'lib yoziladi.

## 6. Ruxsat qanday beriladi

- Egasi `alert:red-light` issue'ga izoh yozadi: **`Ruxsat: B`** (yoki C, D, E), yoki shuni Claude bilan sessiyada aytadi.
- Claude ham egasining GitHub hisobi nomidan ishlaydi, shuning uchun **Claude hech qachon o'zi "Ruxsat" deb yozmaydi**
  va `approved:*` label qo'ymaydi. Ruxsat sifatida faqat egasi tomonidan yozilgan izoh yoki sessiyadagi xabar qabul qilinadi.
- Ruxsat bo'lmasa, Claude har run boshida qizil holatni tekshiradi, hisobotni yangilaydi va boshqa ish qilmaydi.

## 7. Ortga qaytgandan keyin

1. Rollback PR'ida testlar va CI yashil ekani ko'rsatiladi. Egasining "Ruxsat: X" izohidan keyin Claude uni faqat
   `scripts/merge-if-green.sh` orqali merge qiladi (himoyalangan fayllar o'zgargan bo'lsa — egasi merge qiladi).
2. `known-good` yangi yashil nuqta qo'yadi.
3. `docs/LESSONS.md`ga post-mortem: nima bo'ldi, nega erta sezilmadi, qaysi qoida qo'shiladi.
4. Bekor qilingan ishlar kichikroq task'larga bo'linib backlog'ga qaytadi.
5. `alert:red-light` issue yopiladi.

## 8. Prod (deploy bosqichidan keyin)

Deploy workflow'i `workflow_dispatch` orqali istalgan `good-*` tegni qayta deploy qila oladigan qilib yoziladi.
Prod'ni ortga qaytarish ham faqat egasining ruxsati bilan.
