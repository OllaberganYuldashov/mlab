# Loyiha holati dashboard'i

Egasi uchun doimiy sahifa: relizlar, iteratsiyalar, tasklar va ularning natijasi, qancha qismi tayyor va taxminiy
tugash sanalari. Sahifa: **https://claude.ai/artifact/W5HuzuuTwV6AGnZDgNEE6g** ("MLab loyiha holati", Data turi).

## Fayllar
- `plan.py` — yagona manba: relizlar, iteratsiyalar (taxminiy ball), tasklar (holat, natija, PR) va `META`
  (holat sanasi, joriy iteratsiya, keyingi task, kunlik tezlik).
- `build.py` — `plan.py` dan `tasks.json`, `iterations.json`, `releases.json`, `meta.json` yasaydi (tekshiruvlar bilan).
- `index.html` — dashboard sahifasining nusxasi (dashboard'da `files/index.html` hujjati).

## Har run oxirida (docs/prompts/nightly-run.md, 8-qadam)
1. `plan.py`: tugagan tasklar `done` + PR, boshlanganlar `in_progress`; `META.as_of`, `current_iteration`, `next_task`.
   Yangi iteratsiya issue'larga bo'linganda uning `E-...` epiklari o'rniga issue'lar qo'yiladi.
2. `python3 docs/status/build.py`.
3. Har JSON'ni dashboard'ga asset sifatida yuklash (`Artifact` → `asset: true`, `url` yuqoridagi) va
   `datasets/<id>` hujjatining `source.url` va `updated` maydonlarini yangilash (`ArtifactData update`).
4. Haftalik review `META.velocity_per_day` ni haqiqiy tezlik bo'yicha yangilaydi.

## Hisob
Ball: S = 1, M = 2. Epik bali = iteratsiya taxmini / epiklar soni. Kontent (130 ball) I2–I5 ga ulushiga qarab qo'shiladi.
Tugash sanasi = holat sanasi + yig'ilgan qolgan ball / kunlik tezlik. Serverni kutayotgan task prognozga kirmaydi.
