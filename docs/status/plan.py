"""Loyiha rejasi va holati — dashboard manbai. Holatlar: done, in_progress, ready, planned, blocked.

Issue raqami bor task — GitHub issue; `E-...` — hali issue'larga bo'linmagan epik (taxminiy ball).
"""

META = {
    "as_of": "2026-11-24",
    "velocity_per_day": 9,  # ball/kun: kuniga 2 tungi run x ~4-5 ball (haftalik review aniqlaydi)
    "velocity_note": "Kuniga 2 tungi run, har biri ~4-5 ball (M=2, S=1). Yakshanba — 1 run + review.",
    "current_release": "R1",
    "current_iteration": "I1",
    "next_task": "#71 I1 yakuni: ko'rik, uchidan-uchiga test, dars",
}

RELEASES = [
    {"release": "R0", "order": 0, "name": "Poydevor", "goal": "Xavfsiz va avtomatlashtirilgan asos",
     "outcome": "Ro'yxatdan o'tish, kirish, rollar, parol tiklash, audit jurnali, kontent importi, prod konteynerlari, deploy va zaxira skriptlari.",
     "size_text": "1 iteratsiya"},
    {"release": "R1", "order": 1, "name": "MVP", "goal": "Bir guruh bilan to'liq semestr o'tkazish",
     "outcome": "Guruhlar va kirish oynalari, brauzerdagi Python laboratoriyasi, avtobaholovchi, jonli monitoring, AI tutor, baholash va sertifikat.",
     "size_text": "5 iteratsiya"},
    {"release": "R2", "order": 2, "name": "Faollik va o'yin", "goal": "Jamoaviy ish, chuqur individuallashtirish, kengaytirilgan tahlil",
     "outcome": "Jamoaviy topshiriqlar, kengaytirilgan monitoring va tahlil, gVisor baholash.",
     "size_text": "3 iteratsiya"},
    {"release": "R3", "order": 3, "name": "Kengayish", "goal": "Ko'proq o'qituvchi va foydalanuvchi",
     "outcome": "Rus tili, o'qituvchi darajasida sozlash, Hemis ID faollashtirish kodi, 250 faol foydalanuvchi.",
     "size_text": "3 iteratsiya"},
    {"release": "R4", "order": 4, "name": "Ilg'or ML va mahsulot", "goal": "Chuqur o'rganish va pullik model",
     "outcome": "TensorFlow.js (CNN/RNN), GPU imkoniyati, bir nechta OTM, to'lov.",
     "size_text": "pilot natijalariga qarab"},
]

ITERATIONS = [
    {"iteration": "I0", "release": "R0", "order": 0, "name": "Poydevor", "est_points": 29,
     "outcome": "Backend va frontend skeleti, CI, auth, rollar, audit, kontent formati, deploy tayyorgarligi."},
    {"iteration": "I1", "release": "R1", "order": 1, "name": "Guruhlar va kirish oynalari", "est_points": 27,
     "outcome": "O'qituvchi guruh yaratadi, havola/QR beradi, so'rovlarni tasdiqlaydi; sozlamalar; mavzular bo'yicha kirish oynalari va jadval."},
    {"iteration": "I2", "release": "R1", "order": 2, "name": "Kontent va laboratoriya", "est_points": 55,
     "outcome": "22 ma'ruza qadamlari, Aiken testlari, Pyodide notebook (brauzerda Python), datasetlar, monoblokda sinov."},
    {"iteration": "I3", "release": "R1", "order": 3, "name": "Avtobaholovchi va topshiriqlar", "est_points": 70,
     "outcome": "Sandbox baholash, A1–A15 topshiriqlari va variantlar, moslashuvchan daraja, akademik halollik."},
    {"iteration": "I4", "release": "R1", "order": 4, "name": "Monitoring, chat, AI tutor", "est_points": 50,
     "outcome": "Jonli monitoring paneli, yordam navbati, guruh chati, Gemini AI tutor (cheklovli)."},
    {"iteration": "I5", "release": "R1", "order": 5, "name": "Baholash va qabul", "est_points": 40,
     "outcome": "100 ballik baholash, Excel jurnal, sertifikat va QR, hisobotlar, yuklama sinovi, sinov darsi."},
    {"iteration": "KONTENT", "release": "R1", "order": 6, "name": "Kurs kontenti (parallel)", "est_points": 130,
     "outcome": "M01–M22 ma'ruzalar va A1–A15 amaliy topshiriqlar matni — kod bilan parallel, I2–I5 davomida."},
    {"iteration": "R2", "release": "R2", "order": 7, "name": "R2 iteratsiyalari", "est_points": None,
     "outcome": "R1 dan keyin rejalashtiriladi."},
    {"iteration": "R3", "release": "R3", "order": 8, "name": "R3 iteratsiyalari", "est_points": None,
     "outcome": "R2 dan keyin rejalashtiriladi."},
    {"iteration": "R4", "release": "R4", "order": 9, "name": "R4", "est_points": None,
     "outcome": "Pilot natijalariga qarab."},
]


def _t(iteration, key, issue, title, req, size, status, outcome, pr=""):
    release = next(i["release"] for i in ITERATIONS if i["iteration"] == iteration)
    return {"release": release, "iteration": iteration, "key": key, "issue": issue, "title": title,
            "req": req, "size": size, "status": status, "outcome": outcome, "pr": pr}


TASKS = [
    # --- R0 ---
    _t("I0", "R0-01", "#5", "Backend skeleti va CI", "NFR-16, NFR-17", "M", "done", "Django loyihasi, testlar va CI avtomatik ishlaydi", "#22"),
    _t("I0", "R0-02", "#6", "Frontend skeleti", "NFR-14, NFR-15", "M", "done", "React ilova, o'zbekcha matnlar fayli, testlar", "#23"),
    _t("I0", "R0-03", "#7", "Lokal servislar (compose)", "—", "S", "done", "PostgreSQL va Redis bitta buyruq bilan", "#29"),
    _t("I0", "R0-04", "#8", "Foydalanuvchi modeli (Hemis ID, Argon2)", "AUTH-01, AUTH-03", "M", "done", "Hemis ID bilan kirish, xavfsiz parol saqlash", "#28"),
    _t("I0", "R0-05", "#9", "Rollar va ruxsatlar, Django Admin", "SRS 2.2", "M", "done", "4 rol, admin panel, rol o'zgarishi auditda", "#33"),
    _t("I0", "R0-06", "#10", "Ro'yxatdan o'tish API va rozilik", "AUTH-01, SRS 7", "M", "done", "Talaba rozilik bilan ro'yxatdan o'tadi", "#37"),
    _t("I0", "R0-07", "#11", "Kirish/chiqish, 5 xato → blok", "AUTH-02", "M", "done", "Parolni taxmin qilishga qarshi himoya", "#39"),
    _t("I0", "R0-08", "#12", "Parolni tiklash", "AUTH-04, ADM-02", "M", "done", "Vaqtinchalik parol, majburiy almashtirish", "#44"),
    _t("I0", "R0-09", "#13", "O'qituvchi akkaunti va talaba limiti", "AUTH-05, SEC-08", "S", "done", "Admin o'qituvchi yaratadi, limit belgilaydi", "#45"),
    _t("I0", "R0-10", "#14", "Kirish va ro'yxatdan o'tish sahifalari", "AUTH-01..04", "M", "done", "Brauzerda ro'yxatdan o'tish, kirish, parol almashtirish", "#48"),
    _t("I0", "R0-11", "#15", "Siyosat sahifasi", "SRS 7", "S", "done", "Ochiq /policy sahifasi", "#49"),
    _t("I0", "R0-12", "#16", "Audit jurnali", "ADM-02", "S", "done", "Muhim harakatlar o'chirilmaydigan jurnalda", "#31"),
    _t("I0", "R0-13", "#17", "Kontent formati va import", "CNT-01", "M", "done", "Ma'ruzalar fayldan bazaga", "#35"),
    _t("I0", "R0-14", "#18", "JSON loglar, /readyz", "NFR-17", "S", "done", "Kuzatuv: request id, shaxsiy ma'lumot maskalanadi", "#30"),
    _t("I0", "R0-15", "#19", "Prod konteynerlari, Caddy, ADR-0004", "NFR-08", "M", "done", "Serverga tayyor Docker sozlamalari", "#53"),
    _t("I0", "R0-16", "#20", "Deploy, smoke test, zaxira skriptlari", "ADM-04, NFR-08", "M", "done", "Bir buyruqli deploy, kunlik zaxira va tiklash", "#56"),
    _t("I0", "R0-16b", "", "Birinchi haqiqiy deploy va tiklash sinovi", "ADM-04", "S", "blocked", "Server va domen tayyor bo'lgach (egasi)"),
    _t("I0", "R0-17", "#21", "Darslar (docs/learn)", "—", "S", "done", "Egasi uchun texnologiya darslari", "#46"),
    # --- R1 / I1 ---
    _t("I1", "I1-01", "#57", "Guruh va a'zolik modellari", "SEC-01, SEC-07", "M", "done", "Bitta faol guruh qoidasi bazada", "#73"),
    _t("I1", "I1-02", "#58", "Guruh API", "SEC-01, SEC-08, SET-03", "M", "done", "O'qituvchi guruh yaratadi va tahrirlaydi", "#74"),
    _t("I1", "I1-03", "#59", "Qo'shilish havolasi (token)", "SEC-02", "S", "done", "Yangilanadigan maxfiy havola", "#75"),
    _t("I1", "I1-04", "#60", "Havola orqali so'rov", "SEC-03, SEC-06, SEC-07", "M", "done", "Talaba havola orqali guruhga so'rov yuboradi", "#76"),
    _t("I1", "I1-05", "#61", "So'rovlarni tasdiqlash (ommaviy)", "SEC-04..06, SEC-08", "M", "done", "O'qituvchi bir tugmada tasdiqlaydi; sig'im va limit", "#78"),
    _t("I1", "I1-06", "#62", "Boshqa guruhga o'tkazish", "SEC-07", "S", "done", "Talaba ishlari saqlanib o'tkaziladi", "#79"),
    _t("I1", "I1-07", "#63", "Guruh sozlamalari, AI o'chirish", "SET-01..05", "M", "done", "Kurs default → guruh sozlamasi; AI bir tugmada", "#80"),
    _t("I1", "I1-08", "#64", "Kirish oynalari", "ACC-01..03, ACC-09, ACC-11", "M", "done", "Laboratoriya yopiq/hozir/jadval bo'yicha ochiladi", "#81"),
    _t("I1", "I1-09", "#65", "Haftalik jadval yordamchisi", "ACC-04", "M", "done", "Mavzular haftalik slotlarga avtomatik", "#83"),
    _t("I1", "I1-10", "#66", "Topshirish siyosati, muddatlar", "ACC-06..08, ACC-10", "M", "done", "O'z vaqtida / kechikkan / mashq / yopiq", "#84"),
    _t("I1", "I1-11", "#67", "Real vaqt: 'oyna ochildi' xabari", "ACC-05", "M", "done", "Talaba sahifani yangilamasdan xabar oladi", "#87"),
    _t("I1", "I1-12", "#68", "Frontend: o'qituvchi guruhlari, QR", "SEC-01..05", "M", "done", "Guruh yaratish, havola va QR, so'rovlar", "#89"),
    _t("I1", "I1-13", "#69", "Frontend: talaba qo'shilishi", "SEC-03, ACC-05", "M", "done", "Havola → so'rov → holat, keyingi mavzu vaqti", "#91"),
    _t("I1", "I1-14", "#70", "Frontend: sozlamalar va oynalar", "SET, ACC-03, ACC-04", "M", "done", "Oynalarni ochish/yopish, jadval, AI tugmasi", "#92"),
    _t("I1", "I1-15", "#71", "I1 yakuni: ko'rik va e2e", "I1", "S", "ready", "Xavfsizlik ko'rigi, uchidan-uchiga test, dars"),
    # --- R1 keyingi iteratsiyalar (epiklar, taxminiy) ---
    _t("I2", "E-I2-1", "", "Kontent qadamlari, vizual qadam, Aiken testlari", "CNT-02..07", "", "planned", "Ma'ruzalar interaktiv, mavzu testlari", ""),
    _t("I2", "E-I2-2", "", "Laboratoriya: Pyodide notebook", "LAB-01..07", "", "planned", "Brauzerda Python, avtosaqlash", ""),
    _t("I2", "E-I2-3", "", "Datasetlar va monoblokda sinov", "DAT-01..03, NFR-02", "", "planned", "8 GB RAM monoblokda ishlashi tekshiriladi", ""),
    _t("I3", "E-I3-1", "", "Avtobaholovchi (sandbox, navbat)", "AGR-01..06", "", "planned", "Kod xavfsiz konteynerda baholanadi", ""),
    _t("I3", "E-I3-2", "", "A1–A15 topshiriqlari va variantlar", "AGR-07..08", "", "planned", "3 daraja x 5 variant", ""),
    _t("I3", "E-I3-3", "", "Moslashuvchan daraja, akademik halollik", "ADP-01..03, INT-01..05", "", "planned", "Daraja moslashadi, ko'chirishga qarshi choralar", ""),
    _t("I4", "E-I4-1", "", "Jonli monitoring, yordam navbati", "MON-01..07", "", "planned", "O'qituvchi sinfni real vaqtda ko'radi", ""),
    _t("I4", "E-I4-2", "", "Guruh chati va e'lonlar", "COM-01..03", "", "planned", "Moderatsiyali chat", ""),
    _t("I4", "E-I4-3", "", "AI tutor (Gemini, cheklovli)", "AI-01..07, LAB-08", "", "planned", "Yechimsiz yo'naltiruvchi yordamchi", ""),
    _t("I5", "E-I5-1", "", "Baholash, jurnal, Excel", "GRD-01..04", "", "planned", "100 ball, faollik, tasdiqlash", ""),
    _t("I5", "E-I5-2", "", "Sertifikat, QR, tekshirish", "GRD-05..07", "", "planned", "Tekshiriladigan sertifikat", ""),
    _t("I5", "E-I5-3", "", "Hisobotlar, tizim holati, yuklama sinovi, sinov darsi", "RPT, ADM, SRS 10", "", "planned", "MVP qabul mezonlari", ""),
    _t("KONTENT", "E-K-1", "", "M01–M22 ma'ruzalar, A1–A15 matnlari", "CNT", "", "planned", "Kurs kontenti", ""),
]
