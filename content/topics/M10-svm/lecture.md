# Tayanch vektorlar mashinasi (SVM)

## Eng keng "ko'cha"

Ikki sinfni ajratadigan chiziqlar ko'p. SVM ular orasidan sinflargacha masofa (**margin**) eng katta bo'lganini tanlaydi.
Chegaraga eng yaqin nuqtalar — **tayanch vektorlar**: chegara faqat ularga bog'liq.

## Chiziqli SVM

```python try
import numpy as np
import matplotlib.pyplot as plt
import mlab
from sklearn.svm import SVC
iris = mlab.load("iris")
ikki = iris[iris["species"] != "virginica"]
X = ikki[["petal_length", "petal_width"]].to_numpy()
y = (ikki["species"] == "versicolor").astype(int).to_numpy()
svm = SVC(kernel="linear", C=1).fit(X, y)
print("tayanch vektorlar soni:", len(svm.support_vectors_))
plt.scatter(X[:, 0], X[:, 1], c=y, cmap="coolwarm", s=15)
plt.scatter(svm.support_vectors_[:, 0], svm.support_vectors_[:, 1], s=80, facecolors="none", edgecolors="black")
w, b = svm.coef_[0], svm.intercept_[0]
xs = np.linspace(X[:, 0].min(), X[:, 0].max(), 10)
plt.plot(xs, -(w[0] * xs + b) / w[1], "k-")
```

## C parametri

**C** — xatoga jarima. Katta C: har bir nuqtani to'g'ri ajratishga urinadi (tor margin, overfitting xavfi). Kichik C:
ba'zi xatolarga yo'l qo'yib, kengroq va barqarorroq chegara.

## Yadro (kernel) hiylasi

Sinflar chiziq bilan ajralmasa, SVM ma'lumotni yuqoriroq o'lchovga "ko'taradi" va u yerda ajratadi. **RBF** yadrosi —
eng ko'p ishlatiladigani.

```python try
from sklearn.datasets import make_moons
from sklearn.model_selection import cross_val_score
Xm, ym = make_moons(200, noise=0.2, random_state=0)
for yadro in ("linear", "rbf"):
    print(yadro, "CV:", round(cross_val_score(SVC(kernel=yadro), Xm, ym, cv=5).mean(), 3))
```

## Masshtablash

SVM masofalarga tayanadi — belgilarni standartlash deyarli har doim kerak.

```python try
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
bc = mlab.load("breast_cancer")
Xb, yb = bc.drop(columns="diagnosis"), bc["diagnosis"]
print("masshtabsiz:", round(cross_val_score(SVC(), Xb, yb, cv=5).mean(), 3))
print("standartlangan:", round(cross_val_score(make_pipeline(StandardScaler(), SVC()), Xb, yb, cv=5).mean(), 3))
```

## Tezkor savol

```quiz
question: SVM'da "tayanch vektorlar" nima?
options:
  - Barcha o'qitish misollari
  - Ajratuvchi chegaraga eng yaqin misollar
  - Modelning koeffitsiyentlari
answer: B
explain: Chegara faqat shu nuqtalarga bog'liq — qolganlarini olib tashlasa ham o'zgarmaydi.
```
