# Ma'lumotlarga dastlabki ishlov

## Nega tozalash kerak?

Haqiqiy ma'lumot deyarli hech qachon "toza" bo'lmaydi: qiymatlar yetishmaydi, matn va son aralashgan, birliklar har xil.
Model faqat sonlar bilan ishlaydi va xatoli ma'lumotdan xatoli qonuniyat o'rganadi. Shuning uchun ML loyihasi vaqtining
katta qismi ma'lumotni tayyorlashga ketadi.

## Pandas bilan tanishuv

**pandas** — jadval ma'lumotlari bilan ishlash kutubxonasi. Asosiy obyekt — `DataFrame` (ustunlari nomlangan jadval).

```python try
import mlab
df = mlab.load("iris")
print(df.shape)        # (qatorlar, ustunlar)
print(df.dtypes)       # har ustunning turi
df.head()
```

## Yetishmayotgan qiymatlar

Bo'sh katakchalar `NaN` bo'lib keladi. Ularni topamiz, keyin yo o'chiramiz, yo o'rtacha/median bilan to'ldiramiz.

```python try
import numpy as np
import pandas as pd
t = pd.DataFrame({"yosh": [21, np.nan, 23, 22], "ball": [80, 75, np.nan, 90]})
print(t.isna().sum())                  # har ustunda nechta bo'sh
print(t.dropna())                      # bo'sh qatorlarni tashlash
print(t.fillna(t.median()))            # median bilan to'ldirish
```

## Kategorik belgilar

"setosa", "versicolor" kabi matnlarni model tushunmaydi. **One-hot** kodlash har toifa uchun alohida 0/1 ustun yaratadi.

```python try
sinf = pd.get_dummies(df["species"], prefix="tur")
sinf.head()
```

## Masshtablash

Belgilar har xil oraliqda bo'lsa (masalan, maydon 30–200, xonalar 1–5), ba'zi algoritmlar katta sonli belgiga ko'proq
"e'tibor" beradi. **Standartlash**: har ustundan o'rtachani ayirib, standart og'ishga bo'lamiz.

```python try
from sklearn.preprocessing import StandardScaler
sonlar = df.drop(columns="species")
standart = StandardScaler().fit_transform(sonlar)
print(standart.mean(axis=0).round(2), standart.std(axis=0).round(2))
```

## Chetlanuvchi qiymatlar (outlier)

IQR qoidasi: `Q1 - 1.5·IQR` dan kichik yoki `Q3 + 1.5·IQR` dan katta qiymat — shubhali. Uni o'chirishdan oldin
tekshiring: ba'zan bu xato emas, eng muhim misol bo'ladi.

## Tezkor savol

```quiz
question: Ustundagi bo'sh qiymatlarni median bilan to'ldirish qachon o'rtacha (mean) dan yaxshiroq?
options:
  - Ustunda chetlanuvchi (juda katta yoki kichik) qiymatlar bo'lsa
  - Ustun matn bo'lsa
  - Hech qachon
answer: A
explain: Median chetlanuvchi qiymatlarga sezgir emas, o'rtacha esa ular tomon siljiydi.
```
