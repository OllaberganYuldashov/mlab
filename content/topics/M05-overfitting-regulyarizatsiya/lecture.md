# Overfitting va regulyarizatsiya

## Yod olish va tushunish

**Overfitting** (ortiqcha moslashish) — model o'qitish ma'lumotidagi tasodifiy shovqinni ham "yod oladi": o'qitishda
xato juda kichik, yangi ma'lumotda esa katta. **Underfitting** — model juda sodda, o'qitishda ham yomon.

## Polinom darajasi bilan tajriba

Bir xil nuqtalarga 1-, 3- va 12-darajali polinom moslaymiz va o'qitish/test xatosini solishtiramiz.

```python try
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

rng = np.random.default_rng(1)
x = np.sort(rng.uniform(0, 1, 30)).reshape(-1, 1)
y = np.sin(2 * np.pi * x[:, 0]) + rng.normal(0, 0.2, 30)
x_test = np.sort(rng.uniform(0, 1, 30)).reshape(-1, 1)
y_test = np.sin(2 * np.pi * x_test[:, 0]) + rng.normal(0, 0.2, 30)

grid = np.linspace(0, 1, 200).reshape(-1, 1)
plt.scatter(x, y, s=12, color="black")
for daraja in (1, 3, 12):
    m = make_pipeline(PolynomialFeatures(daraja), LinearRegression()).fit(x, y)
    print(daraja, "- daraja: o'qitish", round(mean_squared_error(y, m.predict(x)), 3),
          "| test", round(mean_squared_error(y_test, m.predict(x_test)), 3))
    plt.plot(grid, m.predict(grid), label=f"daraja {daraja}")
plt.ylim(-2, 2)
plt.legend()
```

1-daraja — underfitting, 12-daraja — overfitting (o'qitish xatosi kichik, test xatosi katta), 3-daraja — muvozanat.

## Regulyarizatsiya

Regulyarizatsiya katta koeffitsiyentlar uchun "jarima" qo'shadi va modelni soddaroq bo'lishga majbur qiladi:

- **Ridge (L2):** jarima `α·Σw²` — koeffitsiyentlarni kichraytiradi.
- **Lasso (L1):** jarima `α·Σ|w|` — keraksiz belgilarning koeffitsiyentini aynan 0 qiladi (belgi tanlash).

```python try
from sklearn.linear_model import Ridge
for alpha in (0.0001, 0.01, 1):
    m = make_pipeline(PolynomialFeatures(12), Ridge(alpha=alpha)).fit(x, y)
    print("alpha =", alpha, "| test MSE:", round(mean_squared_error(y_test, m.predict(x_test)), 3))
```

## Bias va variance

- **Bias** (siljish) — model juda sodda bo'lgani uchun tizimli xato (underfitting).
- **Variance** (dispersiya) — model o'qitish to'plamiga haddan tashqari sezgir (overfitting).

Murakkablikni oshirsak bias kamayadi, variance oshadi. Maqsad — test xatosi eng kichik bo'lgan nuqta.

## Tezkor savol

```quiz
question: O'qitish xatosi juda kichik, test xatosi esa katta. Bu qaysi holat?
options:
  - Underfitting
  - Overfitting
  - Model ideal
answer: B
explain: Model o'qitish to'plamini yod olgan, yangi ma'lumotga umumlashtira olmayapti.
```
