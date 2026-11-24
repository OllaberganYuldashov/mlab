# Cross-validation

## Bitta bo'linish yetarlimi?

Ma'lumotni bir marta o'qitish/testga bo'lsak, natija qaysi misollar testga tushganiga bog'liq — "omad" aralashadi.
Kichik datasetlarda bu farq katta bo'ladi.

```python try
import mlab
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
df = mlab.load("iris")
X, y = df.drop(columns="species"), df["species"]
for seed in range(5):
    x_tr, x_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=seed)
    aniqlik = KNeighborsClassifier(15).fit(x_tr, y_tr).score(x_te, y_te)
    print("seed", seed, "aniqlik:", round(aniqlik, 3))
```

## k-fold cross-validation

Ma'lumot k qismga bo'linadi. Har safar bitta qism test, qolganlari o'qitish — k marta. Natija — k ta bahoning o'rtachasi
va tarqoqligi. Odatda k = 5 yoki 10.

```python try
from sklearn.model_selection import cross_val_score
baholar = cross_val_score(KNeighborsClassifier(15), X, y, cv=5)
print(baholar.round(3), "o'rtacha:", baholar.mean().round(3), "±", baholar.std().round(3))
```

## Stratifikatsiya

Tasniflashda har bo'lakda sinflar nisbati butun datasetdagidek bo'lishi kerak — **stratified k-fold**. Scikit-learn
tasniflagichlar uchun buni o'zi qiladi (`cv=5`).

## Giperparametr tanlash

`k` (qo'shnilar soni) kabi sozlamalar **giperparametr** — ularni test to'plamida emas, cross-validation bilan tanlaymiz.

```python try
from sklearn.model_selection import GridSearchCV
qidiruv = GridSearchCV(KNeighborsClassifier(), {"n_neighbors": [1, 3, 5, 9, 15, 25]}, cv=5).fit(X, y)
print("eng yaxshi k:", qidiruv.best_params_, "CV aniqlik:", round(qidiruv.best_score_, 3))
```

## Ma'lumot sizishi (data leakage)

Masshtablash yoki to'ldirish butun datasetda o'qitilsa, test qismidagi ma'lumot o'qitishga "sizib" o'tadi va baho
haqiqatdan yaxshi chiqadi. Yechim — barcha qadamlarni `Pipeline` ichiga qo'yish: har bo'lakda alohida o'qitiladi.

```python try
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
pipe = make_pipeline(StandardScaler(), KNeighborsClassifier(9))
print("Pipeline CV:", cross_val_score(pipe, X, y, cv=5).mean().round(3))
```

## Tezkor savol

```quiz
question: Giperparametrni (masalan, k) qaysi ma'lumot bo'yicha tanlash to'g'ri?
options:
  - Test to'plamidagi natija bo'yicha
  - O'qitish to'plamidagi cross-validation bo'yicha
  - Butun datasetdagi aniqlik bo'yicha
answer: B
explain: Test to'plami faqat yakuniy baho uchun; u tanlovga aralashsa, baho haddan tashqari optimistik bo'ladi.
```
