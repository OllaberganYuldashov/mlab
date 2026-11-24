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

## 6. Image va runner amalda (I3-05)

- `sandbox/Dockerfile`: Python 3.14.10 (digest bilan qotirilgan), paketlar `sandbox/requirements.txt` dan —
  versiya **va hash** bilan (`pip install --require-hashes --only-binary`), pip o'chirilgan, foydalanuvchi UID 10003.
  Datasetlar image ichida, `mlab.load("iris")` brauzerdagidek ishlaydi.
- `sandbox/runner.py`: stdin'dan JSON (kod, testlar, parametrlar), stdout'ga JSON (har test: o'tdi/o'tmadi, vaqt).
  Talaba `print()` lari alohida buferga ketadi — natijani soxtalashtira olmaydi. Yashirin test nomi
  "yashirin test N", xabar faqat "O'tmadi" — test kodi va assert matni chiqmaydi (AGR-05).
- Har kod va test uchun vaqt chegarasi (`signal.alarm`); talabaning `except Exception` bloki uni yuta olmaydi.
- Hujum testlari (`sandbox/tests/test_image_attacks.py`) haqiqiy Docker'da: tarmoq yo'q, fayl yozib bo'lmaydi,
  `/tmp` dan dastur ishga tushmaydi, fork-bomba 64 jarayonda to'xtaydi, xotira 512 MB, cheksiz sikl to'xtatiladi.
- Ma'lum cheklov: talaba kodi runner bilan bitta jarayonda. Juda ataylab yozilgan "hiyla" kod natijani buzishga
  urinishi mumkin (xostga zarar yetkaza olmaydi). Himoya: kod saqlanadi, o'qituvchi ko'radi; I3-19 ko'rigida
  qayta baholanadi.

O'zingiz sinash (Docker Desktop, repo ildizida):

```powershell
docker build -f sandbox/Dockerfile -t mlab-sandbox:dev .
echo '{"code": "x = 2 + 2", "tests": []}' | docker run --rm -i --network none mlab-sandbox:dev
```

## 7. Brauzerdagi "Tekshirish" (I3-04)

"Tekshirish" tugmasi serverga hech narsa yubormaydi: ko'rinadigan testlar talabaning o'z brauzerida, Pyodide'da ishlaydi
(`frontend/src/lab/checker.ts`). Runner `sandbox/runner.py` ning nusxasi — bir xil qoidalar:

- talaba kodi (notebook'ning kod kataklari tartib bilan) **yangi** nomlar fazosida bajariladi — notebook'da qo'lda
  yaratilgan, lekin kodda yo'q o'zgaruvchi testga "sirg'alib" o'tmaydi;
- har `test_*(ns, params)` alohida; `assert` matni talabaga ko'rinadi (bu ko'rinadigan test);
- vaqt chegarasi (30 s) JS tomonda: oshsa worker o'ldiriladi va yangisi ochiladi (cheksiz sikl sahifani qotirmaydi).
  Paketlarni yuklash vaqti chegaraga kirmaydi — avval talaba kodi importlari bo'yicha paketlar yuklanadi;
- talaba kodi va testlar Python dasturiga **JSON satr literali** sifatida qo'yiladi: kod ichidagi `"""` yoki
  `\\` dastur tuzilishini buza olmaydi.

Nega bu xavfsiz? Brauzerdagi natija baho emas: talaba uni xohlagancha "soxtalashtira" oladi — bu faqat o'ziga ta'sir
qiladi. Baho faqat serverda, yashirin testlar bilan (AGR-05) — yashirin testlar `GET .../assignment` javobiga umuman
kirmaydi (testda tekshirilgan).

## 8. Atamalar

| Atama | Ma'nosi |
| --- | --- |
| Konteyner | Alohida, cheklangan muhitda ishlaydigan dastur (Docker) |
| Image | Konteynerning "andozasi" — qaysi Python va paketlar bor |
| Navbat (queue) | Topshirishlar ketma-ket bajarilishi uchun ro'yxat |
| Celery worker | Navbatdan vazifa olib bajaradigan jarayon |
| Idempotent | Bir xil vazifa ikki marta kelsa ham natija bir marta yoziladi |
