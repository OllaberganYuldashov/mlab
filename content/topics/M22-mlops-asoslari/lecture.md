# MLOps asoslari

## Model — bu dastur

Notebook'da ishlagan model hali mahsulot emas. **MLOps** — modelni ishonchli o'qitish, saqlash, joylashtirish va
kuzatish amaliyotlari: dasturiy ta'minot muhandisligi + ML.

## Takrorlanuvchanlik

Bir xil kod va ma'lumot — bir xil natija bo'lishi kerak: `random_state`, kutubxona versiyalari, ma'lumot versiyasi.
Hamma qadamlar bitta `Pipeline` da — o'qitishda ham, ishlatishda ham bir xil.

```python try
import mlab
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
df = mlab.load("breast_cancer")
X, y = df.drop(columns="diagnosis"), df["diagnosis"]
pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=0)).fit(X, y)
print(pipe)
```

## Modelni saqlash va yuklash

O'qitilgan model faylga saqlanadi (scikit-learn uchun odatda `joblib`) va xizmatda yuklanadi. Fayl bilan birga versiya,
sana, ma'lumot va metrikalar yoziladi.

```python try
import io
import joblib
buf = io.BytesIO()
joblib.dump(pipe, buf)
print("model hajmi:", len(buf.getvalue()), "bayt")
buf.seek(0)
yuklangan = joblib.load(buf)
print("bir xil bashorat:", (yuklangan.predict(X) == pipe.predict(X)).all())
```

Eslatma: pickle/joblib faylini faqat ishonchli manbadan yuklang — u kod bajarishi mumkin.

## Joylashtirish

Model odatda API orqali beriladi: so'rov → belgilar → `predict` → javob. Kirish ma'lumoti tekshiriladi (ustunlar,
turlar, oraliqlar), xatolar va kechikish loglanadi.

## Kuzatish va drift

Vaqt o'tib real ma'lumot o'qitishdagidan farq qila boshlaydi (**data drift**) va sifat pasayadi. Belgilar taqsimotini
muntazam solishtiramiz.

```python try
import numpy as np
rng = np.random.default_rng(0)
oqitish = X["mean_radius"].to_numpy()
yangi = oqitish * 1.15 + rng.normal(0, 0.5, len(oqitish))   # o'lchov uskunasi almashgan
siljish = (yangi.mean() - oqitish.mean()) / oqitish.std()
print("standartlashgan siljish:", round(siljish, 2), "→", "drift!" if abs(siljish) > 0.3 else "normal")
```

## Hayot sikli

Ma'lumot → o'qitish → baholash → saqlash → joylashtirish → kuzatish → (drift bo'lsa) qayta o'qitish. Bu siklni
avtomatlashtirish — MLOps ning asosiy maqsadi.

## Tezkor savol

```quiz
question: Model joylashtirilgandan keyin sifati asta-sekin pasaydi. Eng ehtimolli sabab?
options:
  - Data drift — real ma'lumot o'qitishdagidan farq qila boshlagan
  - Model fayli eskirgan
  - Server soati noto'g'ri
answer: A
explain: Ma'lumot taqsimoti o'zgarsa, eski qonuniyatlar ishlamay qoladi — qayta o'qitish kerak.
```
