# ADR-0002: Kurs kontenti formati va import

- **Sana:** 2026-11-22
- **Holat:** Qabul qilindi

## Kontekst
CNT-01: kurs kontenti versiyalanadigan matn fayllarida saqlanadi va import buyrug'i bilan bazaga yuklanadi.
Kontentni egasi va Claude Git orqali yozadi va ko'rib chiqadi (PR). Ma'ruza 5–10 qadamdan iborat (CNT-02).
Laboratoriya topshiriqlarining yashirin testlari va yechimlari hech qachon brauzerga chiqmasligi kerak (AGR-05).

## Variantlar
| Variant | Afzallik | Kamchilik |
| --- | --- | --- |
| A. Markdown (qadamlar `##` sarlavhalar bilan) + YAML meta fayllar | Git diff o'qiladi; GitHub'da ko'rinadi; oddiy muharrirda yoziladi; PyYAML — yetuk, `safe_load` | Ikki format; sxema tekshiruvi o'zimizda |
| B. Bitta katta YAML/JSON fayl | Bitta parser, sxema oson | Markdown matnni YAML ichida yozish noqulay; katta diff, konfliktlar |
| C. Jupyter notebook (`.ipynb`) | Kod va matn birga; ML uchun tabiiy | JSON diff o'qilmaydi; chiqishlar (output) repoga tushadi; qadamlarga bo'lish qiyin |
| D. Faqat Django Admin (bazada) | Kod kerak emas | Versiya va ko'rib chiqish yo'q; CNT-01 ga zid |

## Qaror
**A.** Tuzilma:

```text
content/
  course.yaml                     # slug, title, version; ixtiyoriy defaults: (SET, I1-07)
  topics/<CODE>-<slug>/meta.yaml  # code, title, order
  topics/<CODE>-<slug>/lecture.md # "# Sarlavha", keyin har "## Qadam" — bitta qadam
  labs/<CODE>-<slug>/...          # R1 (I3): assignment.yaml, variants/, tests/visible/, tests/hidden/, solutions/
```

- YAML faqat `yaml.safe_load` (kompozitsiya orqali) bilan o'qiladi — ixtiyoriy Python obyektlari yaratilmaydi.
- Import **idempotent**: tabiiy kalitlar (`course.slug`, `topic.code`, `step.order`) bo'yicha yaratadi yoki
  yangilaydi, fayllarda yo'q qadam va mavzularni o'chiradi. Ikki marta import — bir xil holat.
- Import **bitta tranzaksiya**: avval hamma fayl o'qiladi va tekshiriladi, keyin yoziladi. Xato bo'lsa —
  fayl nomi va qator raqami bilan aniq xabar, baza o'zgarmaydi.
- Kontent versiyasi: `course.yaml` dagi `version` va barcha import qilingan fayllarning SHA-256 xeshi
  (`Course.content_hash`) saqlanadi.
- **Maxfiy yo'llar:** `tests/hidden/` va `solutions/` (`apps.courses.content.PRIVATE_DIRS`) ma'ruza
  importida umuman o'qilmaydi; laboratoriya importi (I3) ularni faqat server tomonidagi modelga yozadi va
  API serializer'lari ularni hech qachon qaytarmaydi (AGR-05).

## Oqibatlar
- Kontent PR orqali ko'rib chiqiladi, `content/` dagi o'zgarish CI'da import testidan o'tadi.
- Hozircha mavzu fayllardan olib tashlansa, bazadan ham o'chiriladi. Talaba natijalari mavzuga bog'langanda
  (R1) bu `PROTECT` bilan to'xtatiladi va import aniq xato beradi — mavzu "arxivlangan" holatga o'tkaziladi.
- Rasm va interaktiv qadamlar (CNT-02, CNT-03) va Aiken testlari (CNT-05) keyingi tasklarda shu formatga qo'shiladi.
