# content/ — MLab kurs kontenti (kod sifatida)

> Format R0-13 taskida ADR-0002 bilan aniqlanadi. Kontent Markdown va YAML fayllarida, Git'da versiyalanadi,
> `import_content` buyrug'i bilan bazaga yuklanadi. Fan dasturidan faqat mavzular ro'yxati olingan;
> yetishmayotgan kontentni Claude sodda va minimal holda yozadi (SRS CNT-04).

## Rejalashtirilgan tuzilma

```text
content/
  course.yaml              # kurs nomi, o'quv yili, baholash vaznlari, default sozlamalar
  topics/M01-ml-asoslari/  # lecture.md (qadamlar), quiz.aiken, meta.yaml
  labs/A01-pandas-numpy/   # assignment.yaml, variants/, tests/visible/, tests/hidden/, solutions/
  datasets/                # kichik CSV fayllar + sources.yaml (manba va litsenziya)
  source/                  # egasining mavjud materiallari (taqdimotlar, Aiken testlar) — faqat manba
```

`tests/hidden/` va `solutions/` hech qachon brauzerga yuborilmaydi (AGR-05).

## Ma'ruzalar (M01–M22)

| # | Mavzu | Material holati |
| --- | --- | --- |
| M01 | ML asoslari | Claude yozadi |
| M02 | Ma'lumotlarga dastlabki ishlov | Claude yozadi |
| M03 | Vizualizatsiya va EDA | Claude yozadi |
| M04 | Regressiya | Claude yozadi |
| M05 | Overfitting va regulyarizatsiya | Claude yozadi |
| M06 | Cross-validation | Taqdimot bor → qadamlarga |
| M07 | Logistik regressiya | Taqdimot bor → qadamlarga |
| M08 | k-NN | Taqdimot bor → qadamlarga |
| M09 | Qarorlar daraxti | Matn, taqdimot, test bor |
| M10 | SVM | Matn, taqdimot, test bor |
| M11 | Metrikalar | Matn, taqdimot, test bor |
| M12 | k-means va DBSCAN | Matn, taqdimot, test bor |
| M13 | Ierarxik klasterlash | Matn, taqdimot, test bor |
| M14 | PCA | Matn, taqdimot, test bor |
| M15 | Assotsiativ qoidalar | Matn, taqdimot, test bor |
| M16 | Perseptron va MLP | Matn, taqdimot, test bor |
| M17 | Backpropagation | Matn, taqdimot, test bor |
| M18 | CNN (1) | Matn, taqdimot, test bor |
| M19 | CNN (2) | Matn, taqdimot, test bor |
| M20 | RNN | Claude yozadi |
| M21 | LSTM va GRU | Claude yozadi |
| M22 | MLOps asoslari | Claude yozadi |

## Amaliy mashg'ulotlar (A1–A15)

Har biri: umumiy topshiriq, 3 daraja × kamida 5 variant, 1 challenge, 1 mustaqil topshiriq (AGR-07).

| # | Mavzu | Mustaqil topshiriq g'oyasi |
| --- | --- | --- |
| A1 | Pandas va NumPy: yuklash va tozalash | Boshqa datasetda yetishmayotgan qiymatlar va outlier'lar |
| A2 | Standartlashtirish, kategorial kodlash | Pipeline: kodlash + masshtablash |
| A3 | EDA: Seaborn va Matplotlib | "Datadan 5 ta xulosa" mini-hisobot |
| A4 | Chiziqli regressiya | Polinomial regressiya bilan taqqoslash |
| A5 | Overfitting va L1/L2 | alpha'ning ta'siri grafigi |
| A6 | Logistik regressiya | Threshold va decision boundary |
| A7 | k-NN va qarorlar daraxti | Giperparametr ta'sirini taqqoslash |
| A8 | SVM va yadrolar | RBF vs Linear vs Polynomial |
| A9 | Metrikalar va Confusion Matrix | Nobalans datasetda ROC-AUC |
| A10 | k-fold va GridSearch | RandomizedSearch bilan taqqoslash |
| A11 | k-means va DBSCAN | Elbow va Silhouette |
| A12 | PCA | Tezlik va aniqlikka ta'siri |
| A13 | Ko'p qatlamli neyron to'r | scikit-learn MLP + vizual o'yin-maydon |
| A14 | CNN bilan tasvir tasnifi | MVP'da oldindan o'qitilgan model namoyishi; to'liq — R4 |
| A15 | Modelni mini-veb ilovaga aylantirish | Brauzerdagi Streamlit (stlite) |

Jamoaviy mini-loyihalar (R2): tabular tasniflash konveyeri, regressiya konveyeri, klasterlash va segmentatsiya.

## Egasining materiallari

Egasi o'z taqdimot va Aiken test fayllarini `content/source/` ga qo'yadi (o'z mualliflik materiallari).
Claude ulardan faqat mavzu tuzilmasi va savollarni oladi, matnni qadamlarga sodda qilib qayta yozadi.
