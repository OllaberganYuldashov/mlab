# Teskari tarqalish (backpropagation)

## Gradient tushish

Tarmoqni o'qitish — yo'qotish funksiyasi `L` (masalan, MSE) eng kichik bo'ladigan og'irliklarni topish. Har og'irlikni
gradientga teskari yo'nalishda biroz suramiz: `w ← w - η·∂L/∂w`. `η` — o'rganish tezligi.

```python try
import numpy as np
# f(w) = (w - 3)²; minimum w = 3 da
w, eta = 0.0, 0.1
for qadam in range(25):
    grad = 2 * (w - 3)
    w -= eta * grad
print("w =", round(w, 4))
```

## Zanjir qoidasi

Tarmoq — funksiyalar zanjiri: `x → z = w·x + b → a = σ(z) → L`. Gradient zanjir qoidasi bilan **orqadan oldinga**
hisoblanadi: `∂L/∂w = ∂L/∂a · ∂a/∂z · ∂z/∂w`. Har qatlam keyingisidan kelgan gradientni oladi va o'zinikini qo'shadi —
shuning uchun "teskari tarqalish".

## Kichik tarmoqni qo'lda o'qitish

2 → 3 → 1 tarmoq XOR ni o'rganadi. Oldinga hisob, keyin gradientlar va yangilash.

```python try
rng = np.random.default_rng(0)
X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
y = np.array([[0], [1], [1], [0]], dtype=float)
W1, b1 = rng.normal(0, 1, (2, 3)), np.zeros(3)
W2, b2 = rng.normal(0, 1, (3, 1)), np.zeros(1)
sigmoid = lambda z: 1 / (1 + np.exp(-z))
for epoch in range(5000):
    h = np.tanh(X @ W1 + b1)           # oldinga
    out = sigmoid(h @ W2 + b2)
    d_out = (out - y) * out * (1 - out)  # orqaga (MSE)
    d_h = (d_out @ W2.T) * (1 - h ** 2)
    W2 -= 0.5 * h.T @ d_out
    b2 -= 0.5 * d_out.sum(axis=0)
    W1 -= 0.5 * X.T @ d_h
    b1 -= 0.5 * d_h.sum(axis=0)
print("bashorat:", out.ravel().round(2))
```

## O'rganish tezligi

`η` juda kichik — o'qitish sekin; juda katta — yo'qotish sakraydi va kamaymaydi. Amalda **Adam** kabi moslashuvchan
optimizatorlar va mini-batch (ma'lumot bo'laklari) ishlatiladi.

```python try
for eta in (0.01, 0.1, 1.05):
    w = 0.0
    for _ in range(25):
        w -= eta * 2 * (w - 3)
    print("eta =", eta, "→ w =", round(w, 3))
```

## Yo'qolayotgan gradient

Sigmoid hosilasi ko'pi bilan 0.25. Ko'p qatlamda bu ko'paytmalar gradientni nolga yaqinlashtiradi — oldingi qatlamlar
deyarli o'rganmaydi. Shuning uchun chuqur tarmoqlarda ReLU va maxsus initsializatsiya ishlatiladi.

## Tezkor savol

```quiz
question: O'rganish tezligi juda katta bo'lsa, odatda nima kuzatiladi?
options:
  - Yo'qotish sakraydi yoki o'sib ketadi
  - O'qitish juda sekin, lekin barqaror
  - Hech narsa o'zgarmaydi
answer: A
explain: Har qadam minimumdan o'tib ketadi.
```
