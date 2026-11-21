# Birinchi sessiya prompti — L1 · MLab

> Claude Code'da (Cloud, muhit `mlab-dev`, repo `mlab`, model Opus, effort High) birinchi xabar sifatida
> to'liq nusxalab yuboriladi. TZ (SRS v2) allaqachon tasdiqlangan, shuning uchun savol-javob bosqichi yo'q.

```text
Bu L1 · MLab loyihasining birinchi sessiyasi. Men egasiman (Product Owner / CTO), sen tech lead va jamoasan.

1. CLAUDE.md, docs/PLAYBOOK.md, docs/SRS.md, docs/PRD.md, docs/ARCHITECTURE.md,
   docs/adr/0001-stack.md, docs/BACKLOG.md va docs/SECURITY.md'ni to'liq o'qi.
   SRS v2 tasdiqlangan — talablarni o'zgartirma. Zid yoki noaniq joy topsang, ro'yxat qilib menga ber.
2. Qaysi skill, agent va buyruqlar mavjudligini ro'yxat qil (.claude/ va akkaunt skill'lari).
3. GitHub label'larini yarat: status:ready, status:in-progress, status:blocked, status:review,
   type:feature, type:bug, type:chore, type:docs, type:content, size:S, size:M,
   release:R0, release:R1, iter:I1..iter:I5, alert:main-guard, alert:red-light.
4. docs/BACKLOG.md'dagi R0-01..R0-17 tasklaridan GitHub Issue'lar yarat (shablon:
   .github/ISSUE_TEMPLATE/task.md, acceptance criteria va bog'liqliklar bilan, sarlavhada talab ID).
   Issue yaratib bo'lmasa — sababini ayt va to'xta, men yordam beraman.
   Natijani jadval qilib ko'rsat va tasdiqlashimni kut.
5. Tasdiqdan keyin R0-01 ni bajar: claude/r0-01-backend-skeleton branch, darhol draft PR,
   CLAUDE.md 6 va 7-bo'limlari bo'yicha (test → kod → hujjat). CI workflow nomi aynan "ci"
   bo'lsin — known-good shu nom bo'yicha yashil nuqta qo'yadi. docs/learn/django.md darsini yoz.
   PR'ni ready for review qil va menga qisqa hisobot ber.
6. CLAUDE.md 4-bo'limidagi buyruqlarni haqiqiy holatga moslab yangila.
   docs/prompts/setup-script.sh yangilanishi kerak bo'lsa, o'zgarishni ayt — men muhitga qo'yaman.
7. Limit qolsa R0-02 ga o't (alohida branch va PR). Yakunda docs/PROGRESS.md va
   docs/learn/JOURNAL.md'ni yangila.

Har bosqichdan keyin to'xta va tasdiq so'ra. Secret so'rama va yozma. main'ga push qilma, PR'ni merge qilma.
```
