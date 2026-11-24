# Model sifati metrikalari

## Aniqlik (accuracy) yetarli emas

100 bemordan 1 tasi kasal bo'lsa, "hamma sog'" degan model 99% aniq — lekin foydasiz. Shuning uchun xatolar turini
alohida ko'ramiz.

## Chalkashlik matritsasi

- **TP** (true positive) — haqiqatda musbat, model ham "musbat" dedi (to'g'ri topildi).
- **FN** (false negative) — haqiqatda musbat, model "manfiy" dedi (o'tkazib yuborildi).
- **FP** (false positive) — haqiqatda manfiy, model "musbat" dedi (soxta signal).
- **TN** (true negative) — haqiqatda manfiy, model ham "manfiy" dedi.

```python try
import mlab
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
bc = mlab.load("breast_cancer")
X, y = bc.drop(columns="diagnosis"), (bc["diagnosis"] == "malignant").astype(int)
x_tr, x_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, stratify=y, random_state=0)
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(x_tr, y_tr)
bashorat = model.predict(x_te)
print(confusion_matrix(y_te, bashorat, labels=[1, 0]))
```

## Precision, recall, F1

- **Precision** = TP / (TP + FP) — "musbat" deganlarimizning qanchasi to'g'ri.
- **Recall** = TP / (TP + FN) — haqiqiy musbatlarning qanchasini topdik.
- **F1** — ikkalasining garmonik o'rtachasi.

```python try
from sklearn.metrics import classification_report
print(classification_report(y_te, bashorat, target_names=["benign", "malignant"], digits=3))
```

## ROC egri chizig'i va AUC

Chegarani 0 dan 1 gacha o'zgartirsak, recall (TPR) va soxta signal ulushi (FPR) o'zgaradi. **AUC** — egri ostidagi yuza:
1 — mukammal, 0.5 — tanga tashlash.

```python try
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve
p = model.predict_proba(x_te)[:, 1]
fpr, tpr, _ = roc_curve(y_te, p)
plt.plot(fpr, tpr)
plt.plot([0, 1], [0, 1], "--", color="gray")
plt.xlabel("FPR")
plt.ylabel("TPR (recall)")
print("AUC:", round(roc_auc_score(y_te, p), 3))
```

## Regressiya metrikalari (eslatma)

MAE (o'rtacha absolyut xato), RMSE (katta xatolarni ko'proq jazolaydi), R² — M04 da ko'rganmiz.

## Tezkor savol

```quiz
question: Kasallikni aniqlashda eng xavfli xato qaysi va uni qaysi metrika nazorat qiladi?
options:
  - FP — precision
  - FN (kasalni sog' deyish) — recall
  - TN — accuracy
answer: B
explain: Recall past bo'lsa, haqiqiy kasallar o'tkazib yuboriladi.
```
