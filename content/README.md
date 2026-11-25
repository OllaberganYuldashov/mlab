# content/ — MLab kurs kontenti (kod sifatida)

> Format: `docs/adr/0002-content-format.md` (R0-13). Import: `cd backend && uv run python manage.py import_content ../content`.
> Kontent Markdown va YAML fayllarida, Git'da versiyalanadi,
> `import_content` buyrug'i bilan bazaga yuklanadi. Fan dasturidan faqat mavzular ro'yxati olingan;
> yetishmayotgan kontentni Claude sodda va minimal holda yozadi (SRS CNT-04).

## Ma'ruza fayli qanday yoziladi

`topics/<KOD>-<slug>/meta.yaml` — `code` (masalan, `M01`), `title`, `order`.
`topics/<KOD>-<slug>/lecture.md` — birinchi qator `# Ma'ruza nomi`, keyin har `## Qadam sarlavhasi` — bitta qadam
(CNT-02: 5–10 qadam). Kod bloki (```) ichidagi `##` qadam hisoblanmaydi.

Qadam ichida (CNT-02, I2-02):

- **Rasm:** `![Alt matn](images/nomi.png)` — fayl `topics/<KOD>-<slug>/images/` da, PNG/JPEG/WebP, ≤ 500 KB,
  alt matn majburiy (NFR-13). SVG va tashqi havolalar qabul qilinmaydi. Rasm baytlari bazaga yoziladi.
- **"O'zing sinab ko'r":** ```` ```python try ```` — talaba brauzerda ishga tushiradi (Pyodide, I2-13). `try` faqat `python` bilan.
- **Tezkor savol** (qadamda bittagacha, baholanmaydi):

  ````text
  ```quiz
  question: Savol matni?
  options:
    - Birinchi variant
    - Ikkinchi variant
  answer: A          # A..F
  explain: Nega shu javob to'g'ri (ixtiyoriy)
  ```
  ````

## Interaktiv vizual qadam (CNT-03)

Qadam ichida ```` ```visual ```` YAML bloki — oldindan tayyorlangan vidjet (ixtiyoriy kod bajarilmaydi):

- `widget: line-fit` — chiziqli regressiya: qiyalik va siljish slayderlari, MSE; ixtiyoriy `points: [[x, y], ...]` (2..50).
- `widget: knn` — k-NN qaror hududlari, k slayderi; ixtiyoriy `seed` (0..1000), `k_max` (3..25).
- Ikkalasida ham ixtiyoriy `title`. Import blokni tekshiradi va JSON ko'rinishida saqlaydi.

## Mavzu testi (CNT-05, Aiken)

`topics/<KOD>-<slug>/quiz.aiken` — savollar banki (ixtiyoriy fayl). Har savol: matn (bir yoki bir necha qator),
`A)` yoki `A.` bilan 2–6 variant, `ANSWER: <harf>`, keyin bo'sh qator. Moodle'dan eksport qilingan fayl (BOM, CRLF)
ham o'qiladi. Fayldan olib tashlangan savol bazadan o'chirilmaydi — arxivlanadi (eski urinishlar saqlanadi).
Savol matni o'zgarsa — u yangi savol hisoblanadi (eski arxivga); faqat variantlar o'zgarsa — o'sha savol yangilanadi.

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

### Topshiriq fayllari (I3-02, ADR-0007)

```text
labs/A01-pandas-numpy/
  assignment.yaml            # code, title, topic (M02), statement ({parametr} bilan), steps [{key, title, points}] — jami 100,
                             # challenge, independent (ixtiyoriy)
  variants/basic-1.yaml      # params: {dataset: iris, column: ...}; har daraja (basic, medium, advanced) kamida 5 ta
  tests/visible/<qadam>.py   # "Tekshirish" — brauzerda (ixtiyoriy)
  tests/hidden/<qadam>.py    # "Topshirish" — faqat sandbox'da, har qadamga majburiy; talabaga hech qachon ko'rinmaydi
  solutions/<daraja>.py      # yoki umumiy solution.py; {parametr} li shablon; import qilinmaydi
```

Yechim tekshiruvi (har variant, ko'rinadigan va yashirin testlar; bo'sh kod bilan yashirin test o'tmasligi ham):

```bash
cd backend && uv run python manage.py check_lab_solutions ../content --python <sandbox paketlari o'rnatilgan python>
# yoki sandbox image bilan: --docker mlab-sandbox:dev   (CI job — I3-18)
```

Tayyor: **A1–A5** (I3-15). Server sandbox'ida seaborn yo'q — topshiriqlardagi grafiklar matplotlib bilan.

Test funksiyasi: `def test_<nom>(ns, params):` — `ns` talaba kodi bajarilgandan keyingi global nomlar, `params` — variant
parametrlari. Shartdagi har `{parametr}` har variantda bo'lishi shart (import tekshiradi).

Jamoaviy mini-loyihalar (R2): tabular tasniflash konveyeri, regressiya konveyeri, klasterlash va segmentatsiya.

## Egasining materiallari

Egasi o'z taqdimot va Aiken test fayllarini `content/source/` ga qo'yadi (o'z mualliflik materiallari).
Claude ulardan faqat mavzu tuzilmasi va savollarni oladi, matnni qadamlarga sodda qilib qayta yozadi.
