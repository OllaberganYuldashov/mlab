# ARCHITECTURE — L1 · MLab

> Manba: `docs/SRS.md` 3 va 8-bo'limlar, `docs/adr/0001-stack.md`. Skelet qurilgach Claude tafsilotlarni to'ldirib boradi.

## Umumiy ko'rinish

```text
 Talaba brauzeri                         O'qituvchi brauzeri
 ├─ React SPA                            ├─ React SPA: jonli panel, guruhlar, oynalar, jurnal
 ├─ Notebook (CodeMirror 6)              └─ WebSocket: holatlar, yordam navbati
 ├─ Pyodide Web Worker: kod va ko'rinadigan testlar
 └─ WebSocket: oyna ochildi, chat, natija
            │  HTTPS · WebSocket
 ┌──────────▼───────────────────── Universitet serveri (Ubuntu, 4 GB, GPU'siz) ─────────┐
 │ Caddy: HTTPS, SPA, statik, Pyodide fayllari                                          │
 │   ├── Django + DRF (gunicorn/uvicorn): API, Django Admin, AI proksi                   │
 │   └── Django Channels (ASGI): WebSocket, monitoring, chat                             │
 │ Celery worker ── navbat (Redis) ── Sandbox konteynerlar (tarmoqsiz, 512 MB, 60 s) ×2  │
 │ PostgreSQL 16          Redis 7 (channel layer, navbat, kesh)                          │
 └───────────────────────────────────────┬──────────────────────────────────────────────┘
                                         │ HTTPS, faqat savol va kod, ismsiz
                                   Gemini API (Google)
```

## Komponentlar

| Komponent | Vazifasi | Talablar |
| --- | --- | --- |
| `accounts` | User (Hemis ID login), rollar, rozilik, lockout, parol tiklash | AUTH, 7-bo'lim |
| `sections` | Guruh, a'zolik, qo'shilish tokeni va QR, guruh sozlamalari, kirish oynalari | SEC, SET, ACC |
| `courses` | Course, Topic, Lecture, Step, Quiz, Dataset; kontent importi | CNT, DAT |
| `labs` | Notebook holati, avtosaqlash, `mlab.load()` | LAB |
| `grading` | Assignment, Variant, Submission, sandbox navbati, ball, daraja tanlash | AGR, ADP, GRD-01..04 |
| `monitoring` | Talaba holati (plitka), yordam navbati, guruh grafigi | MON |
| `chat` | Guruh chati, moderatsiya, e'lonlar | COM |
| `tutor` | AI provayder qatlami (fake, gemini), rejimlar, limitlar, log | AI |
| `integrity` | Paste qaydlari, tushunish savollari, nazorat rejimi, belgilar | INT |
| `certificates` | Sertifikat PDF, QR, tekshirish sahifasi, bekor qilish | GRD-05..07 |
| `reports` | Excel/PDF hisobotlar, ActivityEvent, "Mening ma'lumotlarim" | RPT |
| `audit` | AuditLog, tizim holati | ADM |

## Ma'lumotlar modeli

`docs/SRS.md` 3-bo'lim. Asosiy qoidalar:

- Vaqtlar `timestamptz`, ko'rsatish Asia/Tashkent.
- Ballar `Decimal(5,2)`; vaznlar kurs darajasida.
- Talaba bir vaqtda bitta faol `Membership` (qisman unikal indeks).
- Sozlamalar ikki darajada: kurs default → guruh override.
- Kontent `content/` papkasida (Markdown + YAML), `import_content` bilan bazaga; versiya raqami saqlanadi.

## Tashqi integratsiyalar

Gemini API (server proksi orqali), GitHub Actions (CI/CD). R3: Google OAuth, SMTP.

## Deploy sxemasi

Docker Compose: `caddy`, `web` (ASGI), `worker` (Celery), `db`, `redis`; sandbox image alohida.
GitHub Actions: test → image build → deploy → smoke test. Usul (SSH yoki self-hosted runner) R0-15 da tanlanadi.
Zaxira: kunlik `pg_dump` + media, oylik tiklash sinovi (ADM-04).

## Xavfsizlik chegaralari

1. **Brauzer ↔ server:** hamma API obyekt darajasida ruxsat tekshiradi; sessiya cookie (HttpOnly, Secure, SameSite=Lax) + CSRF.
2. **Server ↔ sandbox:** talaba kodi faqat sandbox'da; konteyner tarmoqsiz; natija faqat ball va qisqa xabar.
3. **Server ↔ Gemini:** API kaliti faqat serverda; FIO va Hemis ID yuborilmaydi.
4. **Natijalarni ko'rsatish:** talaba chiqishi izolyatsiyalangan iframe va qat'iy CSP ichida.

## Kuzatuv

Strukturali JSON loglar (request id bilan), `/healthz` va `/readyz`, navbat uzunligi va sandbox xatolari metrikasi,
tizim holati sahifasi (ADM-03).

## RAM taqsimoti (taxminiy)

OS va Caddy ~500 MB; PostgreSQL ~500 MB; Redis ~150 MB; Django + Channels ~600 MB; Celery ~250 MB; sandbox 2 × 512 MB; zaxira ~500 MB.
