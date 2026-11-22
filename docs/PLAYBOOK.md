# PLAYBOOK — Claude bilan senior darajada loyiha yuritish qoidalari

> "Mother of Projects" qo'llanmasining repo uchun qisqa nusxasi. Har sessiya shu qoidalarga amal qiladi.
> Loyihaga xos sozlamalar `CLAUDE.md`da.

## 1. Rollar

| Rol | Kim | Vazifasi |
| --- | --- | --- |
| Product Owner / CTO | Egasi (siz) | G'oya, yo'nalish, kunlik hisobotni o'qish, savollarga javob berish, `needs:owner` PR'larni merge qilish |
| Tech lead va jamoa | Claude | Reja, arxitektura, kod, test, hujjat, hisobot, o'qitish |
| Mustaqil reviewer | Agentlar: security-reviewer, schema-reviewer, incident-thinker | Muhim o'zgarishlarni alohida tekshirish |
| Xotira | Repo va GitHub | Holat, qarorlar, tarix, zaxira |

## 2. Tamoyillar

1. **Sodda boshlash.** Avval monolit va oddiy vositalar; murakkablik faqat aniq ehtiyoj bo'lganda.
2. **Boring by default.** Yangi texnologiya faqat ADR bilan.
3. **Mayda tasklar.** Har task bitta sessiyada to'liq tugaydi: test, commit, push, hujjat.
4. **Test birinchi.** Bug tuzatishdan oldin uni takrorlaydigan test.
5. **Xavfsizlik refleks.** Secret chat, repo, log, PR va issue'da bo'lmaydi.
6. **Har ish — o'quv materiali.** Har texnologiya egasi uchun `docs/learn/`da tushuntiriladi.
7. **Hamma narsa yoziladi.** Qarorlar ADR'da, holat PROGRESS.md'da, tajriba LESSONS.md'da.

## 3. Bosqichlar va qaror nuqtalari

| Bosqich | Claude | Egasi | Natija |
| --- | --- | --- | --- |
| 0. G'oya | ≤5 savol, PRD | G'oyani beradi, PRD'ni tasdiqlaydi | docs/PRD.md |
| 1. Arxitektura | 2–3 variant + tavsiya | Tanlaydi | docs/ARCHITECTURE.md, docs/adr/ |
| 2. Backlog | Issue'lar, acceptance criteria | Prioritet | GitHub Issues |
| 3. Skelet | CLAUDE.md to'ldiradi, CI, Docker, tuzilma | Repo, muhit, fayllarni yuklash | Skelet PR |
| 4. Runlar | Mayda tasklar | Ertalab hisobot o'qiydi | PR'lar |
| 5. Qabul | PR tavsifi | Merge yoki izoh | main |
| 6. Milestone | Review, retro, skill yangilash | Baholaydi | LESSONS.md |
| 7. Release | deploy-checklist, CI/CD | Deploy'ni tasdiqlaydi | Server |

## 4. Tungi run

- Jadval (2026-11-22): har tunda **2 run** — 23:23 (har kuni) va 03:23 (dushanba–shanba), Asia/Tashkent.
- Haftalik review: yakshanba 03:23 — faqat code-review, tech-debt, LESSONS retro.
- Run hajmi: kamida 2 ta `size:M` yoki 4 ta `size:S`; limit qolsa davom etadi.
- Pro limiti chat va Claude Code o'rtasida umumiy (egasi kunduzi kam ishlatadi).
- Protokol: `CLAUDE.md` 7-bo'lim (Definition of Done — 6-bo'lim). Prompt: `docs/prompts/nightly-run.md`.

## 5. Xotira fayllari

| Fayl | Nima uchun |
| --- | --- |
| CLAUDE.md | Qoidalar, buyruqlar, DoD, skill jadvali |
| docs/PRD.md | Nima quriladi va kim uchun |
| docs/ARCHITECTURE.md | Tizim tuzilishi |
| docs/adr/ | Har muhim qaror |
| docs/PROGRESS.md | Qayerda to'xtadik, keyingi task, bloklar |
| docs/CHANGELOG.md | O'zgarishlar tarixi |
| docs/TESTING.md | Test strategiyasi |
| docs/SECURITY.md | Secret'lar qayerda va qanday |
| docs/LESSONS.md | Haftalik retro |
| docs/learn/ | Egasi uchun darslar va JOURNAL.md |

## 6. Test standarti

| Daraja | Nima | Qachon |
| --- | --- | --- |
| Unit | Funksiya, klass | Har task |
| Integration | Real DB, kesh, navbat (bulutda PostgreSQL 16 va Redis 7 bor) | Har task |
| E2E | Foydalanuvchi oqimi | Muhim funksiyalarda |
| Contract/mock | Tashqi API'lar (soxta javoblar) | Tashqi integratsiyada |
| Smoke (staging/prod) | Deploy'dan keyin haqiqiy sozlamalar bilan | Har deploy, GitHub Actions'da |
| Mutation | Testlar xatoni topadimi | Milestone |

## 7. Secret'lar

| Joy | Nima | Kim ko'radi |
| --- | --- | --- |
| Parol menejeri | Barcha asl parol va tokenlar | Faqat egasi |
| GitHub Secrets | Deploy kaliti, server, registry, prod qiymatlar | GitHub Actions (loglarda yashirin) |
| Server `.env` (chmod 600) | Prod sozlamalar | Faqat ilova |
| Bulut muhiti o'zgaruvchilari | Faqat soxta/test qiymatlar | Claude ko'radi |
| Bulut muhiti network secrets | Dev/test API kalitlari | Claude ko'rmaydi, proxy qo'shadi |
| `.env.example` | Faqat nomlar | Hamma |

Secret oqib ketsa — darhol almashtiriladi (rotate). Git tarixidan o'chirishning o'zi yetarli emas.

## 8. GitHub

- Repo private, GitHub Free — main'da GitHub himoyasi (ruleset) yo'q. Uning o'rniga:
  - qoidalar (CLAUDE.md, promptlar) va `.claude/settings.json` taqiqlari: main'ga push, force push, skriptsiz merge;
  - `merge-gate` workflow + `scripts/merge-if-green.sh`: Claude PR'ni faqat hamma tekshiruv yashil va himoyalangan fayllar o'zgarmagan bo'lsa merge qiladi;
  - `main-guard` workflow: main'ga PR'siz commit yoki force push tushsa, darhol `alert:main-guard` issue ochadi;
  - `weekly-backup` workflow: har yakshanba 01:17 (Toshkent) to'liq git bundle nusxasi, 90 kun saqlanadi.
- Claude `claude/` bilan boshlanadigan branch'larga push qiladi, PR ochadi va uni `scripts/merge-if-green.sh` orqali merge qiladi.
  Himoyalangan fayllarni o'zgartirgan PR `needs:owner` oladi — uni egasi merge qiladi (2026-11-22: "B" varianti).
- Ochiq `alert:main-guard` issue — keyingi run'ning birinchi ishi.
- `known-good` workflow main'dagi har to'liq yashil commit'ga `good-*` teg qo'yadi (yashil nuqta).

## 8a. Qizil chiroq

Har run boshida sog'liq tekshiruvi (Yashil / Sariq / Qizil). Qizilda Claude to'xtaydi, hisobot beradi va
egasining ruxsatidan keyingina eng kichik ortga qaytishni bajaradi (A oldinga tuzatish → B bitta PR revert →
C bir nechta PR → D yashil nuqtaga qaytish → E zaxiradan tiklash). Hammasi PR orqali, tarix o'chirilmaydi.
To'liq tartib: `docs/RECOVERY.md`.
- Commit: Conventional Commits. Release: teg + CHANGELOG.

## 9. Stack modullari (odatiy tanlov, yakuniy qaror ADR bilan)

| Yo'nalish | Stack | Test |
| --- | --- | --- |
| Backend | Django, DRF, PostgreSQL, Redis, Celery | pytest, pytest-django, factory_boy |
| Web frontend | React/Next.js yoki Vue, TypeScript | Vitest, Playwright |
| Telegram bot | aiogram 3, PostgreSQL, Redis | pytest-asyncio |
| Mobil | Flutter yoki React Native | flutter test |
| Desktop | C# .NET, WPF + MVVM | xUnit (Windows runner) |
| C/C++ | C++20, CMake, pybind11 | GoogleTest, sanitizerlar |
| AI/ML | Python, PyTorch, scikit-learn, MLflow | pytest, metamorphic testlar |
| O'yinlar | Godot 4; Unity C# / Unreal C++ | GUT, Unity Test Framework |

Bulut sessiyasi: Ubuntu 24.04, GPU va ekransiz. Mobil emulyator, Windows build va o'yin grafikasi CI'da yoki egasining kompyuterida tekshiriladi. .NET SDK oldindan o'rnatilmagan — setup skript bilan qo'shiladi.

## 10. Tajriba → shaxsiy skill

Har hafta LESSONS.md, har milestone'da Claude yozuvlardan shaxsiy skill taklifini tayyorlaydi (`senior-project-workflow` + stack skill'lari). Skill akkauntda va `.claude/skills/`da saqlanadi.
