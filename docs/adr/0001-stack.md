# ADR-0001: Texnologiyalar steki

- **Holat:** Qabul qilingan (SRS v2 bilan birga, 2026-11-22)
- **Qaror qabul qildi:** egasi (Product Owner / CTO), taklif: Claude

## Kontekst

Yopiq ta'lim platformasi: 100 ta bir vaqtdagi talaba, real vaqt monitoringi, brauzerda Python,
begona kodni xavfsiz tekshirish. Server: 4 GB RAM, CPU, GPU yo'q. Ishlab chiquvchi — Claude (tungi runlar),
egasi — havaskor dasturchi, texnologiyalarni o'rganmoqchi. Shuning uchun "boring", yaxshi hujjatlangan,
bitta asosiy tilga tayangan stek kerak.

## Qaror

| Qism | Tanlov |
| --- | --- |
| Backend | Python 3.12, Django 5 (LTS liniyasi), Django REST Framework |
| Real vaqt | Django Channels + Redis channel layer (WebSocket) |
| Fon vazifalari | Celery + Redis |
| Ma'lumotlar bazasi | PostgreSQL 16 |
| Admin | Django Admin (super admin va admin uchun) |
| Frontend | React 18+ va TypeScript, Vite, React Router, TanStack Query |
| Kod muharriri | CodeMirror 6, o'z yengil notebook komponentimiz |
| Brauzer Python | Pyodide Web Worker ichida; A15 uchun stlite |
| Sandbox | Docker: tarmoqsiz, read-only, root'siz, 512 MB, 1 CPU, 60 s, pids-limit; navbat 2 parallel |
| AI | Gemini API, `tutor.providers` orqali almashtiriladigan; testlarda `fake` provayder |
| Veb-server | Caddy (avtomatik HTTPS, statik va Pyodide fayllari) |
| Paketlar | uv (Python), npm (frontend) |
| Sifat | ruff, mypy + django-stubs, pytest + pytest-django, Vitest, Playwright, ESLint, gitleaks, pip-audit |
| Deploy | GitHub Actions → Docker Compose serverda (usul R0-15 da: SSH yoki self-hosted runner) |

## Ko'rib chiqilgan muqobillar

| Muqobil | Nega tanlanmadi |
| --- | --- |
| FastAPI | Admin, auth, ORM va migratsiyalarni qo'lda yig'ish kerak; MVP sekinlashadi |
| Node.js (NestJS) + Socket.IO | Ikkinchi asosiy til; ML fani Python'da — kontent va testlar ham Python |
| Moodle + CodeRunner | Avtobaholash bor, lekin brauzer laboratoriyasi, jonli panel, kirish oynalari, moslashuvchan variantlar yo'q |
| Server Jupyter (JupyterHub) | Har talabaga kernel — 4 GB RAM'ga sig'maydi |
| JupyterLite | Boy, lekin paste nazorati va telemetriyani boshqarish qiyin (SRS 12-bo'lim, 5-taklif) |
| gVisor sandbox | Kuchliroq izolyatsiya; R2 da baholanadi (Docker cheklovlari MVP uchun yetarli, yashirin testlar baribir serverda) |
| HTMX + Django shablonlari | Notebook va jonli panel uchun yetarli emas |

## Oqibatlar

- Asosiy til bitta (Python), frontend TypeScript. Egasi uchun `docs/learn/` da har biriga dars.
- Pyodide birinchi yuklanishi og'ir (≈6–10 MB va paketlar) — o'z serverdan va kesh bilan beriladi; I2 da monoblokda sinov.
- Sandbox Docker soketiga kirish talab qiladi — faqat Celery worker'da, alohida cheklangan foydalanuvchi va xavfsizlik ko'rigi bilan (R1 I3).
- Gemini almashtiriladigan qatlam orqali — pullik modelga o'tish (R4) kodni o'zgartirmaydi.
