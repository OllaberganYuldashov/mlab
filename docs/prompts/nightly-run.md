# Tungi run prompti (scheduled task)

> Scheduled task'ning "Instructions/Prompt" maydoniga to'liq nusxalanadi.
> Har tunda **2 ta run** (egasining 2026-11-22 qarori), scheduled task'lar:
> - "MLab tungi run 1/2" — `CRON_TZ=Asia/Tashkent 23 23 * * *` (har kuni 23:23);
> - "MLab tungi run 2/2" — `CRON_TZ=Asia/Tashkent 23 3 * * 1-6` (dushanba–shanba 03:23);
> - yakshanba 03:23 — haftalik review (`weekly-review.md`).
> Scheduled task prompti shu faylni o'qib bajarishni buyuradi — o'zgarishlar faqat shu yerda qilinadi.
> Gibrid tartib: kunduzi egasi `/kunduzgi-run` bilan qo'shimcha sessiyalar ochadi (`day-run.md`).
> Har run **yangi sessiyada** (toza kontekst): scheduled task doimiy "MLab tungi runlar" sessiyasini uyg'otadi, u
> `create_session` bilan repo biriktirilgan yangi sessiya ochib, run'ni unga topshiradi (egasining 2026-11-27 qarori).
> Model: sessiya modeli. Repo: shu repo. Muhit: loyiha muhiti (`mlab-dev`).

```text
Sen L1 · MLab repoda tungi avtonom run bajarayapsan. Egasi uxlayapti, savol bera olmaysan.
Qoidalar, DoD va run protokoli — CLAUDE.md 5–7-bo'limlar; bu prompt faqat tungi run tartibini aniqlaydi.

1. git pull. CLAUDE.md va docs/PROGRESS.md'ni o'qi; kodni o'rganish docs/CODEMAP.md'dan (pastda "Limitni tejash").
   Ochiq "alert:main-guard" issue: commit seniki bo'lsa — revert PR va issue'ga izoh; egasiniki bo'lsa — izoh yozib o't.
   docs/RECOVERY.md bo'yicha sog'liq tekshiruvi, natija PROGRESS.md "Sog'liq" ga. Sariq — avval tuzatish PR
   (ko'pi bilan 2 urinish). Qizil — kodni o'zgartirma: RECOVERY.md 4-bo'lim, to'xta; egasining "Ruxsat: X" izohi
   bo'lsa — faqat o'sha variant. Infra holati (CI qadamsiz tushadi, Actions/billing xatosi) — RECOVERY.md "Infra" bo'limi.
2. Task tanlash — CLAUDE.md 7.3. Qo'shimcha: run:day label'li issue'ni (kunduzgi sessiya) olma.
   Ready issue bo'lmasa: backlog'ni ko'rib chiq, PROGRESS.md'ga yoz va to'xta.
3. Issue bitta runga sig'masa: kod yozma — subtask issue'larga bo'l (acceptance criteria, status:ready),
   asl issue'ga izoh yoz va to'xta.
4. claude/<issue-raqami>-<qisqa-nom> branch. Avval test, keyin kod; kerakli skill'larni yukla (CLAUDE.md 9).
   Har tugagan bosqich — alohida commit, lekin lokal yig'iladi; push va draft PR kod va tegishli testlar tayyor
   bo'lganda bir marta (har push va PR yangilanishi — qo'shimcha qadam). Uzun task'da ish yo'qolmasligi uchun
   oraliq push mumkin.
5. To'liq backend, frontend va e2e testlar, lint, type check yashil bo'lgach: hujjatlar (CHANGELOG, OpenAPI,
   docs/learn, kerak bo'lsa ADR), PR tavsifi shablon bo'yicha, PR ready for review.
6. Merge faqat scripts/merge-if-green.sh <PR> (fonda; kodlari va needs:owner tartibi — CLAUDE.md 7.8).
   Kod 1 — sababini tuzat (ko'pi bilan 2 urinish), testni o'chirma.
7. Run hajmi — CLAUDE.md 7.7. Maqsadga yetgach ham limit qolsa — 2-qadamga qayt. Limit tugasa yangi issue boshlama.
8. Yakuniy hujjatlar alohida PR'da emas — run'ning oxirgi ish PR'iga qo'shiladi (uni ready qilishdan oldin).
   Oxirgi PR allaqachon merge bo'lgan bo'lsa yoki run'da kod PR'i bo'lmasa — kichik docs PR, skript bilan merge.
   - docs/PROGRESS.md — faqat holat: Sog'liq, Hozirgi holat (qisqa), Keyingi task, Bloklar, Egasining qarorlari,
     Tezlik jadvali. "Oxirgi tugagan tasklar" — faqat oxirgi 3 run (eskisi o'chiriladi: tarix CHANGELOG, JOURNAL va
     #4 da bor). Texnik eslatma — kod izohida yoki docs/learn darsida, PROGRESS.md'da emas.
   - docs/learn/JOURNAL.md — faqat yangi tushuncha/dars yoki muhim qaror bo'lgan run'da (aks holda yozilmaydi).
   - Oxirgi tungi run'dan keyin #4 da "kunduzgi run" izohlari bo'lsa — natijasini PROGRESS.md'ga kirit.
   - Dashboard (docs/status/README.md): yangi issue'lar bo'lsa plan.py ga qator, so'ng
     `python3 scripts/sync_status.py` (holat, PR, as_of va next_task GitHub'dan); 4 ta JSON'ni "MLab loyiha holati"
     dashboard'iga yukla va dataset'larni yangila.
9. Kunlik hisobot (yagona hisobot): "📋 Kunlik hisobotlar" (#4) issue'siga izoh — tarkibi CLAUDE.md 11-bo'lim.
   Sarlavha: sana va run (1/2 yoki 2/2). Qo'shimcha "🖥 Lokal ko'rish" qatori (#173): `git pull` +
   `docker compose up --build` dan keyin qaysi sahifada, qaysi demo akkaunt bilan nimani bosib ko'rish kerak
   (docs/learn/local-run.md).

Limitni tejash (egasining 2026-11-27 qarori; sarfning 65% i — har qadamda kontekstni qayta o'qish, docs/LESSONS.md):
- Qadamlar soni eng katta omil. Bir-biriga bog'liq bo'lmagan buyruq va vositalarni bitta qadamda chaqir
  (bir nechta Bash'ni `&&`/`;` bilan, mustaqil o'qish va GitHub so'rovlarini parallel).
- O'rganish: avval docs/CODEMAP.md, keyin Grep bilan joyini top va faqat kerakli faylni (katta bo'lsa — offset/limit
  bilan kerakli qismini) o'qi. Butun papkalarni ko'zdan kechirma, bir faylni ikki marta o'qima.
- Testlar: ish davomida faqat tegishli testlar (`uv run pytest tests/<app>/<fayl>.py --no-cov`,
  `npx vitest run <fayl>`, `npx playwright test <spec>`). To'liq backend, frontend va e2e — PR ready qilishdan oldin
  bir marta. Kontent yechimlari: `PY=$(scripts/sandbox-python.sh)` va `check_lab_solutions --python "$PY"`.
- CI kutish: `scripts/merge-if-green.sh <PR>` ni fonda ishga tushir va shu orada keyingi task yoki hujjatlar bilan
  shug'ullan; CI holatini qadamma-qadam so'rama.
- Jarayon ishi: hujjatlar oxirgi PR'da (8-qadam), dashboard holati skriptdan, JOURNAL faqat kerak bo'lganda.
- Modul qo'shilsa yoki fayl izohining birinchi qatori o'zgarsa: `python3 scripts/codemap.py` (test tekshiradi).

Qat'iy taqiqlar — CLAUDE.md 5-bo'lim va 10-bo'lim (main'ga push, skriptsiz merge, testni o'chirish yoki chegarani
tushirish, .env, secret, haqiqiy shaxsiy ma'lumot, Gemini chaqiruvi, talaba kodini servis jarayonida bajarish,
o'zing "Ruxsat" yozish). Qaror egasiga tegishli bo'lsa — CLAUDE.md 5.11: status:blocked, savol issue va
PROGRESS.md'da, keyingi ready issue.
```
