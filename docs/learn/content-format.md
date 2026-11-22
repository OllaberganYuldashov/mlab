# Kontent kod sifatida: Markdown + YAML va `import_content`

## Bu nima (2–3 gap, oddiy tilda)
Kurs matnlari (ma'ruzalar, keyin testlar va topshiriqlar) bazada emas, repodagi `content/` papkasida oddiy
matn fayllari sifatida turadi. `import_content` buyrug'i ularni o'qiydi, tekshiradi va bazaga yuklaydi.
Shunda har o'zgarish Git'da saqlanadi va PR orqali ko'rib chiqiladi.

## Nega aynan u tanlandi (va muqobillari)
ADR-0002: Markdown (o'qish va yozish oson, GitHub'da chiroyli ko'rinadi) + YAML (meta ma'lumot).
Muqobillar: bitta katta YAML/JSON (matn yozish noqulay), Jupyter notebook (diff o'qilmaydi), faqat admin
panel (versiya va ko'rib chiqish yo'q). Kutubxona: **PyYAML** — Python'dagi eng keng tarqalgan YAML o'quvchi.

## Bizning loyihada qayerda ishlatilgan
- `content/course.yaml`, `content/topics/M01-ml-asoslari/` — namuna.
- `backend/apps/courses/content.py` — o'qish, tekshirish va yozish.
- `backend/apps/courses/management/commands/import_content.py` — buyruq.

## Asosiy tushunchalar
1. **Idempotentlik.** Bir xil fayllarni 10 marta import qilsangiz ham natija bitta — ikkinchisidan boshlab
   "O'zgarish yo'q." chiqadi. Xavfsiz qayta ishga tushirish mumkin.
2. **Tranzaksiya.** Avval hamma fayl tekshiriladi, keyin yoziladi. Bitta faylda xato bo'lsa — hech narsa
   yozilmaydi (yarim import yo'q).
3. **Aniq xato.** `topics/M02-.../meta.yaml:3: order takrorlangan` — qaysi fayl, qaysi qator, nima noto'g'ri.
4. **`safe_load`.** YAML fayl ichida Python kodi ishga tushirib bo'lmaydi (`!!python/...` teglari rad etiladi).
5. **Maxfiy papkalar.** `tests/hidden/` va `solutions/` hech qachon ma'ruza importiga tushmaydi va API'ga chiqmaydi.

## Rasmiy hujjat va yaxshi manbalar
- PyYAML hujjati: `yaml.safe_load`.
- CommonMark (Markdown standarti): https://commonmark.org/help/
- Django: "Writing custom django-admin commands".

## Kichik mashq
`content/topics/M01-ml-asoslari/lecture.md` ga yangi `## Qadam` qo'shing va
`cd backend && uv run python manage.py import_content ../content` ni ishga tushiring: `yaratildi: step: 1`.
Keyin `meta.yaml` da `order: 1` ni `order: 0` qiling — xato xabarini o'qing va bazada hech narsa o'zgarmaganini ko'ring.
