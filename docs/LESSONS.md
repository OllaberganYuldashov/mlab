# LESSONS — haftalik retro

> Har hafta (yakshanba review run'ida) yoziladi. Milestone'da shaxsiy skill uchun manba bo'ladi.

## Shablon

### <Hafta: YYYY-MM-DD>
- **Yaxshi ishladi:**
- **Muammo bo'ldi:**
- **Sabab:**
- **Yangi qoida (CLAUDE.md yoki skill'ga):**
- **Limit sarfi va runlar soni:**

### Post-mortem: 2026-11-26/27 — GitHub Actions daqiqalari tugadi (qizil chiroq, #193)
- **Nima bo'ldi:** 2026-11-26 18:53 UTC dan har Actions job'i 3–4 soniyada qadamsiz `failure` bo'ldi. Ikki
  urinishdan keyin holat Qizil. Merge'lar ~8 soat to'xtadi. Kod sabab emas edi.
- **Sabab:** private repo'ning oylik bepul limiti (2000 daqiqa, $12) 5,5 kunda tugadi — kuniga ~400 daqiqa.
  CI draft PR'ga har push'da ishlardi; har job yuqoriga, butun daqiqagacha yaxlitlanadi.
- **Nega erta sezilmadi:** sog'liq tekshiruvida Actions sarfi yo'q edi; billing API'si Claude'ga ko'rinmaydi.
- **Tiklash:** variant A (oldinga tuzatish) — egasi repo'ni vaqtincha public qildi. Hech narsa yo'qolmadi.
- **Yangi qoida:** run boshida Actions sarfi o'lchanadi (`scripts/actions-usage.sh`), draft PR'da CI ishlamaydi,
  qayta ishga tushirishda faqat yiqilgan job (docs/CI-BUDGET.md). Workflow o'zgarishi egasining tasdig'ini kutmoqda.
