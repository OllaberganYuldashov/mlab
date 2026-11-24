# Perseptron va ko'p qatlamli perseptron (MLP)

## Sun'iy neyron

Neyron kirishlarni og'irliklar bilan yig'adi va **faollashtirish funksiyasi**dan o'tkazadi: `a = f(w·x + b)`.
Eng oddiy holat — **perseptron**: `f` pog'onali funksiya (0 yoki 1).

## Perseptron o'rganishi

Xato qilsa, og'irliklarni to'g'ri javob tomon suradi: `w ← w + η·(y - ŷ)·x`.

```python try
import numpy as np
X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
y_and = np.array([0, 0, 0, 1])
w, b, eta = np.zeros(2), 0.0, 0.1
for epoch in range(10):
    for xi, yi in zip(X, y_and):
        pred = int(w @ xi + b > 0)
        w += eta * (yi - pred) * xi
        b += eta * (yi - pred)
print("w =", w, "b =", b, "bashorat:", [int(w @ xi + b > 0) for xi in X])
```

## XOR muammosi

XOR (`[0,1,1,0]`) ni bitta chiziq bilan ajratib bo'lmaydi — perseptron uni o'rgana olmaydi. Yechim — oraliq (yashirin)
qatlam: **MLP**.

## MLP

Bir nechta qatlam: har qatlam oldingisining chiqishini oladi. Yashirin qatlamlarda chiziqli bo'lmagan funksiya
(**ReLU** `max(0, z)`, **sigmoid**, **tanh**) bo'lmasa, butun tarmoq baribir bitta chiziqli modelga teng bo'lardi.

```python try
from sklearn.neural_network import MLPClassifier
y_xor = np.array([0, 1, 1, 0])
mlp = MLPClassifier(hidden_layer_sizes=(4,), activation="tanh", solver="lbfgs", random_state=1, max_iter=1000)
mlp.fit(X, y_xor)
print("XOR bashorati:", mlp.predict(X))
```

## Raqamlarni tanish

8×8 piksel qo'lyozma raqamlar (scikit-learn ichidagi `digits` dataseti).

```python try
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
digits = load_digits()
x_tr, x_te, y_tr, y_te = train_test_split(digits.data, digits.target, test_size=0.25, random_state=0)
model = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(64,), max_iter=300, random_state=0))
model.fit(x_tr, y_tr)
print("Test aniqligi:", round(model.score(x_te, y_te), 3))
```

## Tezkor savol

```quiz
question: Nega yashirin qatlamlarda chiziqli bo'lmagan faollashtirish funksiyasi kerak?
options:
  - Busiz ko'p qatlamli tarmoq bitta chiziqli modelga teng bo'lib qoladi
  - Tezroq hisoblash uchun
  - Og'irliklarni musbat saqlash uchun
answer: A
explain: Chiziqli funksiyalarning kompozitsiyasi ham chiziqli.
```
