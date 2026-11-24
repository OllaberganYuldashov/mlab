# Bosh komponentlar tahlili (PCA)

## O'lchovni kamaytirish

Vino datasetida 13 ta belgi bor — 13 o'lchovli fazoni ko'z bilan ko'rib bo'lmaydi. **PCA** ma'lumotni eng ko'p
o'zgaruvchanlik (dispersiya) yo'nalishlariga — **bosh komponentlarga** proyeksiyalaydi. Birinchi 2–3 komponent ko'pincha
ma'lumotning asosiy tuzilishini saqlaydi.

## Avval standartlash

PCA dispersiyaga qaraydi: masshtabi katta belgi (`proline`) komponentlarni "egallab oladi". Shuning uchun avval
standartlaymiz.

## 13 o'lchovdan 2 ga

```python try
import matplotlib.pyplot as plt
import mlab
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
wine = mlab.load("wine")
X = StandardScaler().fit_transform(wine.drop(columns="cultivar"))
pca = PCA(n_components=2).fit(X)
Z = pca.transform(X)
for nav in sorted(wine["cultivar"].unique()):
    tanlov = (wine["cultivar"] == nav).to_numpy()
    plt.scatter(Z[tanlov, 0], Z[tanlov, 1], s=12, label=nav)
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.legend()
print("Tushuntirilgan dispersiya:", pca.explained_variance_ratio_.round(3))
```

## Nechta komponent kerak?

Kumulyativ tushuntirilgan dispersiyaga qaraymiz: odatda 90–95% ni saqlaydigan eng kam komponent soni.

```python try
import numpy as np
toliq = PCA().fit(X)
kumulyativ = np.cumsum(toliq.explained_variance_ratio_)
print("90% uchun komponentlar:", int(np.argmax(kumulyativ >= 0.9)) + 1)
plt.figure()
plt.plot(range(1, 14), kumulyativ, "o-")
plt.axhline(0.9, color="gray", linestyle="--")
```

## PCA dan keyin model

PCA natijasini boshqa modelga kirish qilib berish mumkin — kamroq belgi, tezroq o'qitish, ba'zan overfitting kamroq.
Lekin komponentlarning ma'nosini tushuntirish qiyinroq.

## Tezkor savol

```quiz
question: PCA dan oldin nega belgilarni standartlash kerak?
options:
  - Masshtabi katta belgi komponentlarni egallab olmasligi uchun
  - PCA faqat butun sonlar bilan ishlaydi
  - Standartlash shart emas
answer: A
explain: PCA dispersiyani maksimallashtiradi, katta masshtabli belgining dispersiyasi ham katta.
```
