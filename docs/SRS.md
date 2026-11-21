# L1 · MLab — Talablar spetsifikatsiyasi (SRS) v2

Versiya: v2 · Tasdiqlangan: 2026-11-22 · Asl nusxa: Claude Docs (https://claude.ai/artifact/Hc2ZCzaWKtRwkd1CJzBXTK)

MLab — Machine Learning fanini bakalavr talabalariga amaliyot, o'yin va individual yondashuv orqali o'qitadigan yopiq (private) web platforma. Hujjat ISO/IEC/IEEE 29148 tuzilmasiga tayanadi; talablar ID, MoSCoW ustuvorligi (Must, Should, Could, Won't) va reliz bilan belgilangan. Ish iterativ olib boriladi: avval MVP, keyingi relizlarda takomillashtiriladi. Bu versiya v1 TZ o'rnini bosadi.

## 1. Kirish

### 1.1. Maqsad

Ushbu hujjat MLab platformasiga qo'yiladigan funksional va nofunksional talablarni, MVP doirasini va keyingi relizlar rejasini belgilaydi. U ishlab chiqish, sinov va qabul qilish uchun yagona asos hisoblanadi.

### 1.2. Mahsulot doirasi

MLab — bitta fan (Machine Learning) uchun yopiq ta'lim platformasi. Talaba faqat o'qituvchi guruhiga a'zo bo'lish orqali kursga kiradi.

- **Doiraga kiradi:** ma'ruzalar, testlar, brauzerdagi laboratoriya, avtomatik baholanadigan topshiriqlar, moslashuvchan variantlar, jamoaviy topshiriqlar, real vaqt monitoringi, AI tutor, akademik halollik mexanizmlari, baholash jurnali, sertifikat, hisobotlar.
- **Doiraga kirmaydi:** Hemis bilan integratsiya, to'lov tizimi, bir nechta fan va OTM (R4 gacha), mobil ilova, GPU talab qiladigan chuqur o'rganish (R4 gacha).

### 1.3. Atamalar lug'ati

| Atama | Ma'nosi |
| --- | --- |
| Kurs (Course) | Platformadagi yagona fan: modullar, mavzular, topshiriqlar va testlar to'plami. Super admin yuritadi |
| Mavzu (Topic) | Kursning bir bo'limi: ma'ruza, laboratoriya mashg'uloti va mustaqil topshiriq |
| Ma'ruza (Lecture) | Qadamlarga bo'lingan nazariy material; doim ochiq |
| Laboratoriya mashg'uloti (Lab session) | Amaliy mashg'ulot: brauzerda kod yoziladi, topshiriqlar avtomatik baholanadi |
| Topshiriq (Assignment) | Baholanadigan ish: umumiy, individual variant, challenge, jamoaviy yoki mustaqil |
| Guruh (Section) | O'qituvchi yaratgan talabalar guruhi. Kursga kirish faqat guruh orqali |
| A'zolik so'rovi (Membership request) | Talabaning guruhga qo'shilish so'rovi; o'qituvchi tasdiqlaydi yoki rad etadi |
| Qo'shilish havolasi (Join link) va QR | Guruhga a'zolik so'rovini yuborish uchun noyob havola va uning QR kodi |
| Kirish oynasi (Access window) | Guruhning ma'lum mavzu laboratoriyasiga kira oladigan vaqt oralig'i |
| Guruh sozlamalari (Section settings) | O'qituvchi boshqaradigan guruh darajasidagi parametrlar (kirish oynalari, AI tutor, a'zolik) |
| Baholash jurnali (Gradebook) | Talabalarning barcha natijalari va 100 ballik yakuniy natija |
| Avtobaholovchi (Autograder) | Topshiriqni testlar bilan avtomatik tekshiruvchi xizmat |
| Ko'rinadigan va yashirin testlar | Ko'rinadiganlari brauzerda darhol ishlaydi; yashirinlari faqat serverda, rasmiy ball uchun |
| Sandbox | Kodni tarmoqsiz va cheklangan resurslar bilan bajaradigan izolyatsiyalangan konteyner |
| Mastery darajasi | Talabaning ko'nikma bo'yicha darajasi: Boshlanmagan, Urinilgan, Tanish, Bilimli, Mohir |
| AI tutor (Ustoz-AI) | Kurs mavzulari doirasida yo'naltiruvchi yordam beruvchi AI yordamchi |
| Akademik halollik (Academic integrity) | Ko'chirish va AI'dan tushunmasdan foydalanishga qarshi mexanizmlar |
| MVP | Minimal hayotiy mahsulot: haqiqiy darsda foydalanish mumkin bo'lgan birinchi reliz |
| Reliz (Release), iteratsiya (Iteration) | Reliz — foydalanuvchiga chiqadigan versiya; iteratsiya — 2 haftalik ish sikli |

### 1.4. Manbalar

- MAL2506 Machine Learning fan dasturi (UrDU, 2026) — faqat ma'ruza va amaliy mavzular ro'yxati uchun.
- Dunyo tajribasi tadqiqoti: Harvard CS50 Duck (AI tutor), Otter-Grader (avtobaholash), Codio va zyBooks (akademik halollik), Codeopticon va CodeHS (real vaqt monitoringi), Khan Academy (mastery), Pyodide va JupyterLite (brauzer laboratoriyasi), TensorFlow Playground (vizual neyron to'r), Stepik va W3Schools (qadamli darslar).
- O'zbekiston Respublikasining "Shaxsga doir ma'lumotlar to'g'risida"gi qonuni (2026-yil martdagi o'zgartirishlar bilan).
- Gemini API foydalanish shartlari.

## 2. Umumiy tavsif

### 2.1. Mahsulot konteksti

Platforma yopiq: ro'yxatdan o'tgan va guruhga tasdiqlangan talabagina kursni ko'radi. Kurs bitta va hamma guruhlar uchun umumiy; o'qituvchi kursni emas, o'z guruhlarining sozlamalarini boshqaradi. Kontentni super admin yuritadi va o'zgarishlar hamma guruhlarda darhol amal qiladi.

### 2.2. Foydalanuvchi sinflari

| Rol | Vazifasi | Asosiy huquqlar | Cheklovlar |
| --- | --- | --- | --- |
| Super admin | Kurs egasi | Kurs kontenti (mavzular, ma'ruzalar, topshiriqlar, testlar, datasetlar) va baholash qoidalari; adminlarni boshqarish; audit jurnali | Talaba ishlarini tahrirlamaydi |
| Admin | Tizim ma'muri | O'qituvchi akkauntlari va ularning talaba limiti; yo'nalishlar ro'yxati; parolni tiklash | Parollarni ko'rmaydi |
| O'qituvchi (Instructor) | Guruhlarni olib boradi | Guruh yaratish; qo'shilish havolasi va QR; a'zolikni tasdiqlash; guruh sozlamalari va kirish oynalari; monitoring; baholash jurnali; hisobotlar; o'z guruhi talabasining parolini tiklash | Faqat o'z guruhlari |
| Talaba (Student) | O'quvchi | Guruhga qo'shilish; ma'ruzalar, laboratoriya, topshiriqlar, testlar; chat; o'z natijalari va sertifikati; o'z ma'lumotlari | Faqat o'z ishlari |
| Mehmon (Guest) | Tashqi foydalanuvchi | Faqat sertifikatni QR orqali tekshirish sahifasi | Boshqa hech narsa |

### 2.3. Ish muhiti

| Qism | Talab |
| --- | --- |
| Server | Universitet serveri: Ubuntu Linux, CPU, 4 GB RAM, GPU'siz, O'zbekiston hududida |
| Mijoz qurilmalari | Talabalar noutbuklari va universitet kompyuter xonasidagi monobloklar |
| Brauzerlar | Chrome, Edge, Firefox — oxirgi 2 ta asosiy versiya; WebAssembly qo'llab-quvvatlanishi shart |
| Tarmoq | Universitet ichki tarmog'i va internet; vaqtinchalik uzilishga chidamli |
| Til | O'zbek (lotin); rus tili R3 da |
| Vaqt zonasi | Asia/Tashkent |

### 2.4. Cheklovlar

- Server resurslari: 4 GB RAM, GPU yo'q.
- AI: Gemini API bepul tarifi (so'rov limitlari; bepul tarifda yuborilgan matnlar Google xizmatlarini yaxshilash uchun ishlatilishi mumkin).
- Ishlab chiqish: Claude Pro tarifida tungi iteratsiyalar.
- Shaxsiy ma'lumotlar O'zbekiston qonunchiligiga muvofiq.

### 2.5. Taxminlar va bog'liqliklar

- Bir vaqtda faol talabalar soni MVP uchun 100 tagacha; bir semestrda 100–250 ta.
- Talabalar 18 yoshdan katta (3-kurs).
- Universitet serveriga domen va HTTPS sertifikati beriladi.
- Kompyuter xonasidagi monobloklar zamonaviy brauzerni ishga tushira oladi (R1 boshida tekshiriladi).

## 3. Domen modeli

Kurs bitta, guruhlar ko'p. Talaba guruhga a'zo bo'lganda avtomatik ravishda kursga ham yoziladi; laboratoriyaga kirish guruhning kirish oynalari bilan boshqariladi.

| Obyekt | Asosiy maydonlar | Bog'lanish |
| --- | --- | --- |
| Course | nomi, o'quv yili, baholash vaznlari | Bitta; Topic'lar unga tegishli |
| Topic | tartib raqami, nomi, turi (ma'ruza/laboratoriya/mustaqil) | Course → ko'p Topic |
| Lecture, LectureStep | qadam turi, matn, kod, savol | Topic → Lecture → qadamlar |
| Assignment | turi (umumiy, individual, challenge, jamoaviy, mustaqil), daraja, variantlar, AI rejimi (default) | Topic → ko'p Assignment |
| AssignmentVariant | parametrlar, dataset qismi, ko'rinadigan va yashirin testlar, tushunish savollari | Assignment → ko'p variant |
| Quiz, Question | savol, variantlar, to'g'ri javob, mavzu | Topic → Quiz |
| Dataset | nomi, fayl, manba, litsenziya | Assignment'larda ishlatiladi |
| User | FIO, Hemis ID (login), rol, parol xeshi | — |
| Section (guruh) | nomi, yo'nalish, o'qituvchi, sig'im, qo'shilish tokeni, sozlamalar | O'qituvchi → ko'p Section |
| Membership | talaba, guruh, holati (so'rov, tasdiqlangan, rad etilgan, chiqarilgan), sanalar | Talaba faqat bitta faol guruhda |
| AccessWindow | guruh, mavzu, rejim (yopiq, ochiq, jadval), ochilish va yopilish vaqti, kechikish muddati, nazorat rejimi | Section × Topic |
| SectionSettings | AI tutor holati va maksimal rejimi, yopilgandan keyingi mashq rejimi, qo'shilish yoqilgan | Section → bitta |
| Submission | talaba, variant, kod, ko'rinadigan va yashirin test natijasi, ball, vaqt, kechikkan belgisi | Talaba × Assignment |
| ComprehensionAnswer | savol, javob, to'g'ri yoki noto'g'ri | Submission → ko'p |
| SkillMastery | talaba, ko'nikma, daraja, ballar | Talaba × ko'nikma |
| Team, TeamStage | jamoa a'zolari, bosqich, ijrochi, holat | Section → Team (R2) |
| ActivityEvent | turi, vaqti, sessiya, qurilma, IP | Talaba → ko'p |
| ChatMessage | kanal (guruh yoki mavzu), muallif, matn | Section → ko'p |
| AiInteraction | savol, javob, rejim, tokenlar | Talaba → ko'p |
| GradeRecord | komponentlar, tavsiya ball, tasdiqlangan ball | Talaba × Course |
| Certificate | raqam, talaba, ball, sana, holati (faol, bekor qilingan) | Talaba → bitta |
| AuditLog | kim, nima, qachon, oldingi va yangi qiymat | Hamma muhim harakatlar |

Sozlamalar ikki darajada: kurs darajasi (super admin, default qiymatlar) va guruh darajasi (o'qituvchi). Guruh sozlamasi bo'lmasa, kurs qiymati amal qiladi.

&#32;Bu tuzilma R3 da o'qituvchiga ko'proq sozlash berishga qayta yozishsiz imkon qoldiradi.

## 4. Funksional talablar

Har talab ID, MoSCoW ustuvorligi va reliz bilan berilgan. R1 = MVP. "Must" talablarsiz MVP qabul qilinmaydi.

### 4.1. Autentifikatsiya va akkauntlar (AUTH)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| AUTH-01 | Talaba ro'yxatdan o'tadi: FIO, Hemis ID (login, noyob), yo'nalish (ro'yxatdan tanlanadi), parol. Rozilik belgisi majburiy | Must | R1 |
| AUTH-02 | Kirish Hemis ID va parol bilan; 5 ta muvaffaqiyatsiz urinishdan keyin 15 daqiqa blok | Must | R1 |
| AUTH-03 | Parollar Argon2 bilan xeshlanadi va hech kimga ko'rinmaydi | Must | R1 |
| AUTH-04 | O'qituvchi yoki admin parolni tiklaydi: tizim bir martalik vaqtinchalik parol beradi, talaba birinchi kirishda yangisini o'rnatadi | Must | R1 |
| AUTH-05 | Admin o'qituvchi akkauntini yaratadi va talaba limitini belgilaydi | Must | R1 |
| AUTH-06 | Faol sessiyalar ro'yxati, boshqa qurilmalardan chiqish | Should | R2 |
| AUTH-07 | Google akkaunti orqali kirish | Could | R3 |
| AUTH-08 | Email orqali parolni tiklash | Could | R3 |

### 4.2. Guruhlar va a'zolik (SEC)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| SEC-01 | O'qituvchi guruh yaratadi: nomi, yo'nalish, sig'im (default 30) | Must | R1 |
| SEC-02 | Har guruh uchun noyob qo'shilish havolasi va QR. O'qituvchi uni yangilaydi (eskisi bekor bo'ladi) yoki o'chirib qo'yadi | Must | R1 |
| SEC-03 | Talaba havola yoki QR orqali kiradi (kerak bo'lsa ro'yxatdan o'tadi) va a'zolik so'rovini yuboradi; guruh nomi va o'qituvchi ko'rinadi | Must | R1 |
| SEC-04 | O'qituvchi so'rovlarni bittalab yoki ommaviy tasdiqlaydi yoki rad etadi; talaba holatni ko'radi | Must | R1 |
| SEC-05 | Tasdiqlangan talaba kursga avtomatik yoziladi; kursga alohida obuna yo'q | Must | R1 |
| SEC-06 | Sig'im to'lganda yangi so'rov qabul qilinmaydi va xabar chiqadi | Must | R1 |
| SEC-07 | Talaba bir vaqtda bitta faol guruhda. O'qituvchi talabani boshqa guruhiga o'tkazadi yoki chiqaradi; natijalar saqlanadi | Should | R1 |
| SEC-08 | Admin o'qituvchi bo'yicha umumiy talaba limitini belgilaydi | Should | R1 |

### 4.3. Kirish oynalari (ACC)

O'qituvchi darsni emas, guruhning mavzular laboratoriyasiga kirish vaqtini boshqaradi.

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| ACC-01 | Ma'ruzalar, mashq testlari va mustaqil topshiriqlar a'zo talabaga doim ochiq | Must | R1 |
| ACC-02 | Laboratoriya mashg'uloti default yopiq; guruh × mavzu uchun kirish oynasi belgilanadi | Must | R1 |
| ACC-03 | Oyna rejimlari: Yopiq; Hozir ochish (qo'lda yopish yoki N daqiqadan keyin avtomatik); Jadval (ochilish va yopilish sanasi va vaqti) | Must | R1 |
| ACC-04 | Takroriy jadval yordamchisi: haftalik slot (masalan, seshanba 10:00, 80 daqiqa) va boshlanish sanasi kiritilsa, mavzular tartib bilan keyingi slotlarga joylashadi; har birini surish mumkin | Should | R1 |
| ACC-05 | Talaba keyingi ochiladigan mavzu va qolgan vaqtni ko'radi; oyna ochilganda real vaqtda xabar keladi | Must | R1 |
| ACC-06 | Oyna yopilganda tugallanmagan ish avtomatik saqlanadi va rasmiy topshirish yopiladi | Must | R1 |
| ACC-07 | Kechikish muddati: yopilgandan keyin belgilangan soat davomida topshirish mumkin, ish "kechikkan" deb belgilanadi; jarima foizi kurs darajasida (default 0) | Should | R1 |
| ACC-08 | Yopilgandan keyingi mashq rejimi: laboratoriya baholarsiz mashq uchun ochiq qoladi (guruh sozlamasi) | Should | R1 |
| ACC-09 | Nazorat rejimi (oyna uchun): AI tutor o'chadi, paste taqiqlanadi, tab almashtirish qayd qilinadi | Should | R1 |
| ACC-10 | Mustaqil topshiriqlar uchun guruh bo'yicha topshirish muddati (deadline) | Must | R1 |
| ACC-11 | Barcha oyna o'zgarishlari audit jurnaliga yoziladi | Must | R1 |
| ACC-12 | O'qituvchining barcha guruhlari oynalari uchun kalendar ko'rinishi | Could | R2 |

### 4.4. Guruh sozlamalari (SET)

O'qituvchi kursni emas, guruh sozlamalarini boshqaradi. Guruhda qiymat berilmasa, kurs qiymati amal qiladi.

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| SET-01 | AI tutor: guruh uchun yoqish yoki o'chirish va maksimal rejim. Topshiriq rejimi guruh chegarasidan yuqori bo'lsa, chegara amal qiladi | Must | R1 |
| SET-02 | AI tutorni bir tugma bilan darhol o'chirish va qayta yoqish | Must | R1 |
| SET-03 | Qo'shilishni yoqish yoki o'chirish, sig'im | Must | R1 |
| SET-04 | Yopilgandan keyingi mashq rejimi va kechikish muddati | Should | R1 |
| SET-05 | Guruh chatini yoqish yoki o'chirish | Should | R1 |
| SET-06 | Kursni o'qituvchi darajasida xususiylashtirish (mavzu va variant tanlash, baho vaznlari) | Could | R3 |

### 4.5. Kontent (CNT)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| CNT-01 | Kurs kontenti versiyalanadigan matn fayllarida (Markdown va YAML) saqlanadi va import buyrug'i bilan yuklanadi | Must | R1 |
| CNT-02 | Ma'ruza 5–10 qadamga bo'linadi: matn va rasm; "O'zing sinab ko'r" kod bloki; tezkor savol | Must | R1 |
| CNT-03 | Interaktiv vizual qadam (slayder bilan parametr o'zgartirish) | Should | R1 |
| CNT-04 | 22 ta ma'ruza mavzusi sodda va minimal kontent bilan | Must | R1 |
| CNT-05 | Aiken formatidagi testlarni import qilish | Must | R1 |
| CNT-06 | Mavzu testi: savollar banki, tasodifiy tanlash, vaqt, urinishlar soni (kurs darajasida) | Must | R1 |
| CNT-07 | Super admin Django Admin orqali kontentni ko'radi va kichik tuzatish kiritadi | Should | R1 |
| CNT-08 | Interaktiv topshiriqlar: tartiblash, moslashtirish, "xatoni top" | Should | R2 |
| CNT-09 | Vizual kontent muharriri | Could | R3 |

### 4.6. Laboratoriya (LAB)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| LAB-01 | Notebook interfeysi: kod va matn kataklari, ishga tushirish (tugma, Shift+Enter), chiqish va grafiklar | Must | R1 |
| LAB-02 | Python brauzerda (Pyodide, Web Worker): numpy, pandas, matplotlib, seaborn, scikit-learn | Must | R1 |
| LAB-03 | Pyodide va paketlar platforma serveridan beriladi, keyingi yuklashlar keshdan | Must | R1 |
| LAB-04 | `mlab.load("nomi")` bilan dataset yuklash | Must | R1 |
| LAB-05 | Ish avtomatik saqlanadi (har 10 soniyada va har ishga tushirishda); tarmoq uzilsa lokal saqlanadi va tiklanganda yuboriladi | Must | R1 |
| LAB-06 | "To'xtatish" tugmasi: uzoq bajarilishni to'xtatib, muhitni qayta ishga tushiradi | Must | R1 |
| LAB-07 | Chap panelda topshiriq sharti va qadamlar, o'ng panelda AI tutor | Must | R1 |
| LAB-08 | Brauzerda ishlaydigan Streamlit (stlite) — A15 uchun | Should | R1 |
| LAB-09 | Vizual neyron to'r konstruktori va unga mos avtomatik kod | Should | R2 |
| LAB-10 | TensorFlow.js asosidagi CNN va RNN laboratoriyalari | Could | R4 |

### 4.7. Topshiriqlar va avtobaholash (AGR)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| AGR-01 | "Tekshirish": ko'rinadigan testlar brauzerda, natija darhol | Must | R1 |
| AGR-02 | "Topshirish": kod serverga yuboriladi, yashirin testlar sandbox'da, rasmiy ball qaytadi | Must | R1 |
| AGR-03 | Sandbox: tarmoqsiz, faqat o'qiladigan fayl tizimi, root'siz, 512 MB, 1 CPU, 60 soniya, jarayonlar soni cheklangan | Must | R1 |
| AGR-04 | Navbat: bir vaqtda 2 ta konteyner; navbatdagi holat talabaga real vaqtda ko'rinadi | Must | R1 |
| AGR-05 | Natija: qadamlar bo'yicha ball, o'tgan va o'tmagan testlar, tushunarli xabar; yashirin test tarkibi oshkor qilinmaydi | Must | R1 |
| AGR-06 | Har urinish saqlanadi; eng yuqori ball hisobga olinadi | Must | R1 |
| AGR-07 | A1–A15 har biri uchun: umumiy topshiriq, 3 daraja × kamida 5 variant, 1 challenge, 1 mustaqil topshiriq | Must | R1 |
| AGR-08 | Variant parametrlari va dataset qismi talabaga deterministik tarzda (talaba ID asosida) beriladi | Must | R1 |
| AGR-09 | Oldindan isitilgan konteynerlar puli (tezroq tekshiruv) | Could | R2 |

### 4.8. Moslashuvchan o'qitish (ADP)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| ADP-01 | Individual variant darajasi (asosiy, o'rta, ilg'or) qoida asosida tanlanadi: mavzu testi va oldingi topshiriqlar natijasi bo'yicha | Must | R1 |
| ADP-02 | O'qituvchi darajani qo'lda o'zgartira oladi | Must | R1 |
| ADP-03 | Tez tugatgan talabaga challenge taklif qilinadi | Should | R1 |
| ADP-04 | To'liq mastery tizimi: 5 daraja, ko'nikmalar xaritasi, talabaga ko'rinadigan progress | Should | R2 |
| ADP-05 | Takrorlash (spaced repetition) savollari | Could | R3 |

### 4.9. Jamoaviy topshiriqlar — ML Pipeline Relay (TEAM)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| TEAM-01 | Jamoalar avtomatik tuziladi (har safar yangi yoki doimiy), har jamoada darajalar aralash | Should | R2 |
| TEAM-02 | Jamoa bitta datasetda 5 bosqichni o'tadi: tozalash, EDA, belgilar, model, baholash; bosqichlar a'zolarga daraja bo'yicha taqsimlanadi | Should | R2 |
| TEAM-03 | Bosqich avtomatik tekshiruvdan o'tgach keyingisi ochiladi (estafeta) | Should | R2 |
| TEAM-04 | Har talaba ko'radi: qaysi bosqich kimda, navbat kimda, jamoa progressi va guruhlar reytingi | Should | R2 |
| TEAM-05 | Yakuniy reyting test to'plamidagi metrika bo'yicha (Kaggle uslubi) | Should | R2 |
| TEAM-06 | Ball bosqichni amalda bajargan a'zoga yoziladi | Should | R2 |

### 4.10. Real vaqt monitoringi (MON)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| MON-01 | Jonli panel (Live Monitoring Dashboard): guruhning har talabasi plitka; holat ranglari — kulrang (faol emas), ko'k (ishlayapti), sariq (5 daqiqadan ortiq bir joyda yoki takroriy xato), qizil (yordam so'radi yoki 10 daqiqadan ortiq qiynalmoqda), yashil (topshirdi) | Must | R1 |
| MON-02 | Plitkada: variant, qadam, oxirgi xato, urinishlar, AI murojaatlari soni | Must | R1 |
| MON-03 | Plitka bosilganda talaba kodi jonli ko'rinadi (faqat o'qish) | Must | R1 |
| MON-04 | "Qo'l ko'tarish" tugmasi va yordam navbati | Must | R1 |
| MON-05 | O'qituvchi talabaga shaxsiy xabar yoki maslahat yuboradi | Must | R1 |
| MON-06 | Holat 5 soniyadan kechikmay yangilanadi | Must | R1 |
| MON-07 | Guruh bo'yicha umumiy grafik: nechta talaba qaysi qadamda | Should | R1 |
| MON-08 | Kod yozilish jarayonini qayta ko'rish (code playback) | Should | R2 |

### 4.11. Muloqot (COM)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| COM-01 | Guruh chati | Must | R1 |
| COM-02 | O'qituvchi moderatsiyasi: xabarni o'chirish, chatni yopish | Must | R1 |
| COM-03 | O'qituvchidan guruhga e'lonlar | Should | R1 |
| COM-04 | Har mavzu uchun alohida chat kanali | Should | R2 |

### 4.12. AI tutor — Ustoz-AI (AI)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| AI-01 | Rejimlar: O'chiq, Yo'naltiruvchi (faqat savol va yo'nalish), Tushuntirish (yechimsiz), To'liq yordam. Default topshiriqda, chegara guruh sozlamasida | Must | R1 |
| AI-02 | Faqat kurs mavzulari bo'yicha, o'zbek tilida; pedagogik cheklovli tizim ko'rsatmasi (CS50 Duck uslubi) | Must | R1 |
| AI-03 | AI paneliga paste o'chirilgan; AI javobidan nusxa olish o'chirilgan | Must | R1 |
| AI-04 | So'rov server proksisi orqali; API kaliti brauzerga tushmaydi; FIO va Hemis ID yuborilmaydi | Must | R1 |
| AI-05 | Talabaga kunlik so'rov limiti; umumiy limit tugasa tushunarli xabar | Must | R1 |
| AI-06 | Har murojaat saqlanadi va o'qituvchiga ko'rinadi | Must | R1 |
| AI-07 | AI provayderi almashtiriladigan qatlam orqali ulanadi | Must | R1 |
| AI-08 | Kurs materiallariga tayanib javob berish (RAG) | Should | R2 |
| AI-09 | Pullik AI tariflari | Could | R4 |

### 4.13. Akademik halollik (INT)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| INT-01 | Laboratoriyada tashqaridan katta matnni joylashtirish cheklanadi (chegara kurs darajasida, default 200 belgi); har paste qayd qilinadi | Must | R1 |
| INT-02 | Topshirgandan keyin 2 ta tushunish savoli (variantga oldindan tayyorlangan, talaba kodiga bog'liq). Noto'g'ri javobda topshiriq balli 50% bilan cheklanadi | Must | R1 |
| INT-03 | Shaxsiy variantlar (AGR-08) | Must | R1 |
| INT-04 | Shubhali holatlar o'qituvchiga belgilanadi; avtomatik jazo yo'q, qarorni o'qituvchi qabul qiladi | Must | R1 |
| INT-05 | Nazorat rejimida tab almashtirish qayd qilinadi | Should | R1 |
| INT-06 | Tushunish savollarini talabaning o'z kodidan AI yordamida generatsiya qilish | Should | R2 |
| INT-07 | Guruh ichida kod o'xshashligi tekshiruvi | Should | R2 |

### 4.14. Baholash jurnali va sertifikat (GRD)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| GRD-01 | 100 ballik yakuniy natija: Amaliy 35, Mustaqil 25, Bilim (testlar) 20, Jamoaviy 10, Faollik 10 (vaznlar kurs darajasida). R1'da jamoaviy topshiriq bo'lmagani uchun uning 10 balli amaliyga qo'shiladi | Must | R1 |
| GRD-02 | Faollik balli: qatnashilgan kirish oynalari ulushi, muddatida topshirish, muntazamlik | Must | R1 |
| GRD-03 | Tavsiya ball istalgan paytda ko'rinadi; o'qituvchi tasdiqlaydi yoki sabab ko'rsatib o'zgartiradi (audit) | Must | R1 |
| GRD-04 | Baholash jurnali: guruh × topshiriqlar jadvali, filtrlar, Excel eksport | Must | R1 |
| GRD-05 | 90 va undan yuqori ball tasdiqlanganda sertifikat avtomatik yaratiladi (PDF): FIO, kurs, o'qituvchi, kafedra (Kompyuter ilmlari va sun'iy intellekt texnologiyalari), universitet (Abu Rayhon Beruniy nomidagi Urganch davlat universiteti), platforma (MLab), ball, sana, noyob raqam, QR | Must | R1 |
| GRD-06 | QR orqali ochiladigan tekshirish sahifasi (autentifikatsiyasiz): haqiqiyligi, kimga va qachon berilgan; Hemis ID ko'rsatilmaydi | Must | R1 |
| GRD-07 | Sertifikatni bekor qilish (tekshirish sahifasida "bekor qilingan") | Should | R1 |

### 4.15. Hisobotlar va faollik (RPT)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| RPT-01 | Talaba va guruh hisobotlari (natijalar, topshiriqlar, faollik) Excel formatida | Must | R1 |
| RPT-02 | Hisobotlar PDF formatida | Should | R1 |
| RPT-03 | Faollik hodisalarini yig'ish: kirish va chiqish, sessiyalar, onlayn vaqt, qurilma, IP, ko'rilgan sahifa va topshiriqlar, paste | Must | R1 |
| RPT-04 | Faollik tahlili paneli: grafiklar, qurilmalar, IP ro'yxati, joriy faol qurilma | Should | R2 |
| RPT-05 | "Mening ma'lumotlarim" sahifasi: talaba o'z ma'lumotlarini ko'radi va yuklab oladi | Must | R1 |

### 4.16. Ma'muriyat (ADM)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| ADM-01 | Super admin kontentni import qiladi va joriy versiyasini ko'radi | Must | R1 |
| ADM-02 | Audit jurnali: kirishlar, rollar, baho o'zgarishlari, parol tiklash, kirish oynalari | Must | R1 |
| ADM-03 | Tizim holati sahifasi: navbat, sandbox, AI limiti, disk | Should | R1 |
| ADM-04 | Kunlik zaxira va oylik tiklash sinovi | Must | R1 |

### 4.17. Datasetlar (DAT)

| ID | Talab | Ustuvorlik | Reliz |
| --- | --- | --- | --- |
| DAT-01 | Datasetlar platformada saqlanadi va `mlab.load()` bilan yuklanadi; R1 da faqat kichik hajmli (bir necha MB gacha) | Must | R1 |
| DAT-02 | Har dataset sahifasida rasmiy manba havolasi va litsenziya ko'rsatiladi | Must | R1 |
| DAT-03 | Faqat ochiq litsenziyali datasetlar; litsenziyasi noaniqlari ochiq muqobil bilan almashtiriladi | Must | R1 |

**Dastlabki ro'yxat** (litsenziyalar implementatsiya paytida rasmiy sahifadan qayta tasdiqlanadi):

| Dataset | Mavzular | Manba | Litsenziya |
| --- | --- | --- | --- |
| Iris, Wine | A1–A3, A7, A11 | UCI ML Repository / scikit-learn | CC BY 4.0 |
| Breast Cancer Wisconsin | A6, A9, A12 | UCI / scikit-learn | CC BY 4.0 |
| Digits (8×8) | A12, A13 | UCI / scikit-learn | CC BY 4.0 |
| California Housing | A4, A5, A10 | scikit-learn (StatLib) | Ochiq |
| Diabetes | A4, A5 | scikit-learn | Ochiq |
| Palmer Penguins | A1–A3, A7 | palmerpenguins | CC0 |
| Bank Marketing | A6, A9 | UCI | CC BY 4.0 |
| Online Retail | A11, assotsiativ qoidalar | UCI | CC BY 4.0 |
| Titanic | A1–A3 | OpenML | Tekshiriladi |
| Fashion-MNIST (kichik qismi) | A13–A14 | Zalando Research | MIT |

## 5. Nofunksional talablar

| ID | Toifa | Talab | O'lchov |
| --- | --- | --- | --- |
| NFR-01 | Unumdorlik | Sahifa (laboratoriyadan tashqari) javob vaqti | p95 ≤ 500 ms, 100 faol talabada |
| NFR-02 | Unumdorlik | Laboratoriya birinchi ochilishi monoblokda | ≤ 2 daqiqa; keyingi ochilishlar ≤ 15 soniya |
| NFR-03 | Unumdorlik | Server tekshiruvi natijasi (navbat bo'sh bo'lsa) | ≤ 30 soniya |
| NFR-04 | Unumdorlik | Monitoring holati yangilanishi | ≤ 5 soniya |
| NFR-05 | Masshtab | Bir vaqtdagi faol talabalar | 100 (R1), 250 (R3) |
| NFR-06 | Ishonchlilik | Dars vaqtida ishlash darajasi | ≥ 99% |
| NFR-07 | Ishonchlilik | Laboratoriya ishi yo'qolmasligi | Avtosaqlash ≤ 10 soniya; tarmoq uzilishiga chidamli |
| NFR-08 | Tiklanish | Zaxira | Kunlik; RPO ≤ 24 soat, RTO ≤ 4 soat |
| NFR-09 | Xavfsizlik | OWASP Top 10 talablari; sandbox tahdidlar modeli (8-bo'lim) | Har relizda xavfsizlik tekshiruvi |
| NFR-10 | Xavfsizlik | Parollar | Argon2; kirish urinishlari cheklangan |
| NFR-11 | Maxfiylik | Shaxsiy ma'lumotlar | 7-bo'limga muvofiq; AI'ga shaxsiy ma'lumot yuborilmaydi |
| NFR-12 | Foydalanish qulayligi | Talaba laboratoriyani o'rgatishsiz ishlata oladi | Birinchi darsda 90% talaba yordamsiz kod ishga tushiradi |
| NFR-13 | Qulaylik (accessibility) | Asosiy sahifalar | WCAG 2.1 AA asosiy talablari: kontrast, klaviatura, matn o'lchami |
| NFR-14 | Lokalizatsiya | Interfeys tili | O'zbek (lotin); matnlar alohida fayllarda (R3 da rus tili) |
| NFR-15 | Moslik | Brauzerlar | Chrome, Edge, Firefox — oxirgi 2 versiya; ekran ≥ 1280 px |
| NFR-16 | Qo'llab-quvvatlash | Kod sifati | Testlar bilan qamrov ≥ 85%, CI yashil; har texnologiya bo'yicha hujjat |
| NFR-17 | Kuzatuvchanlik | Loglar, metrikalar, healthcheck | Strukturali loglar; xatolar va navbat bo'yicha ogohlantirish |
| NFR-18 | Resurslar | Server xotirasi | Hamma servislar 4 GB RAM ichida, ≥ 500 MB zaxira bilan |

## 6. Tashqi interfeyslar

| Interfeys | Tavsif | Reliz |
| --- | --- | --- |
| Foydalanuvchi interfeysi | Veb-ilova: talaba (kurs, laboratoriya, natijalar), o'qituvchi (guruhlar, oynalar, monitoring, jurnal), admin va super admin (Django Admin) | R1 |
| Gemini API | AI tutor uchun; HTTPS; faqat server proksisi orqali; kunlik limitlar | R1 |
| Sertifikat tekshirish sahifasi | Ommaviy, autentifikatsiyasiz, faqat o'qish | R1 |
| Excel va PDF eksport | Hisobot va jurnal fayllari | R1 |
| GitHub Actions | CI/CD: test, xavfsizlik skanerlari, serverga deploy | R0 |
| Google OAuth | Google akkaunti orqali kirish | R3 |
| Email (SMTP) | Parolni tiklash va bildirishnomalar | R3 |
| Hemis | Integratsiya yo'q; Hemis ID faqat login va identifikatsiya uchun | — |

## 7. Ma'lumotlar, maxfiylik va rozilik

FIO, Hemis ID, IP manzil va qurilma ma'lumotlari shaxsiy ma'lumot hisoblanadi. Ro'yxatdan o'tishda talaba foydalanish va maxfiylik siyosati bilan tanishadi va rozilik belgisini qo'yadi; rozilik bo'lmasa ro'yxatdan o'tish yakunlanmaydi. Ma'lumotlar universitetning O'zbekistondagi serverida saqlanadi. Yakuniy matn universitet yuristi bilan kelishiladi (bu yuridik maslahat emas).

**Rozilik matni:**

```markdown
Men MLab platformasining Foydalanish va maxfiylik siyosati bilan tanishdim va roziman:
- FIO, Hemis ID, yo'nalish va guruhim o'qitish va baholash uchun saqlanadi;
- platformadagi faolligim (kirish vaqtlari, qurilma, IP manzil, topshiriqlar ustidagi ishim)
  o'qituvchim tomonidan o'quv jarayonini kuzatish uchun ko'riladi;
- AI tutorga yozgan savollarim va kodim ismimsiz holda Google Gemini xizmatiga yuboriladi.
```

**Siyosat tarkibi:**

| Bo'lim | Mazmuni |
| --- | --- |
| Mas'ul shaxs | Platforma egasi (kafedra o'qituvchisi), aloqa ma'lumotlari |
| Yig'iladigan ma'lumotlar | FIO, Hemis ID, yo'nalish, guruh; o'quv natijalari; faollik jurnali; chat xabarlari; AI tutor murojaatlari |
| Maqsad | Faqat o'qitish, baholash, akademik halollik va xavfsizlik |
| Kim ko'radi | Talabaning o'zi; uning guruhi o'qituvchisi; admin va super admin (texnik zarurat bilan). Boshqa talabalar ko'rmaydi |
| Uchinchi tomon | Faqat Google Gemini: savol va kod matni, ismsiz. Bepul tarifda Google bu matnlarni o'z xizmatlarini yaxshilash uchun ishlatishi mumkinligi ochiq aytiladi |
| Saqlash muddati | Faollik jurnali — kurs tugaganidan keyin 12 oy; AI murojaatlari — 6 oy; baholar va sertifikatlar — universitet talab qilgan muddat |
| Talaba huquqlari | O'z ma'lumotlarini ko'rish va yuklab olish; xatoni tuzatishni so'rash; kurs tugagach o'chirishni so'rash (baho va sertifikat yozuvlaridan tashqari) |
| Xavfsizlik | 5 va 8-bo'limlardagi choralar; buzilish holatida foydalanuvchilarga xabar berish |
| Foydalanish qoidalari | Akkauntni boshqalarga bermaslik; platformaga hujum qilmaslik; akademik halollik; chatda odob |

## 8. Arxitektura va texnologiyalar

Talabaning kodi uning brauzerida ishlaydi; server faqat API, real vaqt aloqasi, saqlash va rasmiy tekshiruvni bajaradi. Shu tufayli 4 GB RAM'li GPU'siz server 100 ta faol talabani ko'tara oladi.

&#91;embedded content: MLab arxitekturasi · brauzer va server komponentlari\]

Gemini'ga so'rov faqat server orqali boradi: API kaliti brauzerga tushmaydi, talabaning ismi yuborilmaydi.

**Texnologiyalar va muqobillar:**

| Qism | Tanlov | Muqobil va nega tanlanmadi |
| --- | --- | --- |
| Backend | Django + Django REST Framework | FastAPI: admin panel, auth va ORM'ni qo'lda yig'ish kerak |
| Real vaqt | Django Channels + Redis | Socket.IO (Node.js): ikkinchi til va servis |
| Ma'lumotlar bazasi | PostgreSQL 16 | — |
| Navbat | Celery + Redis | — |
| Super admin va admin interfeysi | Django Admin | Alohida admin SPA: MVP uchun ortiqcha ish |
| Talaba va o'qituvchi interfeysi | React + TypeScript (Vite) | Django shablonlari + HTMX: notebook va jonli panel uchun yetarli emas |
| Kod muharriri | CodeMirror 6 (o'z yengil notebook'imiz) | JupyterLite: boy, lekin paste nazorati va telemetriyani boshqarish qiyin |
| Brauzer Python | Pyodide (Web Worker), stlite | Server Jupyter: 4 GB RAM'ga sig'maydi |
| Sandbox | Docker (tarmoqsiz, cheklangan) | gVisor: kuchliroq izolyatsiya, R2 da baholanadi |
| AI | Gemini API, almashtiriladigan qatlam | Pullik modellar — R4 |
| Veb-server | Caddy (avtomatik HTTPS) | Nginx + certbot |
| Deploy | GitHub Actions → Docker Compose | Qo'lda deploy |

"Boring" muqobil ham ko'rib chiqildi: Moodle va CodeRunner plagini avtobaholashni beradi, lekin brauzer laboratoriyasi, jonli panel, kirish oynalari, jamoaviy estafeta va moslashuvchan variantlarni bermaydi.

**Sandbox tahdidlar modeli:**

| Tahdid | Himoya |
| --- | --- |
| Kod server yoki boshqa foydalanuvchilarga hujum qiladi | Brauzer kodi faqat talaba kompyuterida; server konteyneri tarmoqsiz, faqat o'qiladigan, root'siz, Docker soketisiz |
| Cheksiz sikl, xotira, fork-bomba | 60 soniya, 512 MB, 1 CPU, jarayonlar soni chegarasi; bir vaqtda 2 ta |
| Yashirin testlarni o'g'irlash | Yashirin testlar faqat serverda; natijada faqat ball va qisqa xabar |
| Brauzer natijasini soxtalashtirish | Rasmiy ball faqat server tekshiruvidan |
| Natija orqali XSS | Chiqishlar izolyatsiyalangan iframe va qat'iy CSP ichida |

**4 GB RAM taqsimoti (taxminiy):** OS va Caddy \~500 MB; PostgreSQL \~500 MB; Redis \~150 MB; Django + Channels \~600 MB; Celery \~250 MB; sandbox 2 × 512 MB; zaxira \~500 MB.

## 9. Reliz rejasi

Ish iterativ olib boriladi: har iteratsiya 2 hafta, oxirida ishlaydigan demo, qisqa hisobot va reja tuzatish bo'ladi. R1 (MVP) haqiqiy darsda foydalanish uchun yetarli bo'lgan birinchi relizdir; keyingi relizlar foydalanuvchi fikri asosida takomillashtiriladi.

| Reliz | Maqsad | Tarkibi (talablar) | Taxminiy hajm |
| --- | --- | --- | --- |
| R0 — Poydevor | Xavfsiz va avtomatlashtirilgan asos | Repo, CI/CD, server (Docker Compose, Caddy, HTTPS, zaxira), Django loyihasi, AUTH-01–05, rollar, Django Admin, kontent import formati (CNT-01), rozilik va siyosat sahifasi | 1 iteratsiya |
| R1 — MVP | Bir guruh bilan to'liq semestr o'tkazish | SEC, ACC (01–11), SET (01–05), CNT (02–07), LAB (01–08), AGR (01–08), ADP (01–03), INT (01–05), MON (01–07), COM (01–03), AI (01–07), GRD, RPT (01–03, 05), ADM | 5 iteratsiya |
| R2 — Faollik va o'yin | Jamoaviy ish, chuqur individuallashtirish, kengaytirilgan tahlil | TEAM, ADP-04, MON-08, COM-04, AI-08, INT-06–07, RPT-04, LAB-09, CNT-08, AUTH-06, AGR-09, ACC-12; gVisor baholash | 3 iteratsiya |
| R3 — Kengayish | Ko'proq o'qituvchi va foydalanuvchi | AUTH-07–08, rus tili, SET-06 (o'qituvchi darajasida sozlash), CNT-09, ADP-05; 250 faol foydalanuvchi | 3 iteratsiya |
| R4 — Ilg'or ML va mahsulot | Chuqur o'rganish va pullik model | LAB-10 (TensorFlow.js CNN/RNN), GPU imkoniyati, AI-09, bir nechta OTM, to'lov | Pilot natijalariga qarab |

**R1 (MVP) iteratsiyalari:**

| Iteratsiya | Natija |
| --- | --- |
| I1 | Guruhlar, qo'shilish havolasi va QR, a'zolikni tasdiqlash; kirish oynalari va guruh sozlamalari |
| I2 | Ma'ruzalar (22 mavzu, qadamlar), testlar importi; laboratoriya notebook'i (Pyodide), datasetlar |
| I3 | Topshiriqlar va avtobaholovchi (sandbox), A1–A15 variantlari, moslashuvchan daraja, akademik halollik |
| I4 | Jonli panel, yordam navbati, guruh chati, AI tutor (Gemini) |
| I5 | Baholash jurnali, sertifikat va QR, hisobotlar, audit; yuklama va xavfsizlik sinovlari, kompyuter xonasida sinov |

**Taxminiy muddat:** R0 + R1 — taxminan 12 hafta tungi ish (Claude Pro) va egasining har kungi 10–20 daqiqalik ko'rigi. Aniq muddat I1 tugagach qayta baholanadi. MVP'ni darsda qo'llash sanasi R1 qabul qilingach belgilanadi.

**Har reliz yakunida:** qabul mezonlari tekshiruvi, demo, retro (LESSONS.md), "good" teg, shaxsiy skill'larni yangilash.

## 10. MVP qabul mezonlari va sinov strategiyasi

R1 barcha "Must" talablari bajarilganda va quyidagi mezonlar tasdiqlanganda qabul qilinadi.

**Qabul mezonlari:**

- [ ] Ro'yxatdan o'tish, rozilik, kirish va parolni tiklash ishlaydi; parollar hech kimga ko'rinmaydi.
- [ ] O'qituvchi guruh yaratadi; 30 talaba QR orqali so'rov yuboradi va ommaviy tasdiqlanadi.
- [ ] Kirish oynalari: qo'lda ochish va yopish, jadval va takroriy slot ishlaydi; yopilganda ish saqlanadi.
- [ ] 22 ma'ruza qadamlarga bo'lingan; testlar import qilingan.
- [ ] A1–A15: umumiy topshiriq, 3 daraja × 5 variant, challenge va mustaqil topshiriq avtomatik baholanadi.
- [ ] Laboratoriya kompyuter xonasidagi monoblokda 2 daqiqada ishga tushadi.
- [ ] Jonli panel 30 talabani 5 soniyalik kechikish bilan ko'rsatadi; yordam navbati ishlaydi.
- [ ] AI tutor rejimlari va guruh chegarasi ishlaydi; uni bir tugma bilan o'chirish mumkin.
- [ ] Paste cheklovi va tushunish savollari ishlaydi.
- [ ] 100 ballik hisob, tavsiya ball, sertifikat va QR tekshiruvi ishlaydi.
- [ ] Excel hisobotlar yuklab olinadi; "Mening ma'lumotlarim" sahifasi ishlaydi.
- [ ] Yuklama sinovi: 100 virtual talaba, NFR-01–04 bajariladi.
- [ ] Xavfsizlik sinovi: sandbox'dan chiqish, boshqa talaba ma'lumotiga kirish va yashirin testlarni olish urinishlari muvaffaqiyatsiz.

**Sinov strategiyasi:**

| Daraja | Nima | Vosita |
| --- | --- | --- |
| Unit | Biznes qoidalari: ball, daraja tanlash, oynalar, ruxsatlar | pytest, Vitest |
| Integration | API, ma'lumotlar bazasi, navbat, WebSocket | pytest-django, Channels test vositalari |
| Avtobaholovchi | Har variantning namunaviy to'g'ri va noto'g'ri yechimlari | Har topshiriq uchun avtomatik test to'plami |
| E2E | Ro'yxatdan o'tish → guruh → oyna → topshirish → ball; o'qituvchi monitoringi | Playwright |
| Yuklama | 100 bir vaqtdagi talaba | Locust yoki k6 |
| Xavfsizlik | Sandbox chiqishi, IDOR, XSS, secret oqishi | Qo'lda sinov + security-reviewer, gitleaks, pip-audit |
| Foydalanuvchi | Kompyuter xonasida haqiqiy talabalar bilan sinov darsi | So'rovnoma |

## 11. Xavflar

| Xavf | Ehtimol | Ta'sir | Choralar |
| --- | --- | --- | --- |
| Laboratoriya eski monobloklarda sekin | O'rta | Yuqori | I2 da kompyuter xonasida erta sinov; kichik datasetlar; Pyodide o'z serverdan |
| Server tekshiruv navbatida bo'g'iladi | O'rta | O'rta | Ko'rinadigan testlar brauzerda; serverda faqat "Topshirish"; navbat holati ko'rinadi; yuklama sinovi |
| Gemini bepul limiti darsda tugaydi | Yuqori | Past | Talabaga kunlik limit; tushunarli xabar; provayderni almashtirish imkoni |
| Tarmoq yoki elektr uzilishi | Past | Yuqori | Avtosaqlash va lokal bufer; kechikish muddati |
| Claude Pro limiti ishni sekinlatadi | O'rta | O'rta | Mayda tasklar; har iteratsiyada reja tuzatish |
| Talabalar laboratoriya tashqarisida AI'dan ko'chiradi | Yuqori | O'rta | Tushunish savollari, shaxsiy variantlar, jarayon bo'yicha baholash |
| Kontent sifati past (minimal versiya) | O'rta | O'rta | MVP'da amaliyotga urg'u; R2 dan keyin kontent sifati oshiriladi |
| Shaxsiy ma'lumotlar bo'yicha talablar | Past | Yuqori | Rozilik, siyosat, mahalliy server, yurist bilan kelishuv |

## 12. Ushbu versiyadagi optimallashtirish takliflari va ochiq savollar

v2 da quyidagi o'zgarishlar kiritildi. Birinchi uchtasi egasining qarori, qolganlari Claude taklifi — TZ tasdiqlanganda ular ham qabul qilingan hisoblanadi.

| # | O'zgarish | Manba | Foyda |
| --- | --- | --- | --- |
| 1 | Clone va konstruktor o'rniga: bitta kurs + o'qituvchi guruhlari; guruhga a'zolik orqali kursga yozilish | Egasi | Murakkablik va xato manbai kamayadi; kontent o'zgarishi hamma guruhda darhol |
| 2 | Darsni emas, guruhning mavzularga kirish oynalarini boshqarish | Egasi | Bitta tushuncha bilan dars vaqti, kechikish va nazorat rejimi hal bo'ladi |
| 3 | O'qituvchi kursni emas, guruh sozlamalarini boshqaradi (AI tutor, a'zolik, mashq rejimi) | Egasi | Sozlamalar ikki darajada (kurs va guruh), R3 ga kengaytirish oson |
| 4 | Kontent kod sifatida (Markdown/YAML, Git) va Django Admin; alohida kontent muharriri R3 ga | Claude | MVP ishining sezilarli qismi tejaladi; kontent versiyalanadi va PR orqali ko'riladi |
| 5 | JupyterLite o'rniga o'z yengil notebook'imiz (CodeMirror + Pyodide) | Claude | Paste nazorati, telemetriya va monitoringni to'liq boshqarish |
| 6 | Tushunish savollari R1 da oldindan tayyorlangan, R2 da AI generatsiyasi | Claude | AI limitiga bog'liq bo'lmagan ishonchli MVP |
| 7 | Jamoaviy estafeta, to'liq mastery va faollik tahlili paneli R2 ga | Claude | MVP tezroq chiqadi; asosiy o'quv sikli birinchi |
| 8 | "Pilot" o'rniga MVP va R0–R4 iterativ relizlar | Egasi | Har 2 haftada ishlaydigan natija |

**Ochiq savollar (ish davomida aniqlanadi):**

- Kompyuter xonasidagi monobloklar parametrlari (RAM, brauzer) — I2 dagi sinov uchun.
- Universitet serveriga domen va HTTPS: alohida domen yoki universitet subdomeni?
- Rozilik matni va siyosatni universitet yuristi bilan kelishish.
- Sertifikatda universitet logotipidan foydalanishga ruxsat.

## 13. Izlanuvchanlik (traceability)

Egasining dastlabki 27 talabining har biri qaysi talablar bilan qoplanganini ko'rsatadi.

| # | Egasining talabi (qisqa) | Qoplovchi talablar | Reliz |
| --- | --- | --- | --- |
| 1 | Sodda ro'yxatdan o'tish va kirish | AUTH-01–04, 7-bo'lim | R1 |
| 2 | WebSocket, real vaqtda ishlash va monitoring | MON-01–06, NFR-04 | R1 |
| 3 | Ma'ruza, test, topshiriq, amaliy (individual, jamoaviy, AI bilan/siz), mustaqil topshiriq, sertifikat | CNT, AGR, AI-01, ACC-10, GRD-05; TEAM | R1; R2 |
| 4 | Stepik va W3Schools uslubidagi qadamli, "try it" ko'rsatmalar | CNT-02–03 | R1 |
| 5 | Colab'ga o'xshash sodda va xavfsiz laboratoriya | LAB-01–07, AGR-03, 8-bo'lim | R1 |
| 6 | Umumiy, individual (5–10 variant) va jamoaviy topshiriqlar; 60 daqiqalik ish | AGR-07–08, ACC-04; TEAM | R1; R2 |
| 7 | Amaliy topshiriqlarni avtomatik tekshirish | AGR-01–06 | R1 |
| 8 | Guruhni real vaqtda kuzatish va oqsayotganlar bilan ishlash | MON-01–05 | R1 |
| 9 | Umumiy baza; o'qituvchi guruhi; havola va QR orqali qo'shilish | SEC-01–05, SET (v2: clone o'rniga guruhlar) | R1 |
| 10 | Bilim darajasiga mos individual topshiriqlar | ADP-01–03; ADP-04 | R1; R2 |
| 11 | Jamoaviy loyiha: avtomatik jamoalar, daraja bo'yicha taqsimlash, vizual progress, o'yin | TEAM-01–06 | R2 |
| 12 | AI bilan ko'r-ko'rona nusxa ko'chirishga qarshi tizim | INT-01–07, AI-03 | R1; R2 |
| 13 | O'yin orqali to'liq ML jarayoni; platformaga AI integratsiyasi | TEAM-02, AI-01–08, LAB | R1; R2 |
| 14 | Murakkablikka qarab AI ruxsati; Ctrl+C/V cheklovi | AI-01, AI-03, SET-01–02 | R1 |
| 15 | Yetarli baza: testlar, topshiriqlar, loyihalar, datasetlar | CNT-04–06, AGR-07, DAT | R1 |
| 16 | Neyron to'rni vizual qurish va avtomatik kod | LAB-09 | R2 |
| 17 | Chuqur o'rganish: CNN, RNN, rasmli datalar | A14 namoyishi; LAB-10 | R1; R4 |
| 18 | Platformadagi datasetlar, rasmiy havolalar, mualliflik huquqi | DAT-01–03 | R1 |
| 19 | O'qituvchi hisobotlari, monitoring va yuklab olish | RPT-01–02, GRD-04 | R1 |
| 20 | Umumiy va har mavzu uchun chat | COM-01; COM-04 | R1; R2 |
| 21 | FIO, Hemis ID (login), yo'nalish, guruh | AUTH-01, SEC-03 | R1 |
| 22 | Faollikni to'liq kuzatish (sessiyalar, qurilmalar, IP, mavzular) | RPT-03; RPT-04 | R1; R2 |
| 23 | Yopiq platforma, o'qituvchi tasdig'i, kelajakda pullik | 2.1, SEC-04; to'lov R4. Public rejim v2 da olib tashlandi | R1; R4 |
| 24 | Mustaqil ta'lim \~50% | ACC-10, AGR-07 (har amaliyga mustaqil topshiriq), GRD-01 | R1 |
| 25 | Ma'ruza va mustaqil ta'lim ochiq; amaliy faqat ruxsat yoki jadval bo'yicha | ACC-01–04 | R1 |
| 26 | Turli interaktiv topshiriqlar | CNT-03; CNT-08 | R1; R2 |
| 27 | Tavsiya baholar | GRD-01–03 | R1 |
