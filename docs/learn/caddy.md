# Caddy — veb-server va avtomatik HTTPS

## Bu nima (2–3 gap, oddiy tilda)
**Caddy** — internetdan kelgan so'rovlarni qabul qiladigan "eshik": u HTTPS sertifikatini o'zi oladi va
yangilaydi, React ilovasi va Pyodide fayllarini beradi, API so'rovlarini esa Django'ga uzatadi
(reverse proxy).

## Nega aynan u tanlandi (va muqobillari)
ADR-0001: konfiguratsiyasi qisqa va avtomatik HTTPS (Let's Encrypt) o'rnatilgan. Muqobillar: **Nginx**
(juda keng tarqalgan, lekin sertifikat uchun alohida certbot va ko'proq sozlash), **Traefik** (konteynerlar
uchun qulay, lekin bitta server uchun murakkabroq).

## Bizning loyihada qayerda ishlatiladi
- Hali kodda yo'q: `deploy/Caddyfile` va `deploy/compose.prod.yaml` — R0-15 (#19) da yoziladi.
- Server va domen tayyor bo'lgach (egasining 2026-11-23 qarori bo'yicha R1 orasida) birinchi deploy.
- Backend tomoni tayyor: Django Caddy ortida ishlashni biladi — `SECURE_PROXY_SSL_HEADER`
  (`backend/config/settings/prod.py`) va mijoz IP'si `TRUSTED_PROXY_COUNT=1` (`backend/apps/accounts/net.py`).

## Asosiy tushunchalar
1. **Reverse proxy.** Foydalanuvchi faqat Caddy bilan gaplashadi; Django ichki tarmoqda, tashqariga ochiq emas.
2. **Avtomatik HTTPS.** Domen ko'rsatilsa, Caddy sertifikatni o'zi oladi va muddati tugashidan oldin yangilaydi.
3. **`X-Forwarded-For`.** Caddy haqiqiy mijoz IP'sini shu sarlavhaga qo'shadi. Django faqat Caddy qo'shgan
   oxirgi qiymatga ishonadi — aks holda hujumchi IP'ni soxtalashtirib cheklovlardan qochadi.
4. **Statik fayllar.** React build va Pyodide paketlari Caddy'dan to'g'ridan-to'g'ri, siqilgan va keshlangan holda.
5. **Xavfsizlik sarlavhalari.** HSTS (domen ma'lum bo'lgach `includeSubDomains` qarori), CSP — Caddyfile'da.

## Rasmiy hujjat va yaxshi manbalar
- https://caddyserver.com/docs/ — "Getting Started", `reverse_proxy` direktivasi.
- https://caddyserver.com/docs/automatic-https

## Kichik mashq
R0-15 tayyor bo'lgach: `deploy/Caddyfile` ni oching va har bir blok nimaga javob berishini (sayt, API, statik
fayllar) o'z so'zlaringiz bilan yozing. Hozircha: `backend/apps/accounts/net.py` dagi izohni o'qib,
nega `TRUSTED_PROXY_COUNT` prod'da 1 bo'lishi shartligini tushuntiring.
