# Logistik regressiya

## Tasniflash masalasi

Nishon son emas, sinf bo'lsa (spam/spam emas, xavfli/xavfsiz) — bu **tasniflash**. Logistik regressiya nomiga qaramay
tasniflash modeli: u sinfga tegishlilik **ehtimolini** beradi.

## Sigmoid funksiyasi

Chiziqli qiymat `z = w·x + b` ni sigmoid `σ(z) = 1 / (1 + e⁻ᶻ)` 0..1 oralig'iga o'tkazadi — bu ehtimol.

```python try
import numpy as np
import matplotlib.pyplot as plt
z = np.linspace(-8, 8, 200)
plt.plot(z, 1 / (1 + np.exp(-z)))
plt.axhline(0.5, color="gray", linestyle="--")
plt.title("Sigmoid: 0.5 dan katta — 1-sinf")
```

## Model o'qitish

Ko'krak bezi o'smasi datasetida 30 ta belgi bor. Belgilar har xil masshtabda — standartlash bilan Pipeline.

```python try
import mlab
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
df = mlab.load("breast_cancer")
X, y = df.drop(columns="diagnosis"), df["diagnosis"]
x_tr, x_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(x_tr, y_tr)
print("Test aniqligi:", round(model.score(x_te, y_te), 3))
```

## Ehtimol va chegara

`predict_proba` har sinf ehtimolini beradi. Odatda chegara 0.5, lekin tibbiyotda xavfli holatni o'tkazib yubormaslik
uchun chegarani pasaytirish mumkin — bunda soxta signallar ko'payadi.

```python try
ehtimol = model.predict_proba(x_te)
sinflar = list(model.classes_)
p_xavfli = ehtimol[:, sinflar.index("malignant")]
for chegara in (0.5, 0.3):
    topildi = ((p_xavfli >= chegara) & (y_te == "malignant")).sum()
    print("chegara", chegara, ": xavfli holatlardan topildi", topildi, "/", (y_te == "malignant").sum())
```

## Ko'p sinfli tasniflash

Sinflar uchta va undan ko'p bo'lsa ham `LogisticRegression` ishlaydi (softmax).

```python try
iris = mlab.load("iris")
m = LogisticRegression(max_iter=1000).fit(iris.drop(columns="species"), iris["species"])
print(m.predict(iris.drop(columns="species").iloc[[0, 60, 120]]))
```

## Tezkor savol

```quiz
question: Logistik regressiya natijasi 0.8 chiqdi. Bu nimani bildiradi?
options:
  - Obyekt 1-sinfga tegishli bo'lish ehtimoli 0.8 (80%)
  - Model aniqligi 80%
  - Nishon qiymati 0.8
answer: A
explain: Sigmoid chiqishi — sinfga tegishlilik ehtimoli.
```
