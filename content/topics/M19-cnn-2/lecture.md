# Svertkali neyron tarmoqlar (CNN), 2-qism

## Pooling

**Max pooling** (masalan, 2×2) har bo'lakdan eng katta qiymatni oladi: xarita o'lchami 2 marta kichrayadi, kichik
siljishlarga chidamlilik oshadi va hisob kamayadi.

```python try
import numpy as np
def max_pool(x, k=2):
    h, w = x.shape[0] // k, x.shape[1] // k
    return x[: h * k, : w * k].reshape(h, k, w, k).max(axis=(1, 3))
x = np.arange(16).reshape(4, 4)
print(x)
print(max_pool(x))
```

## Tipik arxitektura

`[svertka → ReLU → pooling] × N → yoyish (flatten) → to'liq bog'langan qatlamlar → softmax`.
Chuqurlashgan sari xaritalar kichrayadi, filtrlar soni esa ko'payadi (8 → 16 → 32 …).

## Oddiy "CNN" qo'lda

Qo'lda yozilgan filtrlar va pooling bilan belgilar chiqaramiz, keyin ularni oddiy klassifikatorga beramiz. Haqiqiy CNN
filtrlarni o'zi o'rganadi — bu yerda faqat g'oyani ko'ramiz.

```python try
from sklearn.datasets import load_digits
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
digits = load_digits()
filtrlar = [np.array([[1, 0, -1]] * 3), np.array([[1, 0, -1]] * 3).T]
def svertka(rasm, f):
    return np.array([[np.sum(rasm[i:i + 3, j:j + 3] * f) for j in range(6)] for i in range(6)])
def belgilar(rasm):
    return np.concatenate([max_pool(np.maximum(svertka(rasm, f), 0)).ravel() for f in filtrlar])
F = np.array([belgilar(r) for r in digits.images])
print("belgilar soni:", F.shape[1], "(xom piksellar: 64)")
print("CV aniqlik:", round(cross_val_score(LogisticRegression(max_iter=2000), F, digits.target, cv=5).mean(), 3))
```

## Mashhur arxitekturalar

LeNet (1998, raqamlar), AlexNet (2012, ImageNet inqilobi), VGG (bir xil 3×3 qatlamlar), ResNet (qoldiq ulanishlar
bilan 100+ qatlam). Amalda ko'pincha tayyor o'qitilgan tarmoq olinib, o'z vazifasiga moslashtiriladi
(**transfer learning**).

## Ma'lumot ko'paytirish (augmentation)

Rasmlarni biroz aylantirish, siljitish, yorqinligini o'zgartirish — yangi misollar "bepul". Bu overfittingni kamaytiradi.

## Tezkor savol

```quiz
question: 2×2 max pooling 8×8 xaritani qanday o'lchamga keltiradi?
options:
  - 4×4
  - 6×6
  - 16×16
answer: A
explain: Har o'lcham 2 marta kichrayadi.
```
