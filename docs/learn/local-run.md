# Loyihani o'z kompyuteringizda ishlatish (Windows)

> #173. Maqsad: serverni kutmasdan har merge'dan keyin nima yaratilganini o'z kompyuteringizda ko'rish.
> Bitta buyruq — butun ilova: baza, Redis, backend, frontend va Python laboratoriyasi (Pyodide).

## 1. Bir martalik o'rnatish

1. **Git for Windows** — https://git-scm.com/download/win (o'rnatishda hamma variantlar default).
2. **Docker Desktop** — https://www.docker.com/products/docker-desktop/ . O'rnatgach kompyuterni qayta yoqing,
   Docker Desktop'ni oching va pastki chap burchakda "Engine running" yozuvini kuting.
   (WSL 2 so'rasa — "OK", u o'zi o'rnatadi.)
3. Python, Node.js yoki PostgreSQL o'rnatish **shart emas** — hammasi konteyner ichida.

## 2. Birinchi ishga tushirish

PowerShell'ni oching (Start → "PowerShell") va:

```powershell
cd $HOME\Documents
git clone https://github.com/OllaberganYuldashov/mlab.git
cd mlab
docker compose up --build
```

Birinchi marta **5–10 daqiqa** ketadi: image'lar va Pyodide (~100 MB+) yuklab olinadi. Oxirida shu qator
chiqadi:

```text
migrate-1  | Demo tayyor (...). Kirish: Hemis ID 900000000001 (admin), ...
```

Keyin brauzerda (Chrome) **http://localhost:8080** ni oching.

| Rol | Hemis ID | Parol |
| --- | --- | --- |
| Admin (super admin) | 900000000001 | mlab-demo-2026 |
| O'qituvchi | 900000000002 | mlab-demo-2026 |
| Talaba (3 ta) | 900000000011, 900000000012, 900000000013 | mlab-demo-2026 |

Bu akkauntlar va "Demo guruh" faqat lokal kompyuter uchun (`seed_demo` buyrug'i prod sozlamalarida ishlamaydi).
Hamma mavzu laboratoriyasi ochiq. Django admin: http://localhost:8080/admin/ (admin akkaunti bilan).

To'xtatish: PowerShell oynasida `Ctrl + C`. Fonda ishlatish: `docker compose up -d --build`,
to'xtatish: `docker compose down` (ma'lumot saqlanadi).

## 3. Har kuni: yangi o'zgarishlarni ko'rish

```powershell
cd $HOME\Documents\mlab
git checkout main
git pull
docker compose up --build
```

Yangi migratsiyalar va kontent o'zi qo'llanadi, sizning ma'lumotlaringiz (yozgan kodingiz, test urinishlari)
saqlanib qoladi. Nimani sinab ko'rish kerakligi — kunlik hisobotdagi "Lokal ko'rish" qatorida.

## 4. Merge bo'lmagan PR'ni ko'rish

Masalan, PR #131:

```powershell
git fetch origin pull/131/head:pr-131
git checkout pr-131
docker compose up --build
```

Qaytish: `git checkout main`. PR'da migratsiya bo'lsa, main'ga qaytganda baza bilan mos kelmasligi mumkin —
unda 6-bo'limdagi "noldan boshlash".

## 5. Muammolar

| Belgi | Sabab va yechim |
| --- | --- |
| `port is already allocated` (8080) | Boshqa dastur band qilgan. `$env:MLAB_PORT=8090; docker compose up --build` → http://localhost:8090 |
| `port is already allocated` (5432 yoki 6379) | Kompyuterda PostgreSQL/Redis o'rnatilgan. `$env:POSTGRES_PORT=55432; $env:REDIS_PORT=56379` va qayta |
| `docker: command not found` / `cannot connect` | Docker Desktop ochilmagan — oching va "Engine running" ni kuting |
| `migrate-1 exited with code 1` | `docker compose logs migrate` natijasini Claude'ga yuboring |
| Sahifa ochiladi, lekin eski ko'rinishda | `Ctrl + F5` (brauzer keshi) |
| Kompyuter sekinlashdi | Docker Desktop → Settings → Resources: Memory 4 GB yetadi |

## 6. Noldan boshlash (DIQQAT)

Bazani butunlay o'chirib, demo ma'lumotni qaytadan yaratish:

```powershell
docker compose down -v
docker compose up --build
```

`-v` **lokal bazadagi hamma narsani o'chiradi** (sizning sinov akkauntlaringiz, yozgan kodlar). Serverga ta'siri yo'q.

## 7. Bu qanday ishlaydi

- `compose.yaml` — 5 servis: `db` (PostgreSQL 16), `redis`, `migrate` (bir martalik: migratsiya, statik fayllar,
  `import_content`, `seed_demo`), `web` (Django), `caddy` (React ilovasi + Pyodide + proksi).
- Image'lar serverdagi bilan **bir xil Dockerfile'lardan** yig'iladi (`backend/Dockerfile`, `frontend/Dockerfile`,
  `deploy/Caddyfile`) — lokal ishlasa, serverda ham ishlashiga ishonch ortadi. Farqi: `config.settings.dev`
  (HTTPS talab qilinmaydi), soxta parollar, AI tutor doim `fake`.
- Portlar faqat `127.0.0.1` ga ochiq — tarmoqdagi boshqa kompyuterlar ulana olmaydi.
- `.gitattributes`: Windows'da ham fayllar LF satr oxiri bilan olinadi (konteyner ichida CRLF xato beradi).
- Hali yo'q: avtobaholovchi sandbox (I3), haqiqiy AI tutor (I4).

## 8. Dasturchi rejimi (ixtiyoriy)

Kodni o'zgartirib darhol ko'rish uchun (Python 3.12 + uv va Node 22 kerak): `docker compose up -d db redis`,
backend'da muhit o'zgaruvchilari (`.env.example` qiymatlari) bilan `uv run python manage.py runserver`, frontend'da
`npm run dev` → http://localhost:5173 (Vite `/api`, `/ws`, `/admin` ni 8000 ga yo'naltiradi).
