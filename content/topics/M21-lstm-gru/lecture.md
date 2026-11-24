# LSTM va GRU

## Uzoq xotira muammosi

"Men O'zbekistonda tug'ilganman, … (50 so'z) … shuning uchun ona tilim — ___". Javob uchun boshidagi so'z kerak.
Oddiy RNN da bu axborot ko'p qadamdan keyin "yuvilib ketadi".

## LSTM: darvozalar

**LSTM** alohida **hujayra holati** `c` (uzoq xotira "konveyeri") va uchta **darvoza**ga ega (har biri 0..1 — sigmoid):

- **unutish darvozasi** `f` — eski xotiradan nimani o'chirish;
- **kirish darvozasi** `i` — yangi axborotdan nimani yozish;
- **chiqish darvozasi** `o` — xotiradan nimani tashqariga berish.

`cₜ = f·cₜ₋₁ + i·c̃ₜ`, `hₜ = o·tanh(cₜ)`. Qo'shish (ko'paytirish emas) gradientni uzoq masofaga yetkazadi.

```python try
import numpy as np
sigmoid = lambda z: 1 / (1 + np.exp(-z))
rng = np.random.default_rng(0)
n = 4
W = {g: rng.normal(0, 0.5, (n, n + 1)) for g in "fioc"}
h, c = np.zeros(n), np.zeros(n)
for x in [1.0, 0.0, 0.0, 0.0, 0.0]:
    z = np.concatenate([h, [x]])
    f, i, o = sigmoid(W["f"] @ z), sigmoid(W["i"] @ z), sigmoid(W["o"] @ z)
    c = f * c + i * np.tanh(W["c"] @ z)
    h = o * np.tanh(c)
    print("c =", c.round(3), "| unutish o'rtacha:", f.mean().round(2))
```

## GRU

**GRU** — soddalashtirilgan LSTM: ikki darvoza (**yangilash** `z` va **qayta o'rnatish** `r`), alohida hujayra holati
yo'q. Parametrlar kamroq, tezroq o'qitiladi, ko'p vazifalarda natijasi LSTM ga yaqin.

## Darvoza qanday ishlaydi?

Darvoza qiymati 1 ga yaqin bo'lsa — axborot o'tadi, 0 ga yaqin — to'xtaydi. Quyida unutish darvozasi har xil bo'lganda
xotira qanchalik saqlanishini ko'ramiz.

```python try
import matplotlib.pyplot as plt
for f in (0.5, 0.9, 0.99):
    c, iz = 1.0, []
    for _ in range(50):
        c = f * c
        iz.append(c)
    plt.plot(iz, label=f"f = {f}")
plt.xlabel("qadam")
plt.ylabel("xotirada qolgan")
plt.legend()
```

## Qaysi birini tanlash?

Boshlash uchun GRU (sodda va tez); juda uzun ketma-ketliklar va ko'p ma'lumot bo'lsa — LSTM. Ikkalasini sinab, cross-
validation bilan solishtirish eng ishonchli yo'l.

## Tezkor savol

```quiz
question: LSTM da qaysi darvoza eski xotiradan nimani o'chirishni hal qiladi?
options:
  - Kirish darvozasi
  - Unutish darvozasi
  - Chiqish darvozasi
answer: B
explain: cₜ = f·cₜ₋₁ + … — f eski xotirani qancha qoldirishni belgilaydi.
```
