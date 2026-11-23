# Kirish: sessiya cookie, CSRF va lockout

## Bu nima (2–3 gap, oddiy tilda)
Talaba Hemis ID va parol bilan kirganda server unga **sessiya cookie** beradi — keyingi so'rovlarda brauzer
uni o'zi yuboradi. **CSRF** himoyasi boshqa sayt talaba nomidan so'rov yubora olmasligini ta'minlaydi.
**Lockout** — 5 marta xato paroldan keyin 15 daqiqa blok (parolni taxmin qilishga qarshi).

## Nega aynan u tanlandi (va muqobillari)
- Sessiya cookie (`HttpOnly`, `SameSite=Lax`, prod'da `Secure`) — ARCHITECTURE qarori. Muqobil — JWT token
  brauzer xotirasida: XSS bo'lsa o'g'irlanadi va bekor qilish qiyin.
- Lockout hisoblagichi **Redis**da: har xato urinish bazaga yozilmaydi, muddat (TTL) tabiiy.
- Blok kaliti — **Hemis ID + IP** (egasining qarori): boshqa joydagi hujumchi talabaning o'z kompyuterini
  bloklay olmaydi; kompyuter xonasidagi boshqa talabalar ham bloklanmaydi.

## Bizning loyihada qayerda ishlatilgan
- `backend/apps/accounts/backends.py` — yagona login yo'li (API ham, `/admin/` ham shu yerdan o'tadi).
- `backend/apps/accounts/lockout.py` — 5 xato / 15 daqiqa.
- `backend/apps/accounts/views.py` — `/api/auth/csrf`, `login`, `logout`, `me`.
- `backend/apps/accounts/signals.py` — kirishlar audit jurnaliga.

## Asosiy tushunchalar
1. **CSRF oqimi.** Frontend avval `GET /api/auth/csrf` chaqiradi → `csrftoken` cookie; keyin har POST'da shu
   qiymat `X-CSRFToken` sarlavhasida. Boshqa sayt cookie qiymatini o'qiy olmaydi.
2. **Login CSRF.** Hujumchi talabani o'z akkauntiga kiritib qo'yishi mumkin — shuning uchun login ham CSRF talab qiladi.
3. **Bir xil javob.** "Bunday foydalanuvchi yo'q" va "parol noto'g'ri" bir xil: "Hemis ID yoki parol noto'g'ri."
4. **Sessiya kaliti yangilanadi** har kirishda (session fixation'ga qarshi).
5. **IP Caddy ortida** `X-Forwarded-For` dan olinadi, lekin faqat ishonchli proksi qo'shgan qismi
   (`TRUSTED_PROXY_COUNT`), aks holda hujumchi IP'ni soxtalashtirib blokdan qochadi.

## Parolni tiklash (R0-08)
Admin yoki o'qituvchi talabaning parolini tiklasa, tizim **bir martalik vaqtinchalik parol** ko'rsatadi —
u faqat o'sha javobda bir marta chiqadi, hech qayerda saqlanmaydi. Talaba shu parol bilan kiradi va
parolni almashtirmaguncha boshqa hech narsa ocha olmaydi (`must_change_password`, middleware). Kim kimning
parolini tiklay olishi bitta faylda: `backend/apps/accounts/policies.py`. Tiklash va almashtirish audit
jurnaliga yoziladi (parolsiz).

## Rasmiy hujjat va yaxshi manbalar
- Django: "Cross Site Request Forgery protection", "How to use sessions".
- OWASP: Authentication Cheat Sheet (account lockout bo'limi).

## Kichik mashq
Brauzer DevTools → Application → Cookies: kirgandan keyin `sessionid` ning `HttpOnly` va `SameSite` ustunlariga
qarang. So'ng 5 marta noto'g'ri parol kiriting va 6-urinishda to'g'ri parol ham rad etilishini ko'ring.
