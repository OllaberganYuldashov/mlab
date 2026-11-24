# Assotsiativ qoidalar

## "Non olganlar sut ham oladi"

Assotsiativ qoidalar savatlarda birga uchraydigan narsalarni topadi: `{non} → {sut}`. Do'kon javonlarini joylashtirish,
tavsiya tizimlari, hatto talabalar qaysi mavzularda birga qiynalishini tahlil qilishda ishlatiladi.

## Uch o'lchov

- **Support** — to'plam barcha savatlarning qancha qismida uchraydi.
- **Confidence** `A → B` — A bor savatlarning qancha qismida B ham bor: `support(A∪B) / support(A)`.
- **Lift** — `confidence / support(B)`. 1 dan katta — A va B birga tasodifdan ko'ra ko'proq uchraydi.

## Savatlar jadvali

```python try
import pandas as pd
savatlar = [
    {"non", "sut", "tuxum"},
    {"non", "sut"},
    {"non", "choy"},
    {"sut", "tuxum"},
    {"non", "sut", "choy"},
    {"choy", "shakar"},
    {"non", "sut", "shakar"},
    {"choy", "shakar", "non"},
]
mahsulotlar = sorted(set().union(*savatlar))
jadval = pd.DataFrame([[m in s for m in mahsulotlar] for s in savatlar], columns=mahsulotlar)
print(jadval.mean().round(2))     # har mahsulotning support'i
```

## Qoidalarni hisoblash

```python try
from itertools import permutations
def support(*nomlar):
    return jadval[list(nomlar)].all(axis=1).mean()

qoidalar = []
for a, b in permutations(mahsulotlar, 2):
    s = support(a, b)
    if s >= 0.25:
        conf = s / support(a)
        qoidalar.append((a, b, round(s, 2), round(conf, 2), round(conf / support(b), 2)))
natija = pd.DataFrame(qoidalar, columns=["A", "B", "support", "confidence", "lift"])
natija.sort_values("lift", ascending=False)
```

## Apriori g'oyasi

Mahsulotlar ko'p bo'lsa, barcha kombinatsiyalarni tekshirib bo'lmaydi. **Apriori** kuzatuvi: to'plam kam uchrasa, uni
o'z ichiga olgan katta to'plam ham kam uchraydi. Shuning uchun avval tez-tez uchraydigan kichik to'plamlar topiladi va
faqat ulardan kattaroqlari quriladi.

## Tezkor savol

```quiz
question: '"{choy} → {shakar}" qoidasining lift qiymati 2. Bu nimani bildiradi?'
options:
  - Choy olganlar shakarni tasodifdagidan 2 marta ko'proq oladi
  - Shakar choydan 2 marta qimmat
  - Qoida 2 marta uchragan
answer: A
explain: Lift > 1 — ijobiy bog'liqlik; 1 — bog'liqlik yo'q.
```
