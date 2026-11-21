# PRD — L1 · MLab

> Qisqa mahsulot tavsifi. To'liq va majburiy talablar: `docs/SRS.md` (SRS v2, tasdiqlangan 2026-11-22).
> Bu fayl va SRS bir-biriga zid bo'lsa, SRS ustun.

## Muammo

Machine Learning fanida talabalar nazariyani eshitadi, lekin amaliyotda kodni ko'chiradi yoki AI'dan
tushunmasdan oladi. O'qituvchi 30 talabaning har birini dars davomida kuzata olmaydi, individual
topshiriqlarni qo'lda tekshirish esa vaqt talab qiladi.

## Foydalanuvchilar

| Rol | Asosiy ehtiyoj |
| --- | --- |
| Talaba (3-kurs bakalavr) | O'rnatishsiz brauzerda kod yozish, darhol fikr olish, o'z darajasidagi topshiriq |
| O'qituvchi | Guruhni real vaqtda ko'rish, qiynalayotganga yordam, avtomatik baho va hisobot |
| Super admin | Kurs kontentini yuritish |
| Admin | O'qituvchi akkauntlari va limitlar |
| Mehmon | Sertifikat haqiqiyligini QR orqali tekshirish |

## Maqsadlar va o'lchovlar (R1 — MVP)

- Bir guruh (≈30 talaba) bilan to'liq semestr platformada o'tadi.
- Birinchi darsda talabalarning 90% yordamsiz kod ishga tushiradi (NFR-12).
- Laboratoriya monoblokda ≤ 2 daqiqada ochiladi (NFR-02); monitoring ≤ 5 soniya kechikadi (NFR-04).
- A1–A15 topshiriqlari to'liq avtomatik baholanadi; o'qituvchi faqat tavsiya ballni tasdiqlaydi.
- 100 ta bir vaqtdagi faol talaba 4 GB RAM'li serverda (NFR-05, NFR-18).

## Asosiy funksiyalar (MVP)

1. Ro'yxatdan o'tish (Hemis ID login), rozilik, kirish, parolni tiklash (parolni hech kim ko'rmaydi).
2. Guruhlar: QR va havola orqali qo'shilish, o'qituvchi tasdig'i, avtomatik kursga yozilish.
3. Kirish oynalari: guruh × mavzu laboratoriyasi uchun qo'lda, jadval va takroriy slotlar.
4. Guruh sozlamalari: AI tutor chegarasi, mashq rejimi, kechikish muddati, chat.
5. Kontent: 22 ma'ruza qadamlarga bo'lingan, testlar (Aiken importi).
6. Brauzer laboratoriyasi: notebook, Pyodide, datasetlar, avtosaqlash.
7. Avtobaholash: ko'rinadigan testlar brauzerda, yashirinlari sandbox'da; A1–A15, 3 daraja × 5 variant.
8. Moslashuvchan daraja tanlash va challenge.
9. Jonli monitoring paneli, yordam navbati, guruh chati.
10. Ustoz-AI: rejimlar, cheklovlar, limitlar, shaxsiy ma'lumotsiz.
11. Akademik halollik: paste cheklovi, tushunish savollari, nazorat rejimi.
12. Baholash jurnali (100 ball), tavsiya ball, sertifikat (90+) va QR tekshiruvi, Excel/PDF hisobotlar.

## MVP'ga kirmaydiganlar

Jamoaviy estafeta (R2), to'liq mastery (R2), code playback (R2), mavzu chatlari (R2), RAG (R2),
vizual neyron to'r konstruktori (R2), Google kirish va email (R3), rus tili (R3), kontent muharriri (R3),
TensorFlow.js CNN/RNN (R4), pullik AI va to'lov (R4), Hemis integratsiyasi (yo'q).

## Cheklovlar

- Server: universitet, Ubuntu, 4 GB RAM, CPU, GPU yo'q.
- AI: Gemini bepul tarifi (limitlar; matnlar Google tomonidan ishlatilishi mumkin — shuning uchun shaxsiy ma'lumot yuborilmaydi).
- Ishlab chiqish: Claude Pro, tungi runlar; egasining kunlik ko'rigi 10–20 daqiqa.
- Til: o'zbek (lotin). Vaqt zonasi: Asia/Tashkent.

## Ochiq savollar

`docs/SRS.md` 12-bo'lim: monobloklar parametrlari, domen va HTTPS, yurist bilan kelishuv, logotipga ruxsat.
