# Qarorlar daraxti

## G'oya

Qarorlar daraxti "ha/yo'q" savollar zanjiri: *gulbarg uzunligi < 2.45 sm?* → ha: setosa; yo'q: keyingi savol…
Har tugunda algoritm ma'lumotni eng yaxshi ajratadigan belgi va chegarani tanlaydi. Natija — odam o'qiy oladigan qoidalar.

## Bo'linish sifati: Gini

Tugun qanchalik "aralash" ekanini **Gini nopokligi** o'lchaydi: `G = 1 - Σ pᵢ²`. Bir sinfli tugunda G = 0. Daraxt har
bo'linishda nopoklik eng ko'p kamayadigan savolni tanlaydi (entropiya ham shunga o'xshash ishlatiladi).

## Daraxt qurish va o'qish

```python try
import mlab
from sklearn.tree import DecisionTreeClassifier, export_text
iris = mlab.load("iris")
X, y = iris.drop(columns="species"), iris["species"]
daraxt = DecisionTreeClassifier(max_depth=2, random_state=0).fit(X, y)
print(export_text(daraxt, feature_names=list(X.columns)))
```

## Chuqurlik va overfitting

Cheklanmagan daraxt har bir misolni alohida bargga ajratguncha o'sadi — o'qitishda 100%, testda yomonroq.

```python try
from sklearn.model_selection import cross_val_score
bc = mlab.load("breast_cancer")
Xb, yb = bc.drop(columns="diagnosis"), bc["diagnosis"]
for depth in (1, 3, 5, None):
    m = DecisionTreeClassifier(max_depth=depth, random_state=0)
    oqitish = m.fit(Xb, yb).score(Xb, yb)
    cv = cross_val_score(m, Xb, yb, cv=5).mean()
    print("max_depth =", depth, "| o'qitish:", round(oqitish, 3), "| CV:", round(cv, 3))
```

## Belgilar muhimligi

```python try
m = DecisionTreeClassifier(max_depth=4, random_state=0).fit(Xb, yb)
muhim = sorted(zip(m.feature_importances_, Xb.columns), reverse=True)[:5]
for qiymat, nom in muhim:
    print(f"{nom:25s} {qiymat:.3f}")
```

## Tasodifiy o'rmon (qisqacha)

Bitta daraxt beqaror: ma'lumot biroz o'zgarsa, daraxt butunlay boshqacha bo'ladi. **Random forest** ko'p daraxtni
tasodifiy qismlarda o'qitib, ovoz beradi — odatda aniqroq va barqarorroq.

```python try
from sklearn.ensemble import RandomForestClassifier
print("Random forest CV:", round(cross_val_score(RandomForestClassifier(100, random_state=0), Xb, yb, cv=5).mean(), 3))
```

## Tezkor savol

```quiz
question: Qarorlar daraxtida max_depth cheklanmasa, odatda nima bo'ladi?
options:
  - Underfitting
  - Overfitting
  - Daraxt qurilmaydi
answer: B
explain: Daraxt o'qitish ma'lumotini to'liq yod olguncha o'sadi.
```
