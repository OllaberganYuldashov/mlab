# Rekurrent neyron tarmoqlar (RNN)

## Ketma-ketliklar

Matn, nutq, kunlik harorat, aksiya narxi — tartib muhim bo'lgan ma'lumot. Oddiy tarmoq har kirishni alohida ko'radi;
**RNN** esa oldingi qadamlardan "xotira" — **yashirin holat** `h` ni olib yuradi.

## RNN qadami

Har vaqt qadamida: `hₜ = tanh(Wₓ·xₜ + Wₕ·hₜ₋₁ + b)`. Bir xil og'irliklar har qadamda qayta ishlatiladi.

```python try
import numpy as np
rng = np.random.default_rng(0)
Wx, Wh, b = rng.normal(0, 0.5, (3, 1)), rng.normal(0, 0.5, (3, 3)), np.zeros(3)
h = np.zeros(3)
ketma_ketlik = [0.1, 0.5, 0.9, 0.4]
for t, x in enumerate(ketma_ketlik):
    h = np.tanh(Wx @ [x] + Wh @ h + b)
    print("t =", t, "h =", h.round(3))
```

## Vaqt qatori bashorati

Oldingi `k` qiymatdan keyingisini bashorat qilish — ketma-ketlik modellarining asosiy vazifasi. RNN bo'lmasa ham,
"sirpanuvchi oyna" bilan oddiy model qurib ko'ramiz.

```python try
import matplotlib.pyplot as plt
from sklearn.neural_network import MLPRegressor
t = np.arange(300)
qator = np.sin(t / 10) + rng.normal(0, 0.05, 300)
k = 10
X = np.array([qator[i:i + k] for i in range(len(qator) - k)])
y = qator[k:]
model = MLPRegressor(hidden_layer_sizes=(32,), max_iter=500, random_state=0).fit(X[:220], y[:220])
plt.plot(range(220 + k, 300), y[220:], label="haqiqiy")
plt.plot(range(220 + k, 300), model.predict(X[220:]), label="bashorat")
plt.legend()
```

## Vaqt bo'ylab teskari tarqalish

RNN qadamlar bo'ylab "yoyib" chiqiladi va oddiy backpropagation qo'llanadi (BPTT). Uzun ketma-ketlikda gradient ko'p
marta ko'paytiriladi — **yo'qoladi** yoki **portlaydi**. Shuning uchun oddiy RNN uzoq bog'liqliklarni yomon eslaydi
(keyingi mavzu — LSTM va GRU).

## Qo'llanilishi

Matn yaratish, tarjima, nutqni tanish, vaqt qatori bashorati. Bugun ko'p vazifalarda **transformer**lar ishlatiladi,
lekin RNN g'oyasi — ketma-ketlikni holat bilan qayta ishlash — asosiy tushuncha bo'lib qoladi.

## Tezkor savol

```quiz
question: RNN ning oddiy tarmoqdan asosiy farqi nimada?
options:
  - Oldingi qadamlardan yashirin holatni (xotirani) olib yuradi
  - Faqat rasmlar bilan ishlaydi
  - Og'irliklari yo'q
answer: A
explain: hₜ oldingi hₜ₋₁ ga bog'liq.
```
