# Tungi run prompti (scheduled task)

> Scheduled task'ning "Instructions/Prompt" maydoniga to'liq nusxalanadi.
> Jadval: Custom cron `CRON_TZ=Asia/Tashkent 47 1 * * 1-6` (dushanba–shanba 01:47, Toshkent vaqti; yakshanba — haftalik review).
> Model: Sonnet (oddiy tasklar). Repo: shu repo. Muhit: loyiha muhiti.

```text
Sen L1 · MLab repoda tungi avtonom run bajarayapsan. Egasi uxlayapti, savol bera olmaysan.
Talablarning yagona manbai docs/SRS.md; joriy reliz va tasklar docs/BACKLOG.md va GitHub Issues'da.

1. git pull qil. CLAUDE.md, docs/PLAYBOOK.md va docs/PROGRESS.md'ni o'qi.
   Ochiq "alert:main-guard" issue bo'lsa, avval uni tekshir: commit seniki bo'lsa,
   revert PR och va issue'ga izoh yoz; egasiniki bo'lsa, issue'ga izoh yozib o't.
   docs/RECOVERY.md bo'yicha sog'liq tekshiruvini qil va natijani PROGRESS.md'ga yoz.
   - Sariq: yangi task olma, avval tuzatish PR och (ko'pi bilan 2 urinish).
   - Qizil: kodni o'zgartirma. Tashxis, alert:red-light issue va docs/incidents hisobotini
     yoz, variantlar va nima yo'qolishini ko'rsat, to'xta. Ochiq alert:red-light issue'da
     egasining "Ruxsat: X" izohi bo'lsa — faqat o'sha variantni RECOVERY.md bo'yicha bajar.
2. GitHub Issues'dan status:ready label'li, bog'liqligi yopilgan eng kichik issue'ni ol
   va uni status:in-progress qil. Ready issue bo'lmasa: backlog'ni ko'rib chiq,
   PROGRESS.md'ga yoz va to'xta.
3. Issue bitta runga sig'maydigan bo'lsa: kod yozma. Uni subtask issue'larga bo'l
   (har biri acceptance criteria bilan, status:ready), asl issue'ga izoh yoz va to'xta.
4. claude/<issue-raqami>-<qisqa-nom> branch och va darhol draft PR yarat.
5. CLAUDE.md 5 va 8-bo'limlariga amal qil: avval test, keyin kod; kerakli skill'larni yukla.
   Har tugagan bosqichni alohida commit qilib push qil.
6. Testlar, lint, type check yashil bo'lgach: hujjatlarni yangila (CHANGELOG, OpenAPI,
   docs/learn, kerak bo'lsa ADR), PR tavsifini shablon bo'yicha to'ldir, PR'ni ready for review qil.
   Keyin faqat skript orqali merge: scripts/merge-if-green.sh <PR raqami>.
   0 — merge bo'ldi, issue yopildi; 1 — qizil: sababini tuzat (ko'pi bilan 2 urinish), testni o'chirma;
   2 — tekshiruvlar tugamadi: keyingi taskka o't, run oxirida qayta urin.
   PR needs:owner bo'lsa — issue'ni status:review qil va kunlik hisobotda ko'rsat.
7. Limit yetsa 2-qadamga qayt. Yetmasa yangi issue boshlama.
8. Yakunda docs/PROGRESS.md va docs/learn/JOURNAL.md'ni yangila (alohida kichik PR, skript bilan merge).
9. Kunlik hisobot: "📋 Kunlik hisobotlar" issue'siga izoh yoz (bo'lmasa yarat, label: report):
   sog'liq, merge bo'lgan PR'lar va talab ID'lari, needs:owner PR'lar, status:blocked savollar,
   keyingi tasklar, egasi o'qishi kerak bo'lgan dars. 10–15 qator, o'zbek tilida, oddiy tilda.

Qat'iy taqiqlar: main'ga push qilma, PR'ni skriptdan boshqa yo'l bilan merge qilma, tekshiruvni o'tkazish uchun
testni o'chirma yoki chegarani tushirma, .env'ni o'qima, secret yozma,
haqiqiy shaxsiy ma'lumot ishlatma, Gemini'ni chaqirma (testlarda AI_PROVIDER=fake),
talaba kodini servis jarayonida bajarma. Qaror egasiga tegishli bo'lsa (arxitektura, pul,
xavfsizlik, ma'lumot o'chirish): issue'ni status:blocked qil, savolni issue va PROGRESS.md'ga
yoz, keyingi ready issue'ga o't.
```
