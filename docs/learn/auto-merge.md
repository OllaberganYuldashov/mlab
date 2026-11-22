# Avtomatik merge: merge-gate qanday ishlaydi

## Bu nima
Claude o'z PR'ini o'zi merge qiladi, lekin qaror Claude'ning fikriga emas, GitHub'dagi qat'iy tekshiruvlarga tayanadi.
Siz faqat kunlik hisobotni o'qiysiz va savollarga javob berasiz (2026-11-22 qarori: hamma merge Claude'da).

## Nega shunday
Egasi har kuni merge qilishga ulgurmasligi mumkin — ish to'xtab qolmasligi kerak (2026-11-22 qarori).
Lekin "o'zi yozdi, o'zi tekshirdi, o'zi qabul qildi" xavfli. Shuning uchun uchta qatlam bor:

| Qatlam | Nima qiladi |
| --- | --- |
| `merge-gate` (workflow) | Branch `claude/`, PR draft emas, `needs:owner`/`hold` yo'q, himoyalangan fayllar o'zgarmagan |
| `scripts/merge-if-green.sh` | merge-gate, ci, secret-scan va boshqa barcha tekshiruvlar yashil bo'lsagina merge; aniq commit (`sha`) bilan |
| `scripts/merge-protected.sh` | `needs:owner` PR uchun: ci, secret-scan va qolgan hamma tekshiruv yashil, merge-gate faqat `needs:owner` sababli qizil; himoya mexanizmining o'zini o'zgartirgan PR'ni rad etadi; qizil holatda ishlamaydi. Har doim main'dagi nusxasi ishga tushiriladi |
| Kuzatuv | main-guard (skriptsiz merge yoki PR'siz commit bo'lsa issue), known-good (yashil nuqtalar), haftalik review (avto-merge PR'lar auditi) |

## Himoyalangan fayllar
`.github/workflows/*`, `.claude/settings.json`, `scripts/merge-if-green.sh`, `CLAUDE.md`, `docs/SRS.md`, `docs/RECOVERY.md`, `deploy/`.
Bular "o'yin qoidalari": testlar, xavfsizlik taqiqlari, talablar, prod server. Ularni o'zgartirgan PR avtomatik
`needs:owner` label va izoh oladi. 2026-11-22 dan bunday PR'larni ham Claude `merge-protected.sh` bilan merge qiladi va
kunlik hisobotda alohida qatorda yozadi (qaysi fayl, nega); haftalik review ularni qayta tekshiradi.

**Faqat siz merge qilasiz:** himoya mexanizmining o'zi — `.claude/settings.json`, `scripts/merge-*.sh`, merge-gate, main-guard,
known-good, secret-scan, weekly-backup workflow'lari. Claude o'z cheklovlarini o'zi yumshata olmasligi uchun skript bunday PR'ni rad etadi.

## Siz nima qilasiz
1. Har kuni "📋 Kunlik hisobotlar" issue'sidagi yangi izohni o'qing (GitHub ilovasi bildirishnoma yuboradi).
2. `status:blocked` savol bo'lsa — issue'da javob yozing (hisobotda variantlar va tavsiya bo'ladi).
3. Juda kam hollarda: himoya mexanizmini o'zgartiradigan PR — uni o'zingiz ko'rib, merge qilasiz.
4. PR'ni to'xtatmoqchi bo'lsangiz — unga `hold` label qo'ying; Claude uni merge qilmaydi.

## Qachon Claude merge qilmaydi
Biror tekshiruv qizil; tekshiruvlar tugamagan; konflikt; `hold` yoki `alert:*` label; PR himoya mexanizmining o'zini o'zgartiradi; loyiha Qizil holatda.

## Kichik mashq
GitHub'da istalgan PR'ning **Checks** yorlig'ini oching va `merge-gate` qatorini toping: u yashilmi yoki qizil — va nega?
