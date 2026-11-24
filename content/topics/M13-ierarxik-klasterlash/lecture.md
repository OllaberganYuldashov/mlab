# Ierarxik klasterlash

## G'oya

**Agglomerativ** (yig'uvchi) usul: har nuqta o'zi alohida klaster; har qadamda eng yaqin ikki klaster birlashtiriladi —
bitta klaster qolguncha. Natija — birlashishlar daraxti (**dendrogramma**). Uni istalgan balandlikda "kesib", kerakli
sondagi klasterni olamiz.

## Klasterlar orasidagi masofa (linkage)

- **single** — eng yaqin nuqtalar masofasi (cho'ziq "zanjir" klasterlar);
- **complete** — eng uzoq nuqtalar masofasi;
- **average** — barcha juftliklar o'rtachasi;
- **ward** — birlashganda ichki tarqoqlik eng kam oshadigan juftlik (ko'pincha eng yaxshi boshlang'ich tanlov).

## Dendrogramma

```python try
import matplotlib.pyplot as plt
import mlab
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.preprocessing import StandardScaler
wine = mlab.load("wine")
X = StandardScaler().fit_transform(wine.drop(columns="cultivar"))
Z = linkage(X[::4], method="ward")     # rasm o'qilishi uchun har 4-namuna
dendrogram(Z, no_labels=True)
plt.title("Ward usuli bilan dendrogramma")
```

## Scikit-learn bilan

```python try
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
labels = AgglomerativeClustering(n_clusters=3, linkage="ward").fit_predict(X)
print(pd.crosstab(labels, wine["cultivar"]))
```

Jadvalda klasterlar navlarga qanchalik mos tushganini ko'ramiz (navlar algoritmga berilmagan edi).

## Qachon ishlatiladi?

- Klasterlar soni noma'lum va ierarxiya o'zi qiziq (masalan, turlar tasnifi);
- Kichik va o'rta datasetlar: hisob murakkabligi kamida O(n²), katta ma'lumotda sekin.

## Tezkor savol

```quiz
question: Dendrogrammani balandroq joydan kesish nima beradi?
options:
  - Ko'proq klaster
  - Kamroq klaster
  - Shovqin nuqtalar
answer: B
explain: Yuqorida klasterlar ko'proq birlashgan bo'ladi.
```
