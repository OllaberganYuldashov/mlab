# SECURITY — L1 · MLab: secret'lar, shaxsiy ma'lumotlar, sandbox

## Qoida

Secret faqat uch joyda: parol menejeri, GitHub Secrets, serverdagi `.env` (chmod 600).
Chat, repo, log, PR, issue, bulut muhiti o'zgaruvchilari va scheduled task promptida — hech qachon.

## Sozlamalar ro'yxati

> Har yangi sozlama shu jadvalga qo'shiladi (qiymatsiz).

| Nomi | Nima uchun | Dev/test qiymati | Prod qiymati qayerda |
| --- | --- | --- | --- |
| SECRET_KEY | Django kriptografiyasi (prod: ≥ 50 belgi, dev/test qiymati rad etiladi) | .env.example (soxta) | Server .env |
| DATABASE_URL | PostgreSQL | .env.example (soxta) | Server .env |
| REDIS_URL | Channels, Celery, kesh | .env.example | Server .env |
| ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS | Domen (prod'da `*` taqiqlangan) | localhost | Server .env |
| DEBUG | Faqat dev (prod'da doim false) | .env.example | — |
| TIME_ZONE | Vaqt zonasi (default Asia/Tashkent) | .env.example | Server .env |
| TRUSTED_PROXY_COUNT | Mijoz IP'sini aniqlash (Caddy ortida 1; prod'da 0 bo'lsa ilova ishga tushmaydi). Haqiqiydan katta — X-Forwarded-For soxtalashtiriladi; ilova porti faqat ichki tarmoqda | .env.example (0) | Server .env (1) |
| AUTH_REGISTER_RATE | Ro'yxatdan o'tish cheklovi (IP bo'yicha, IPv6 — /64; default 60/hour) | .env.example | Server .env |
| AUTH_REGISTER_GLOBAL_RATE | Umumiy ro'yxatdan o'tish chegarasi (default 300/hour) | .env.example | Server .env |
| SECTION_JOIN_PREVIEW_RATE | Havola bo'yicha guruhni ko'rish, IP bo'yicha (default 600/hour) | .env.example | Server .env |
| SECTION_JOIN_RATE | A'zolik so'rovi, talaba bo'yicha (default 30/hour) | .env.example | Server .env |
| LAB_SAVE_RATE | Laboratoriya avtosaqlashi, talaba bo'yicha (default 60/min) | .env.example | Server .env |
| VARIANT_SECRET | Variant tanlash HMAC kaliti (AGR-08); bo'sh bo'lsa SECRET_KEY dan hosil qilinadi. Almashsa yangi talabalar varianti o'zgaradi, berilganlari saqlanadi | Parol menejeri | Server .env |
| LAB_EVENT_RATE | Laboratoriya hodisalari (paste qaydi), talaba bo'yicha (default 120/min) | .env.example | Server .env |
| SECTION_CREATE_RATE | Guruh yaratish, o'qituvchi bo'yicha (default 30/hour) | .env.example | Server .env |
| AUTH_LOGIN_RATE | Login so'rovlari IP bo'yicha (default 120/minute); lockout (5 xato → 15 daqiqa, Hemis ID + IP) kodda qat'iy | .env.example | Server .env |
| AUTH_LOGIN_GLOBAL_RATE | Umumiy login chegarasi (default 600/minute; Argon2 yuklamasi) | .env.example | Server .env |
| AUTH_CHANGE_PASSWORD_RATE | Parol almashtirish urinishlari, foydalanuvchi bo'yicha (default 10/hour) | .env.example | Server .env |
| AUTH_RESET_PASSWORD_RATE | Parol tiklash, tiklovchi bo'yicha (default 60/hour) | .env.example | Server .env |
| AUTH_INSTRUCTOR_CREATE_RATE | O'qituvchi yaratish, yaratuvchi bo'yicha (default 30/hour) | .env.example | Server .env |
| POSTGRES_PASSWORD, POSTGRES_USER, POSTGRES_DB | Prod PostgreSQL (compose.prod.yaml; parol majburiy, kamida 24 belgi tasodifiy) | .env.example (soxta) | Server .env |
| SITE_ADDRESS | Caddy domeni (masalan `mlab.example.uz`; sinov uchun `:80`) — secret emas | .env.example | Server .env |
| MLAB_VERSION | Image tegi (deploy workflow qo'yadi, `good-*` teg) — secret emas | — | Server .env / workflow |
| LOG_LEVEL | Log darajasi (default INFO), secret emas | .env.example | Server .env |
| SECURE_SSL_REDIRECT | Prod: HTTP → HTTPS yo'naltirish (default true) | — | Server .env |
| GEMINI_API_KEY | AI tutor | bo'sh (AI_PROVIDER=fake) | Server .env |
| AI_PROVIDER, GEMINI_MODEL, AI_DAILY_LIMIT_PER_STUDENT | AI sozlamalari | .env.example | Server .env |
| SANDBOX_* | Sandbox cheklovlari | .env.example | Server .env |
| PUBLIC_BASE_URL | Sertifikat QR havolasi | localhost | Server .env |
| DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY, DEPLOY_KNOWN_HOSTS | Deploy (faqat SSH usuli tanlansa; self-hosted runner usulida kerak emas) | — | GitHub Secrets |
| MLAB_ENV_FILE, MLAB_BACKUP_DIR, MLAB_BACKUP_KEEP_DAYS, MLAB_REPO_DIR | Deploy/zaxira skriptlari yo'llari (secret emas; default `/opt/mlab/...`, 14 kun) | — | Server muhiti / GitHub variables |

## Secret oqib ketsa

1. Darhol yangi qiymat yaratiladi va eskisi bekor qilinadi (rotate).
2. Yangi qiymat parol menejeri, GitHub Secrets va server `.env`ga yoziladi.
3. Hodisa `docs/incidents/` va LESSONS.md'ga yoziladi.

## Shaxsiy ma'lumotlar (SRS 7-bo'lim)

- FIO, Hemis ID, IP, qurilma — shaxsiy ma'lumot. Faqat universitet serverida (O'zbekiston).
- Testda faqat factory/Faker. Haqiqiy ro'yxatlar, baholar va loglar repoga, bulut sessiyasiga va promptga tushmaydi.
- Ma'lum xavf: ro'yxatdan o'tishda "bu Hemis ID band" xabari Hemis ID mavjudligini oshkor qiladi (foydalanuvchiga aniq xabar kerak); `AUTH_REGISTER_RATE` IP bo'yicha cheklaydi, login esa umumiy javob beradi. R3 da faollashtirish kodi (#41) bilan kamayadi.
- Qo'shilish tokeni URL yo'lida keladi: so'rov logida yo'l niqoblanadi (`/api/join/[REDACTED]`), bazada faqat xeshi.
- Loglarda Hemis ID va IP maskalanadi; parol, token, cookie hech qachon loglanmaydi.
  Bu `backend/config/observability.py` dagi `JsonFormatter` da majburiy (har log qatori undan o'tadi),
  testlar: `backend/tests/test_nfr_17_observability.py`.
- Gemini'ga faqat savol, kod va mavzu konteksti; FIO va Hemis ID yuborilmaydi (AI-04).
- Saqlash muddatlari: faollik jurnali 12 oy, AI murojaatlari 6 oy (kurs tugagach) — Celery vazifasi tozalaydi.
- Parolni hech kim ko'rmaydi: faqat bir martalik vaqtinchalik parol va majburiy almashtirish (AUTH-04).

## Sandbox tahdidlar modeli (SRS 8-bo'lim)

| Tahdid | Himoya |
| --- | --- |
| Server yoki boshqa foydalanuvchilarga hujum | Kod faqat brauzerda yoki sandbox'da; konteyner `--network none`, `--read-only`, root'siz, Docker soketisiz |
| Cheksiz sikl, xotira, fork-bomba | 60 s, 512 MB, 1 CPU, `--pids-limit`, bir vaqtda 2 ta |
| Yashirin testlarni o'g'irlash | Yashirin testlar faqat serverda; natijada faqat ball va qisqa xabar |
| Brauzer natijasini soxtalashtirish | Rasmiy ball faqat server tekshiruvidan |
| Natija orqali XSS | Chiqishlar izolyatsiyalangan iframe va qat'iy CSP ichida |

Sandbox bilan bog'liq har PR `security-reviewer` agenti bilan tekshiriladi.

## Har PR uchun minimal tekshiruv

- Yangi endpoint: autentifikatsiya, rol va obyekt darajasidagi ruxsat (begona foydalanuvchi testi).
- Kiritilgan ma'lumot serializer'da tekshiriladi; mass assignment yo'q (`fields` aniq ro'yxat).
- Xom SQL yo'q yoki parametrlangan.
- Fayl yuklash: hajm va tur cheklangan.
- gitleaks, pip-audit, npm audit yashil.
