# Loyiha holati dashboard'i

Egasi uchun doimiy sahifa: relizlar, iteratsiyalar, tasklar va ularning natijasi, qancha qismi tayyor va taxminiy
tugash sanalari. Sahifa: **https://claude.ai/artifact/W5HuzuuTwV6AGnZDgNEE6g** ("MLab loyiha holati", Data turi).

## Fayllar
- `plan.py` — **faqat reja**: relizlar, iteratsiyalar (taxminiy ball), tasklar (iteratsiya, hajm, natija) va `META`
  (joriy reliz va iteratsiya, kunlik tezlik). Issue'li task holati va PR'i bu yerda qo'lda yangilanmaydi.
- `live.json` — GitHub'dagi holat (issue → `status`, `pr`; `as_of`, `next_task`). Uni `scripts/sync_status.py` yozadi.
- `build.py` — `plan.py` + `live.json` dan `tasks.json`, `iterations.json`, `releases.json`, `meta.json` yasaydi
  (tekshiruvlar bilan). `live.json` dagi qiymat `plan.py` dagisidan ustun.
- `index.html` — dashboard sahifasining nusxasi (dashboard'da `files/index.html` hujjati).

## Holat qayerdan olinadi (`scripts/sync_status.py`)
`gh api graphql` bitta so'rovda `plan.py` dagi har issue'ni oladi:

| GitHub | Dashboard |
| --- | --- |
| issue yopiq | `done`; `pr` — uni yopgan **merge bo'lgan** PR'lar (`closedByPullRequestsReferences`) |
| `status:blocked` | `blocked` |
| `status:review` yoki `status:in-progress` | `in_progress` |
| `status:ready` | `ready` |
| ochiq, status label'i yo'q | `plan.py` dagi qiymat (masalan, serverni kutayotgan `blocked`, kelajakdagi `planned`) |

- `META.as_of` — bugungi sana (Asia/Tashkent).
- `next_task` — **avtomatik**: eng kichik raqamli `status:ready` issue (`run:day` — kunduzgi sessiya olgani — tashlanadi).
  Bu run protokoli (CLAUDE.md 7.3) bilan bir xil qoida, shuning uchun qo'lda yozilgan matndan ko'ra eskirmaydi.
  Maxsus izoh kerak bo'lsa (masalan, "I3 yakuni, keyin deploy") — `plan.py` da `META["next_task"]` ga matn yoziladi,
  skript uni o'zgartirmaydi; bo'sh qator — avtomatik.
- Issue'siz `E-...` epiklar (hali bo'linmagan iteratsiya) va `R0-16b` kabi tasklar holati `plan.py` da qoladi.
- Test: `backend/tests/test_sync_status.py` (gh javobi soxta).

## Har run oxirida (docs/prompts/nightly-run.md, 8-qadam)
1. Yangi iteratsiya issue'larga bo'linganda `plan.py` da uning `E-...` epiklari o'rniga issue'lar qo'yiladi
   (yangi issue — yangi `_t(...)` qatori). Boshqa holatlarda `plan.py` ga tegilmaydi.
2. `python3 scripts/sync_status.py` (GitHub'dan holat + `build.py`). gh ishlamasa — `--offline` (mavjud `live.json`).
3. Har JSON'ni dashboard'ga asset sifatida yuklash (`Artifact` → `asset: true`, `url` yuqoridagi) va
   `datasets/<id>` hujjatining `source.url` va `updated` maydonlarini yangilash (`ArtifactData update`).
4. Haftalik review `META.velocity_per_day` ni haqiqiy tezlik bo'yicha yangilaydi.

## Hisob
Ball: S = 1, M = 2. Epik bali = iteratsiya taxmini / epiklar soni. Kontent (130 ball) I2–I5 ga ulushiga qarab qo'shiladi.
Tugash sanasi = holat sanasi + yig'ilgan qolgan ball / kunlik tezlik. Serverni kutayotgan task prognozga kirmaydi.
