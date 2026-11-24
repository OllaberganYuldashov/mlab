# ML asoslari

## Mashinali o'qitish nima?

Mashinali o'qitish (Machine Learning, ML) — kompyuter qoidalarni dasturchidan emas, **ma'lumotlardan**
o'rganadigan yondashuv. Biz misollar beramiz, model esa ulardagi qonuniyatni topadi.

## An'anaviy dasturlash va ML

An'anaviy dasturda: *qoidalar + ma'lumot → javob*. ML da: *ma'lumot + javoblar → qoidalar (model)*.
Masalan, spam filtri uchun minglab "spam" va "spam emas" xatlar beriladi — model farqni o'zi o'rganadi.

## O'qitish turlari

- **Nazoratli (supervised):** har misolning to'g'ri javobi bor (narxni bashorat qilish, rasmni tasniflash).
- **Nazoratsiz (unsupervised):** javoblar yo'q, model guruhlarni topadi (mijozlarni segmentlash).
- **Mustahkamlovchi (reinforcement):** agent mukofot orqali o'rganadi (o'yin o'ynash).

## Asosiy atamalar

- **Belgi (feature)** — kirish ma'lumoti ustuni, masalan, uy maydoni.
- **Nishon (target)** — bashorat qilinadigan qiymat, masalan, uy narxi.
- **Model** — belgilardan nishonni hisoblaydigan funksiya.
- **O'qitish va test to'plami** — model biri bilan o'rganadi, ikkinchisi bilan tekshiriladi.

## O'zing sinab ko'r

Quyidagi kod eng oddiy "model"ni ko'rsatadi: o'rtacha qiymat bilan bashorat.

```python try
narxlar = [120, 135, 150, 128]
bashorat = sum(narxlar) / len(narxlar)
print(f"Yangi uy narxi taxminan: {bashorat:.1f}")
```

**Savol:** bu modelning kamchiligi nimada? (Maslahat: u uy maydoniga qaraydimi?)

## Tezkor savol

```quiz
question: Spam filtrini "spam" va "spam emas" deb belgilangan xatlarda o'qitish qaysi turga kiradi?
options:
  - Nazoratli (supervised)
  - Nazoratsiz (unsupervised)
  - Mustahkamlovchi (reinforcement)
answer: A
explain: Har xatning to'g'ri javobi (belgisi) bor — bu nazoratli o'qitish.
```
