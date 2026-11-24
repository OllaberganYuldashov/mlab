# Vizualizatsiya va EDA

## EDA nima?

**EDA** (Exploratory Data Analysis — razvedka tahlili) — model qurishdan oldin ma'lumotni "tanish": taqsimotlar,
bog'liqliklar, g'alati qiymatlar. Yaxshi grafik ko'p soatlik noto'g'ri ishning oldini oladi.

## Tavsifiy statistika

```python try
import mlab
df = mlab.load("iris")
print(df["species"].value_counts())
df.describe().round(2)
```

## Gistogramma — taqsimot

Gistogramma qiymatlar qaysi oraliqda ko'p uchrashini ko'rsatadi.

```python try
import matplotlib.pyplot as plt
plt.hist(df["petal_length"], bins=20, color="#3a6ea5")
plt.xlabel("Gulbarg uzunligi (sm)")
plt.ylabel("Soni")
plt.title("Ikki cho'qqi — ikki xil guruh borligiga ishora")
```

## Nuqtali diagramma — bog'liqlik

Ikki belgining birgalikdagi ko'rinishi. Rang bilan sinfni ko'rsatsak, sinflar ajraladimi — darhol ko'rinadi.

```python try
for tur, rang in zip(["setosa", "versicolor", "virginica"], ["#3a6ea5", "#d9822b", "#1d6b35"]):
    qism = df[df["species"] == tur]
    plt.scatter(qism["petal_length"], qism["petal_width"], label=tur, color=rang, s=15)
plt.xlabel("Gulbarg uzunligi")
plt.ylabel("Gulbarg kengligi")
plt.legend()
```

## Korrelyatsiya

Korrelyatsiya (-1..1) ikki son belgining chiziqli bog'liqligini o'lchaydi. 1 ga yaqin — birga o'sadi, -1 ga yaqin —
biri o'ssa, ikkinchisi kamayadi, 0 — chiziqli bog'liqlik yo'q (lekin boshqa bog'liqlik bo'lishi mumkin!).

```python try
korr = df.drop(columns="species").corr().round(2)
print(korr)
```

## Seaborn bilan quti diagrammasi

Box plot median, kvartillar va chetlanuvchilarni bitta rasmda ko'rsatadi.

```python try
import seaborn as sns
sns.boxplot(data=df, x="species", y="sepal_width")
```

## Tezkor savol

```quiz
question: Ikki belgi orasidagi korrelyatsiya 0 ga teng. Bu nimani anglatadi?
options:
  - Ular orasida hech qanday bog'liqlik yo'q
  - Ular orasida chiziqli bog'liqlik yo'q, boshqa turdagi bog'liqlik bo'lishi mumkin
  - Belgilardan biri doimiy
answer: B
explain: Masalan, y = x² da korrelyatsiya 0 ga yaqin bo'lishi mumkin, lekin bog'liqlik kuchli.
```
