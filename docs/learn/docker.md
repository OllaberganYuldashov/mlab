# Docker va Docker Compose

## Bu nima (2–3 gap, oddiy tilda)
**Docker** dasturni kerakli hamma narsasi bilan birga "konteyner"da ishga tushiradi: kompyuteringizga
PostgreSQL yoki Redis'ni o'rnatmasdan, ularning tayyor nusxasini (image) yuklab, alohida qutida ishlatasiz.
**Docker Compose** bir nechta konteynerni bitta faylda (`compose.yaml`) ta'riflaydi va bitta buyruq bilan ko'taradi.

## Nega aynan u tanlandi (va muqobillari)
- ADR-0001: lokal ishlab chiqish va prod (universitet serveri) bir xil vositada — Docker Compose.
- Muqobillari: PostgreSQL va Redis'ni to'g'ridan-to'g'ri o'rnatish (versiyalar kompyuterdan kompyuterga
  farq qiladi, o'chirish qiyin), Kubernetes (bitta server uchun ortiqcha murakkab).
- Bulut sessiyasida (Claude) Docker daemon yo'q — u yerda PostgreSQL va Redis oldindan o'rnatilgan va
  setup skript ishga tushiradi. `compose.yaml` — egasining kompyuteri uchun.

## Bizning loyihada qayerda ishlatilgan
- `compose.yaml` — `db` (PostgreSQL 16) va `redis` (Redis 7), sog'liq tekshiruvlari, nomli volume'lar.
- Keyin: `deploy/compose.prod.yaml` (R0-15) — prod uchun alohida fayl; `sandbox/` — talaba kodini
  baholovchi konteyner (I3).

## Asosiy tushunchalar
1. **Image va konteyner.** Image — tayyor shablon (`postgres:16.10-alpine`), konteyner — undan ishga
   tushgan nusxa. Versiya aniq yoziladi (`latest` emas), shunda hamma bir xil versiyada ishlaydi.
2. **Nomli volume** (`db-data`). Konteyner o'chirilsa ham baza ma'lumoti volume'da saqlanadi.
3. **Healthcheck.** `pg_isready` va `redis-cli ping` servis haqiqatan tayyor ekanini tekshiradi;
   `docker compose ps` da `healthy` yozuvi chiqadi.
4. **Portni faqat `127.0.0.1` ga ochish.** Baza faqat sizning kompyuteringizdan ko'rinadi, Wi-Fi'dagi
   boshqa qurilmalardan emas.
5. **Soxta parol.** `mlab:mlab` — faqat lokal dev uchun, `.env.example` dagi `DATABASE_URL` bilan mos.
   Haqiqiy parol hech qachon `compose.yaml` ga yozilmaydi.

## Kundalik buyruqlar

| Vazifa | Buyruq |
| --- | --- |
| Servislarni ko'tarish | `docker compose up -d db redis` |
| Holatini ko'rish | `docker compose ps` (`healthy` bo'lishi kerak) |
| Loglar | `docker compose logs -f db` |
| To'xtatish (ma'lumot saqlanadi) | `docker compose down` |
| Backend testlari | `cd backend && uv run pytest` (servislar ko'tarilgandan keyin) |

**Xavfli buyruq:** `docker compose down` ga `-v` (yoki `--volumes`) qo'shilsa, `db-data` va `redis-data`
volume'lari **butunlay o'chadi** — lokal baza bo'shab qoladi. Faqat bazani ataylab noldan yaratmoqchi
bo'lsangiz ishlating (masalan, migratsiyalar tarixi buzilganda). Claude bu buyruqni sizning ruxsatingizsiz
ishga tushirmaydi.

Port band bo'lsa (kompyuterda boshqa PostgreSQL ishlayotgan bo'lsa): `POSTGRES_PORT=55432 docker compose up -d db`
va `DATABASE_URL` dagi portni ham o'zgartiring.

## Rasmiy hujjat va yaxshi manbalar
- Docker Compose: https://docs.docker.com/compose/
- PostgreSQL rasmiy image: https://hub.docker.com/_/postgres
- Redis rasmiy image: https://hub.docker.com/_/redis

## Kichik mashq
`docker compose up -d db redis`, keyin `docker compose ps` — ikkala servis `healthy` bo'lguncha kuting.
So'ng `docker compose down` qiling va yana `up` qiling: `cd backend && uv run python manage.py migrate`
ikkinchi marta "No migrations to apply" desa — volume ma'lumotni saqlab qolgan.
