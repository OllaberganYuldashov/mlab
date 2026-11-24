# Regressiya

## Regressiya masalasi

**Regressiya** — son qiymatni bashorat qilish: uy narxi, harorat, mahsulot savdosi. Eng oddiy model — chiziq:
`y = w·x + b`. Bu yerda `w` — qiyalik (x bir birlikka o'zgarsa, y qanchaga o'zgaradi), `b` — siljish.

## Chiziqni qo'lda tanlash

Slayderlar bilan chiziqni nuqtalarga moslang. Xato (MSE) — nuqtalardan chiziqqacha bo'lgan masofalar kvadratlarining o'rtachasi.

```visual
widget: line-fit
title: Chiziqni nuqtalarga moslash
points:
  - [1, 2.1]
  - [2, 3.9]
  - [3, 6.2]
  - [4, 7.8]
  - [5, 10.1]
  - [6, 12.2]
```

## Eng kichik kvadratlar usuli

O'qitish — MSE ni eng kichik qiladigan `w` va `b` ni topish. Chiziqli regressiyada buning aniq formulasi bor;
scikit-learn uni `LinearRegression` ichida hisoblaydi.

```python try
import numpy as np
from sklearn.linear_model import LinearRegression
rng = np.random.default_rng(0)
x = rng.uniform(30, 150, 60).reshape(-1, 1)          # uy maydoni, m²
y = 2.5 * x[:, 0] + 40 + rng.normal(0, 15, 60)      # narx (shartli birlik)
model = LinearRegression().fit(x, y)
print("w =", model.coef_[0].round(2), " b =", round(model.intercept_, 2))
print("100 m² uy narxi:", model.predict([[100]]).round(1))
```

## Sifatni baholash

- **MSE / RMSE** — o'rtacha xato (RMSE nishon birligida).
- **R²** — model nishon o'zgaruvchanligining qancha qismini tushuntiradi (1 — mukammal, 0 — o'rtacha qiymat darajasida).

Baholash har doim **test** to'plamida — model ko'rmagan ma'lumotda.

```python try
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
x_tr, x_te, y_tr, y_te = train_test_split(x, y, test_size=0.25, random_state=0)
m = LinearRegression().fit(x_tr, y_tr)
bashorat = m.predict(x_te)
print("RMSE:", np.sqrt(mean_squared_error(y_te, bashorat)).round(2))
print("R²:", round(r2_score(y_te, bashorat), 3))
```

## Ko'p belgili regressiya

Belgilar bir nechta bo'lsa, model `y = w₁x₁ + w₂x₂ + … + b`. Masalan, vino tarkibidan spirt darajasini bashorat qilish:

```python try
import mlab
wine = mlab.load("wine")
X = wine[["color_intensity", "proline", "total_phenols"]]
m = LinearRegression().fit(X, wine["alcohol"])
print(dict(zip(X.columns, m.coef_.round(4))))
print("R² (o'qitish to'plamida):", round(m.score(X, wine["alcohol"]), 3))
```

## Tezkor savol

```quiz
question: Test to'plamida R² = 0 chiqdi. Bu nimani anglatadi?
options:
  - Model mukammal
  - Model har doim o'rtacha qiymatni aytgandek yaxshi — foydasi yo'q
  - Model har doim noto'g'ri belgi bilan bashorat qiladi
answer: B
explain: R² = 0 — model nishonning o'rtachasini bashorat qilishdan yaxshi emas.
```
