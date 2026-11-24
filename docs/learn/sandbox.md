# Sandbox: talaba kodi serverda qanday xavfsiz tekshiriladi

> Kim uchun: loyiha egasi. Qaror: ADR-0007. O'qish vaqti: ~10 daqiqa.

## 1. Nega sandbox?

"Tekshirish" brauzerda ishlaydi — lekin u yerda talaba hamma narsani ko'radi va o'zgartira oladi. Rasmiy ball uchun
kod **serverda**, talaba ko'rmaydigan **yashirin testlar** bilan tekshirilishi kerak. Ammo talaba kodi — begona kod:
u fayllarni o'chirishga, tarmoqqa chiqishga yoki serverni "qotirib" qo'yishga urinishi mumkin. Shuning uchun u
**sandbox** — har safar yangi yaratilib, keyin o'chiriladigan, qattiq cheklangan konteynerda bajariladi.

## 2. Bitta topshirish yo'li

```text
Talaba "Topshirish" → Django: Submission (queued) → Redis navbati → Celery worker (2 ta parallel)
   → sandbox-launcher: yangi konteyner (tarmoqsiz, 512 MB, 60 s) → runner.py testlarni bajaradi → JSON natija
   → worker: ball saqlanadi (done) → WebSocket: talabaga natija
```

## 3. Konteyner cheklovlari va nima uchun

| Cheklov | Nimadan himoya |
| --- | --- |
| Tarmoq yo'q | Ma'lumot o'g'irlash, tashqi hujum, javob yuklab olish |
| Faqat o'qiladigan fayl tizimi | Image yoki tizimni buzish |
| Root'siz foydalanuvchi, `cap-drop ALL`, `no-new-privileges` | Konteynerdan chiqishga urinishlar |
| 512 MB xotira, 1 CPU | Serverning boshqa qismlarini bo'g'ib qo'yish |
| 60 soniya | Cheksiz sikl |
| Jarayonlar soni (64) | "Fork-bomba" |

## 4. Nega alohida "launcher"?

Docker'ni boshqarish huquqi = serverda root huquqi. Agar bu huquq Celery worker'da bo'lsa va worker buzilsa — butun
server xavf ostida. Shuning uchun Docker'ga faqat kichik `sandbox-launcher` xizmati kiradi va u tashqariga **bitta**
amal beradi: "shu kodni shu testlar bilan ishga tushir". Konteyner sozlamalari uning kodida qotirilgan — hech kim
"imtiyozli konteyner yarat" deb so'ray olmaydi.

## 5. Brauzer va server natijasi bir xil bo'lishi uchun

Sandbox image'dagi Python paketlari Pyodide'dagi bilan aynan bir xil versiyada (numpy 2.4.6, pandas 3.0.2,
scikit-learn 1.8.0 ...). Aks holda talaba "Tekshirish"da o'tib, "Topshirish"da yiqilishi mumkin edi.

## 6. Atamalar

| Atama | Ma'nosi |
| --- | --- |
| Konteyner | Alohida, cheklangan muhitda ishlaydigan dastur (Docker) |
| Image | Konteynerning "andozasi" — qaysi Python va paketlar bor |
| Navbat (queue) | Topshirishlar ketma-ket bajarilishi uchun ro'yxat |
| Celery worker | Navbatdan vazifa olib bajaradigan jarayon |
| Idempotent | Bir xil vazifa ikki marta kelsa ham natija bir marta yoziladi |
