# Avtomatik merge: merge-gate qanday ishlaydi

## Bu nima
Claude o'z PR'ini o'zi merge qiladi, lekin qaror Claude'ning fikriga emas, GitHub'dagi qat'iy tekshiruvlarga tayanadi.
Siz faqat kunlik hisobotni o'qiysiz va kamdan-kam hollarda (`needs:owner`) bitta tugmani bosasiz.

## Nega shunday
Egasi har kuni merge qilishga ulgurmasligi mumkin — ish to'xtab qolmasligi kerak (2026-11-22 qarori).
Lekin "o'zi yozdi, o'zi tekshirdi, o'zi qabul qildi" xavfli. Shuning uchun uchta qatlam bor:

| Qatlam | Nima qiladi |
| --- | --- |
| `merge-gate` (workflow) | Branch `claude/`, PR draft emas, `needs:owner`/`hold` yo'q, himoyalangan fayllar o'zgarmagan |
| `scripts/merge-if-green.sh` | merge-gate, ci, secret-scan va boshqa barcha tekshiruvlar yashil bo'lsagina merge; aniq commit (`sha`) bilan |
| Kuzatuv | main-guard (skriptsiz merge yoki PR'siz commit bo'lsa issue), known-good (yashil nuqtalar), haftalik review (avto-merge PR'lar auditi) |

## Himoyalangan fayllar (faqat siz merge qilasiz)
`.github/workflows/*`, `.claude/settings.json`, `scripts/merge-if-green.sh`, `CLAUDE.md`, `docs/SRS.md`, `docs/RECOVERY.md`, `deploy/`.
Bular "o'yin qoidalari": testlar, xavfsizlik taqiqlari, talablar, prod server. Ularni o'zgartirgan PR avtomatik
`needs:owner` label va izoh oladi. Bunday PR R0 da bir necha marta (CI, deploy), keyin juda kam bo'ladi.

## Siz nima qilasiz
1. Har kuni "📋 Kunlik hisobotlar" issue'sidagi yangi izohni o'qing (GitHub ilovasi bildirishnoma yuboradi).
2. Hisobotda `needs:owner` PR bo'lsa — ochib, tavsifini o'qing va 07:00–23:00 da **Merge pull request**.
3. `status:blocked` savol bo'lsa — javob yozing.
4. PR'ni to'xtatmoqchi bo'lsangiz — unga `hold` label qo'ying; Claude uni merge qilmaydi.

## Qachon Claude merge qilmaydi
Biror tekshiruv qizil; tekshiruvlar tugamagan; konflikt; `needs:owner`, `hold` yoki `alert:*` label; loyiha Qizil holatda.

## Kichik mashq
GitHub'da istalgan PR'ning **Checks** yorlig'ini oching va `merge-gate` qatorini toping: u yashilmi yoki qizil — va nega?
