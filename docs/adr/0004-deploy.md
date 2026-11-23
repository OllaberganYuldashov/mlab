# ADR-0004: Prod konteynerlari va deploy usuli

- **Sana:** 2026-11-23
- **Holat:** Qabul qilindi (konteyner tuzilmasi); deploy usuli — taklif (server tarmog'iga qarab egasi yakuniy tanlaydi)

## Kontekst
Bitta universitet serveri (4 GB RAM, GPU yo'q, 100 faol talaba — NFR-08). Server hozir boshqa lokal tarmoqda,
ko'chirish muddati noma'lum, domen tayyor emas (egasining 2026-11-23 qarori: R0 dan keyin kutmasdan R1 ga o'tiladi).
Shu sababli prod konteynerlari serversiz tayyorlanadi va tekshiriladi; birinchi haqiqiy deploy keyin.

## Variantlar

**1. ASGI server**
| Variant | Afzallik | Kamchilik |
| --- | --- | --- |
| uvicorn (2 worker) | Bitta jarayon turi, Channels (I1/I4) uchun tayyor, kam RAM | Jarayon boshqaruvi gunicorn'chalik boy emas |
| gunicorn + uvicorn worker | Yetuk jarayon boshqaruvi | Ikki qatlam, ortiqcha RAM |
| daphne | Channels'ning o'zi bilan keladi | Kamroq keng tarqalgan, sozlamalari kam |

**2. Deploy usuli (R0-16 da amalga oshadi)**
| Variant | Afzallik | Kamchilik |
| --- | --- | --- |
| A. GitHub Actions → SSH | Oddiy, server tashqaridan ko'rinishi kerak | Server boshqa lokal tarmoqda bo'lsa ulanib bo'lmaydi; SSH kalit GitHub Secrets'da |
| B. Self-hosted runner (serverda) | Server tashqariga ochilmaydi (runner o'zi GitHub'ga chiqadi), lokal tarmoqda ishlaydi | Runner serverda doim ishlashi kerak; runner'ni himoyalash (faqat main/teg) |
| C. Qo'lda (`git pull` + compose) | Hech qanday avtomatika | Takrorlanuvchan emas, `good-*` tegga qaytish qo'lda |

## Qaror
- **ASGI:** uvicorn, 2 worker; `--proxy-headers` Caddy ortida. Yangi bog'liqlik: `uvicorn` (lockfile bo'yicha).
- **Konteynerlar:** `backend/Dockerfile` (multi-stage, `uv sync --frozen`, UID 10001, `read_only` + `cap_drop: ALL` compose'da),
  `frontend/Dockerfile` (Node build → Caddy, UID 10002). Servislar: `db`, `redis`, `migrate` (bir martalik migratsiya +
  collectstatic), `web`, `caddy`. Faqat Caddy 80/443 ni ochadi. RAM: db 1 GB, web 1 GB, redis 256 MB, caddy 128 MB.
- **Celery worker va sandbox** compose'ga I3 da qo'shiladi: kodda hali Celery yo'q, bo'sh servis healthcheck'dan o'tmaydi.
- **Deploy usuli:** tavsiya **B (self-hosted runner)**, chunki server boshqa lokal tarmoqda va tashqaridan SSH ochiq bo'lmasligi mumkin.
  A — server ochiq IP/port-forward bilan ko'rinsa. Yakuniy tanlov — egasiniki, server joyi aniq bo'lgach.
  R0-16 ikkala usulga mos bo'lishi uchun deploy mantig'ini serverdagi skriptga (`deploy/`) yig'adi, workflow faqat uni chaqiradi.

## Oqibatlar
- `docker compose ... config` va statik testlar (`backend/tests/test_nfr_08_prod_deploy.py`) repoda tekshiriladi; image build va Caddyfile `caddy validate`
  haqiqiy docker muhitida (egasi kompyuterida yoki server) sinaladi — bulut sessiyasida docker daemon yo'q.
- HSTS `includeSubDomains`/preload va CSP kengaytmasi (Pyodide, I2) domen ma'lum bo'lgach qayta ko'riladi.
- Server tayyor bo'lganda: birinchi deploy, smoke test, zaxira tiklash sinovi (R0-16 ning serverga bog'liq qismi).
