# Kunduzgi run prompti (egasi boshqaradi)

> Gibrid tartib (egasining 2026-11-27 qarori, "C"): kechasi avtomatik tungi run'lar (`nightly-run.md`), kunduzi —
> egasi o'zi ochadigan sessiyalar. Kunduzgi sessiya soni haftalik limit sarfiga qarab tanlanadi (pastdagi jadval).
> Ishga tushirish: yangi Claude Code sessiyasi (claude.ai/code'da repo bilan yoki lokal kompyuterda repo papkasida) va
> `/kunduzgi-run` (ixtiyoriy: issue raqami yoki vazifa, masalan `/kunduzgi-run #165`).

## Haftalik limitga qarab nechta kunduzgi sessiya

Egasi claude.ai → Settings → Usage'da haftalik foydalanish foizini ko'radi. Kutilgan sarf = hafta kuni / 7
(dushanba — 14%, chorshanba — 43%, juma — 71%, yakshanba — 100%). Tungi run'lar uchun zaxira qoladi:

| Haftalik sarf | Bugun kunduzi |
| --- | --- |
| kutilgandan 15 punktdan ko'proq past | 2 sessiya |
| kutilganga yaqin (±15 punkt) | 1 sessiya |
| kutilgandan 15 punktdan ko'proq yuqori | faqat 15 daqiqa: qaror, savollarga javob, `needs:owner` merge (sessiya ochilmaydi) |

Misol: chorshanba, sarf 25% → kutilgan 43% dan 18 punkt past → 2 sessiya.
5 soatlik limit tugasa: sessiya ishni draft PR va issue izohi bilan to'xtatadi (pastda, 6-band), keyingi sessiya davom etadi.

## Kun va tun ish taqsimoti

- **Kunduzi** (egasi yonida): egasining qarori kerak bo'lgan tasklar (`status:blocked` javoblari, talqin, UX), katta
  funksiyalar (I4: AI tutor, jonli monitoring), `needs:owner` PR'lar (egasi darrov ko'rib merge qiladi), lokal Docker'da
  butun tizimni sinash.
- **Kechasi**: kontent, testlar, kichik va o'rta tasklar, hujjatlar va dashboard.
- Kunduzgi sessiya olgan issue'ga `run:day` label'i qo'yiladi — tungi run uni olmaydi. Tugaganda label olinadi.

```text
Sen L1 · MLab repoda egasi bilan kunduzgi run bajarayapsan. Egasi yonida — qaror kerak bo'lsa, qisqa savol ber
(2–3 variant va tavsiyang bilan). Barcha javoblar o'zbek tilida. Talablarning yagona manbai docs/SRS.md.

1. `git checkout main && git pull`. CLAUDE.md va docs/PROGRESS.md'ni o'qi; kodni o'rganish docs/CODEMAP.md'dan.
   docs/prompts/nightly-run.md'dagi "Limitni tejash" qoidalari bu yerda ham amal qiladi.
2. Vazifa: egasi issue yoki vazifa aytgan bo'lsa — o'sha. Aytmagan bo'lsa: ochiq status:blocked savollar va
   needs:owner PR'larni egasiga qisqa ro'yxat qilib ko'rsat (u hozir hal qila oladi), keyin "Kun va tun ish taqsimoti"
   bo'yicha kunduzga mos status:ready issue'ni taklif qil va egasi tanlasin.
3. Tanlangan issue: status:in-progress va run:day label'lari. Boshqa sessiyaning status:in-progress issue'sini
   (6 soatdan yangi) yoki run:day issue'sini olma.
4. CLAUDE.md 5–7-bo'limlari: claude/<issue>-<nom> branch, avval test, kod, tegishli testlar; PR ready qilishdan oldin
   to'liq testlar va e2e. Merge faqat scripts/merge-if-green.sh (fonda; kutish paytida keyingi qadam).
   needs:owner PR — egasiga havola ber, u merge qiladi.
5. Task tugagach: run:day label'ini ol, issue yopilganini tekshir. Egasi davom et desa — 2-bandga qayt.
6. Sessiya oxirida (yoki 5 soatlik limit yaqinlashsa): tugamagan ish — draft PR va issue'ga "to'xtash nuqtasi" izohi,
   run:day label'i olinadi (tungi run davom ettira olsin). "📋 Kunlik hisobotlar" (#4) issue'siga
   "<sana> — kunduzgi run" izohi: merge bo'lgan PR'lar va talab ID'lari, egasining qarorlari, tugamagan ish.
   PROGRESS.md, JOURNAL va dashboard'ni tungi run yangilaydi (kunduzgi hisobot izohidan oladi).

Qat'iy taqiqlar: CLAUDE.md 5-bo'lim (main'ga push yo'q, merge faqat skript bilan, testni o'chirma, .env'ni o'qima,
haqiqiy shaxsiy ma'lumot ishlatma, Gemini'ni chaqirma, talaba kodini servis jarayonida bajarma).
"Ruxsat" va approved:* label'ini o'zing qo'yma — faqat egasi.
```
