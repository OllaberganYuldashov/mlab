# Server: birinchi deploy, zaxira va tiklash

> Bu yo'riqnoma server tayyor bo'lganda ishlatiladi (R0-16). Hozircha serversiz tayyorlangan; haqiqiy sinov server kelgach.

## Bu nima (2–3 gap, oddiy tilda)
Platforma bitta serverda Docker konteynerlarida ishlaydi: `caddy` (eshik, HTTPS), `web` (Django), `db` (PostgreSQL), `redis`.
Yangi versiya "deploy" qilinganda server tanlangan `good-*` tegdagi kodni oladi, konteynerlarni yangilaydi va
tekshiradi (smoke test). Har kuni bazaning zaxirasi olinadi.

## Nega aynan shunday (va muqobillari)
ADR-0004: konteynerlar (bir xil muhit), deploy mantig'i `deploy/deploy.sh` da (workflow faqat chaqiradi), shuning uchun
SSH yoki self-hosted runner usuli tanlansa ham mantiq o'zgarmaydi. Muqobil — qo'lda `git pull` (takrorlanmaydi).

## Bizning loyihada qayerda
- `deploy/compose.prod.yaml`, `deploy/Caddyfile`, `backend/Dockerfile`, `frontend/Dockerfile` (R0-15)
- `deploy/deploy.sh <teg>`, `deploy/smoke.sh`, `deploy/backup.sh`, `.github/workflows/deploy.yml` (R0-16)

## Birinchi deploy (egasi uchun, taxminan 1–2 soat)
1. **Serverga Docker o'rnating** (Docker Engine + Compose plagini) va foydalanuvchini `docker` guruhiga qo'shing.
2. **Repo nusxasi:** `sudo mkdir -p /opt/mlab && sudo chown $USER /opt/mlab && git clone <repo-url> /opt/mlab/app`.
3. **Sozlamalar fayli** `/opt/mlab/.env` (secret'lar faqat shu yerda; repoga hech qachon):
   ```text
   SECRET_KEY=<uzun tasodifiy qator: python3 -c "import secrets;print(secrets.token_urlsafe(50))">
   ALLOWED_HOSTS=mlab.sizning-domen.uz
   CSRF_TRUSTED_ORIGINS=https://mlab.sizning-domen.uz
   SITE_ADDRESS=mlab.sizning-domen.uz
   POSTGRES_PASSWORD=<kamida 24 belgi tasodifiy>
   TRUSTED_PROXY_COUNT=1
   ```
   Keyin `chmod 600 /opt/mlab/.env`. (Domen tayyor bo'lmasa sinov uchun `SITE_ADDRESS=:80` va `SECURE_SSL_REDIRECT=false`.)
4. **Domen:** DNS'da `A` yozuvi serverning IP'siga; 80 va 443 portlar tashqaridan ochiq (Caddy sertifikatni o'zi oladi).
5. **Deploy:** repo ildizida `deploy/deploy.sh good-<oxirgi teg>` (teglar GitHub'dagi "Tags" bo'limida). Skript: tegni oladi,
   konteynerlarni yig'adi va ishga tushiradi, migratsiya qiladi, smoke test o'tkazadi.
6. **Birinchi super admin:** `docker compose -f deploy/compose.prod.yaml --env-file /opt/mlab/.env run --rm migrate python manage.py createsuperuser`
   (Hemis ID — 12 raqam; parolni parol menejeriga saqlang).
7. Brauzerda `https://<domen>/` va `https://<domen>/healthz` ni tekshiring.

## Keyingi deploy'lar
- **Workflow orqali:** GitHub → Actions → "deploy" → Run workflow → teg. (Serverda self-hosted runner kerak: yorlig'i
  `mlab-prod`; GitHub'da "production" environment'iga o'zingizni tasdiqlovchi qilib qo'ying.)
- **Qo'lda:** serverda `deploy/deploy.sh <teg>`. **Orqaga qaytish** ham shu: oldingi `good-*` tegni bering.
- Skript har deploy'dan oldin bazaning zaxirasini oladi; smoke test yiqilsa deploy "qizil" hisoblanadi va oldingi tegni ko'rsatadi.

## Zaxira (ADM-04; RPO ≤ 24 soat)
- `deploy/backup.sh backup` — `/opt/mlab/backups/db-<sana>.dump`, 14 kundan eskilari o'chadi (`MLAB_BACKUP_KEEP_DAYS`).
- **Kunlik avtomatik:** serverda `crontab -e` ga: `30 2 * * * /opt/mlab/app/deploy/backup.sh backup >> /opt/mlab/backup.log 2>&1`
  (02:30, server vaqti Asia/Tashkent bo'lsin: `timedatectl set-timezone Asia/Tashkent`).
- **Muhim:** zaxira shu serverning o'zida turadi — server disk'i buzilsa u ham yo'qoladi. Haftada bir zaxirani boshqa joyga
  (universitetning boshqa kompyuteri yoki tashqi disk) nusxalang: `scp` yoki `rsync`. Bu ochiq qaror: qayerga (SRS 12).

## Tiklash (RTO ≤ 4 soat)
1. Zaxirani tanlang: `deploy/backup.sh list`.
2. `deploy/backup.sh restore /opt/mlab/backups/db-<sana>.dump --yes` — joriy holatning zaxirasi olinadi, `web` va `caddy`
   to'xtatiladi, baza tiklanadi, servislar qayta ishga tushadi va smoke test o'tadi.
3. Butunlay yangi serverda: 1–5 qadamlar (Docker, repo, `.env`), keyin `deploy.sh`, so'ng 2-qadam.
4. **Oyda bir marta tiklash sinovi** (ADM-04): zaxirani **alohida sinov muhitida** tiklab, `/readyz` va bir nechta jadvalni tekshiring.
   Sinovsiz zaxira — zaxira emas.

## Asosiy tushunchalar
1. **Idempotent deploy:** bir xil tegni ikki marta deploy qilish zarar qilmaydi.
2. **Smoke test:** deploy'dan keyin foydalanuvchi yo'li (Caddy → web → DB/Redis) ishlayotganini tekshiradi.
3. **Faqat `good-*` teglar:** CI yashil bo'lgan commit'lar; "main" deploy qilinmaydi.
4. **Volume'lar:** `down` buyrug'iga volume bayrog'i qo'shilsa baza yo'qoladi — hech qachon qo'shmang.

## Rasmiy hujjat va yaxshi manbalar
- https://docs.docker.com/compose/ — `up`, `ps`, healthcheck
- https://www.postgresql.org/docs/16/app-pgdump.html va `pg_restore`
- https://docs.github.com/actions/hosting-your-own-runners

## Kichik mashq
`deploy/backup.sh` ni o'qing: nega zaxira avval `.part` fayliga yoziladi va keyin `mv` qilinadi? (Javob: `backend/tests/test_adm_04_backup_deploy_scripts.py`
dagi `test_adm_04_failed_dump_leaves_no_file`.)
