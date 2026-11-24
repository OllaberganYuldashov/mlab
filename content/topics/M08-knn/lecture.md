# k eng yaqin qo'shni (k-NN)

## G'oya

k-NN eng sodda algoritmlardan: yangi obyektga eng yaqin `k` ta o'qitish misolini topadi va ularning ko'pchiligi qaysi
sinf bo'lsa, shu sinfni beradi. O'qitish — shunchaki ma'lumotni eslab qolish.

## Masofa

Odatda Evklid masofasi: `d = √((x₁-y₁)² + (x₂-y₂)² + …)`. Masofa masshtabga bog'liq — shuning uchun belgilarni
standartlash muhim (pastda ko'ramiz).

## k ning ta'siri

Slayder bilan k ni o'zgartiring. k = 1 da chegara "yirtiq" (har nuqtaga moslashadi — overfitting), katta k da silliq.

```visual
widget: knn
title: Qaror hududlari va k
k_max: 25
```

## Scikit-learn'da k-NN

```python try
import mlab
from sklearn.model_selection import cross_val_score
from sklearn.neighbors import KNeighborsClassifier
iris = mlab.load("iris")
X, y = iris.drop(columns="species"), iris["species"]
for k in (1, 5, 15, 50):
    print("k =", k, "CV aniqlik:", cross_val_score(KNeighborsClassifier(k), X, y, cv=5).mean().round(3))
```

## Masshtablash nega muhim?

Vino datasetida `proline` yuzlab birlikda, `hue` esa 1 atrofida — masofani deyarli faqat `proline` belgilaydi.

```python try
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
wine = mlab.load("wine")
Xw, yw = wine.drop(columns="cultivar"), wine["cultivar"]
print("masshtabsiz:", cross_val_score(KNeighborsClassifier(5), Xw, yw, cv=5).mean().round(3))
print("standartlangan:", cross_val_score(make_pipeline(StandardScaler(), KNeighborsClassifier(5)), Xw, yw, cv=5).mean().round(3))
```

## Afzallik va kamchiliklar

- Sodda, o'qitish bir zumda, sinflar soni istalgancha.
- Bashorat sekin (har safar hamma misollar bilan masofa), ko'p belgilarda masofa ma'nosini yo'qotadi ("o'lchov la'nati").

## Tezkor savol

```quiz
question: k-NN da k = 1 tanlansa, odatda nima bo'ladi?
options:
  - Model juda silliq bo'ladi (underfitting)
  - Model shovqinga sezgir bo'ladi (overfitting)
  - Model ishlamaydi
answer: B
explain: Har yangi nuqta faqat bitta eng yaqin qo'shniga qaraydi — tasodifiy nuqtalar chegarani buzadi.
```
