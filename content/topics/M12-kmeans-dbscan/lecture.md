# k-means va DBSCAN

## Klasterlash

**Klasterlash** — javoblarsiz (nazoratsiz) ma'lumotni o'xshash guruhlarga ajratish: mijozlar segmenti, hujjatlar mavzusi.
Natijani "to'g'ri javob" bilan emas, guruhlarning ma'nosi va ixchamligi bilan baholaymiz.

## k-means algoritmi

1. k ta markazni tasodifiy tanlash.
2. Har nuqtani eng yaqin markazga biriktirish.
3. Markazni o'z nuqtalarining o'rtachasiga ko'chirish.
4. Markazlar o'zgarmay qolguncha 2–3 ni takrorlash.

```python try
import matplotlib.pyplot as plt
import mlab
from sklearn.cluster import KMeans
iris = mlab.load("iris")
X = iris[["petal_length", "petal_width"]]
km = KMeans(n_clusters=3, n_init=10, random_state=0).fit(X)
plt.scatter(X["petal_length"], X["petal_width"], c=km.labels_, cmap="viridis", s=15)
plt.scatter(km.cluster_centers_[:, 0], km.cluster_centers_[:, 1], marker="x", s=120, color="red")
print(km.cluster_centers_.round(2))
```

## k ni tanlash: "tirsak" usuli

**Inertia** — nuqtalardan o'z markazigacha masofalar kvadratlari yig'indisi. k oshsa doim kamayadi; kamayish sekinlashgan
"tirsak" nuqtasi — yaxshi k.

```python try
inertia = [KMeans(k, n_init=10, random_state=0).fit(X).inertia_ for k in range(1, 8)]
plt.figure()
plt.plot(range(1, 8), inertia, "o-")
plt.xlabel("k")
plt.ylabel("inertia")
```

## DBSCAN — zichlik bo'yicha

k-means klasterlarni "dumaloq" deb faraz qiladi. **DBSCAN** zich hududlarni klaster deydi: `eps` radiusida kamida
`min_samples` qo'shnisi bor nuqtalar. Klaster sonini oldindan bermaymiz, siyrak nuqtalar esa **shovqin** (`-1`).

```python try
from sklearn.cluster import DBSCAN
from sklearn.datasets import make_moons
Xm, _ = make_moons(300, noise=0.06, random_state=0)
km_labels = KMeans(2, n_init=10, random_state=0).fit_predict(Xm)
db_labels = DBSCAN(eps=0.2, min_samples=5).fit_predict(Xm)
fig, ax = plt.subplots(1, 2, figsize=(8, 3))
ax[0].scatter(Xm[:, 0], Xm[:, 1], c=km_labels, s=8)
ax[0].set_title("k-means")
ax[1].scatter(Xm[:, 0], Xm[:, 1], c=db_labels, s=8)
ax[1].set_title("DBSCAN")
print("DBSCAN klasterlari:", sorted(set(db_labels)))
```

## Tezkor savol

```quiz
question: Klasterlar yarim oy shaklida va shovqin nuqtalar bor. Qaysi algoritm mosroq?
options:
  - k-means
  - DBSCAN
  - Chiziqli regressiya
answer: B
explain: DBSCAN ixtiyoriy shakldagi zich hududlarni topadi va siyrak nuqtalarni shovqin deb belgilaydi.
```
