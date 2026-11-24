# Svertkali neyron tarmoqlar (CNN), 1-qism

## Rasm — sonlar matritsasi

Kulrang rasm — piksellar yorqinligi matritsasi. Oddiy MLP rasmni bitta uzun vektorga yoyadi va qo'shni piksellar
bog'liqligini yo'qotadi. CNN esa kichik "oyna" bilan rasm bo'ylab yuradi.

```python try
import matplotlib.pyplot as plt
from sklearn.datasets import load_digits
digits = load_digits()
plt.imshow(digits.images[0], cmap="gray_r")
plt.title(f"raqam: {digits.target[0]}")
print(digits.images[0].astype(int))
```

## Svertka (convolution)

**Filtr** (masalan, 3×3) rasm ustida siljiydi; har joyda piksellar bilan filtr qiymatlari ko'paytirilib yig'iladi.
Natija — **belgilar xaritasi**: filtr qidirgan naqsh (chegara, chiziq) qayerda borligini ko'rsatadi.

```python try
import numpy as np
def svertka(rasm, filtr):
    h, w = rasm.shape[0] - 2, rasm.shape[1] - 2
    return np.array([[np.sum(rasm[i:i + 3, j:j + 3] * filtr) for j in range(w)] for i in range(h)])
vertikal = np.array([[1, 0, -1], [1, 0, -1], [1, 0, -1]])
gorizontal = vertikal.T
fig, ax = plt.subplots(1, 3, figsize=(8, 3))
ax[0].imshow(digits.images[0], cmap="gray_r")
ax[1].imshow(svertka(digits.images[0], vertikal), cmap="coolwarm")
ax[1].set_title("vertikal chegaralar")
ax[2].imshow(svertka(digits.images[0], gorizontal), cmap="coolwarm")
ax[2].set_title("gorizontal chegaralar")
```

## O'rganiladigan filtrlar

Yuqorida filtrni qo'lda yozdik. CNN da filtr qiymatlari og'irlik — ular backpropagation bilan o'rganiladi. Birinchi
qatlamlar chegaralarni, keyingilari shakl va qismlarni, oxirgilari butun obyektni taniydi.

## Parametrlar tejami

28×28 rasm va 100 neyronli to'liq bog'langan qatlam: 78 400 og'irlik. 3×3 li 16 ta filtr: atigi 16·(9+1) = 160.
Bitta filtr butun rasmda **qayta ishlatiladi** — shuning uchun CNN rasmlarda samarali.

## Tezkor savol

```quiz
question: Svertka qatlamida filtr qiymatlari qayerdan keladi?
options:
  - Dasturchi qo'lda yozadi
  - O'qitish jarayonida backpropagation bilan o'rganiladi
  - Rasmning o'rtacha qiymatidan
answer: B
explain: Filtrlar — tarmoqning o'rganiladigan og'irliklari.
```
