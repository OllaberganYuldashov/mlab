# ADR-0007: Avtobaholovchi — sandbox, navbat va Docker'ga kirish

- **Sana:** 2026-11-24
- **Holat:** Qabul qilindi (I3-01, #149)

## Kontekst
AGR-02..05: "Topshirish" bosilganda talaba kodi va **yashirin testlar** serverda bajariladi va rasmiy ball qaytadi.
CLAUDE.md §5.5: talaba kodi hech qachon Django yoki Celery jarayonida bajarilmaydi — faqat izolyatsiyalangan konteynerda.
AGR-03 cheklovlari: tarmoqsiz, faqat o'qiladigan FS, root'siz, 512 MB, 1 CPU, 60 s, jarayonlar soni cheklangan.
AGR-04: bir vaqtda 2 ta konteyner, navbat holati real vaqtda. Server: 8 GB RAM (ARCHITECTURE: sandbox 2 × 512 MB).
Brauzerdagi Pyodide (ADR-0006) va server natijalari bir xil bo'lishi kerak (talaba "Tekshirish"da o'tib, "Topshirish"da
yiqilmasin).

## Variantlar

**Navbat**
| Variant | Afzallik | Kamchilik |
| --- | --- | --- |
| **A. Celery + Redis** (ADR-0001 stack'ida) | Tayyor: qayta urinish, vaqt chegarasi, `concurrency=2`, monitoring | Yana bitta jarayon (worker) |
| B. PostgreSQL navbati (`SKIP LOCKED`) | Yangi komponent yo'q | Retry/timeout/beat'ni o'zimiz yozamiz; Celery baribir I3/I5 da kerak (rejali yopilishlar, eslatmalar) |

**Docker'ga kirish** (eng muhim xavfsizlik qarori)
| Variant | Afzallik | Kamchilik |
| --- | --- | --- |
| A. Worker'ga `/var/run/docker.sock` | Oddiy | Worker buzilsa — host'da root (istalgan konteyner, istalgan mount) |
| B. docker-socket-proxy (faqat `CONTAINERS`, `POST`) | API bo'limlari cheklanadi | **Konteyner sozlamasini cheklamaydi**: `privileged`, host mount'li konteyner yaratish mumkin — A bilan deyarli bir xil xavf |
| **C. Alohida "launcher" xizmati** | Docker'ga faqat u kiradi; tashqariga bitta qat'iy API: `POST /run {code, tests, timeout}`. Konteyner sozlamasi (image, cheklovlar) launcher kodida qotirilgan — worker uni o'zgartira olmaydi | Kichik qo'shimcha xizmat (~150 qator Python) |
| D. gVisor / Firecracker | Kuchliroq izolyatsiya | Murakkab; R2 da baholanadi (ADR-0001) |

## Qaror

1. **Navbat: Celery 5 + Redis broker** (ADR-0001), `worker --concurrency=2`, `acks_late`, `task_time_limit` (sandbox 60 s +
   zaxira). Vazifa idempotent: `Submission` holati qulf ostida o'tadi (`queued → running → done/error`), takroriy
   yetkazishda qayta baholanmaydi. Qayta urinish faqat infratuzilma xatosida (launcher javob bermadi), talaba kodi xatosida emas.
2. **Docker'ga kirish: C — `sandbox-launcher` xizmati.** Docker soketi faqat unga ulanadi (ichki tarmoq, tashqariga port
   yo'q). Worker launcher'ga `POST /run` yuboradi: talaba kodi, testlar (yashirin testlar ham shu yerda), vaqt chegarasi.
   Launcher har so'rov uchun **o'zi** quyidagi sozlama bilan konteyner yaratadi:
   - image: `mlab-sandbox:<versiya>` (faqat shu, digest bilan),
   - `--network none`, `--read-only`, `--tmpfs /tmp:size=64m,noexec`, `--user 10003:10003`,
   - `--memory 512m --memory-swap 512m`, `--cpus 1`, `--pids-limit 64`,
   - `--cap-drop ALL`, `--security-opt no-new-privileges`, standart seccomp, `--ulimit nofile=64`,
   - vaqt: 60 s dan keyin `kill` va `remove` (har holatda, `finally`).
   Kod va testlar konteynerga **stdin** orqali (fayl tizimiga mount yo'q), natija — stdout'dagi JSON, 256 KB dan oshsa kesiladi.
3. **Sandbox image** (`sandbox/Dockerfile`): Python **3.14** va Pyodide 314.0.7 dagi bilan **aynan bir xil** versiyalar:
   numpy 2.4.6, pandas 3.0.2, scikit-learn 1.8.0, scipy 1.18.0, matplotlib 3.10.8 (PyPI'da cp314 wheel'lari bor —
   2026-11-24 tekshirildi). Datasetlar image ichida (`mlab.load` bilan bir xil API, tarmoqsiz). Root'siz, minimal.
4. **Runner** (`sandbox/runner.py`): har test alohida, vaqt va natija; talabaga faqat test **nomi** (ko'rinadiganlar uchun)
   yoki umumiy xabar (yashirinlar uchun), ball va o'tgan/o'tmagan soni — yashirin test kodi va ichki traceback chiqmaydi (AGR-05).
5. **Yangi sozlamalar** (implementatsiya PR'larida): `SANDBOX_LAUNCHER_URL`, `SANDBOX_IMAGE`, `CELERY_BROKER_URL` — SECURITY.md.
6. **CI:** image build va hujum testlari (tarmoq yo'q, yozib bo'lmaydi, fork-bomba, xotira/vaqt) — workflow o'zgarishi
   `needs:owner`.

## Oqibatlar
- Yangi xizmatlar: `worker` (Celery) va `sandbox-launcher`; RAM: worker ~250 MB, launcher ~50 MB, sandbox 2 × 512 MB —
  ARCHITECTURE byudjetiga sig'adi.
- Launcher — eng nozik komponent: kichik, alohida xavfsizlik ko'rigi (I3-19), o'z testlari bilan.
- Docker konteyner izolyatsiyasi MVP uchun yetarli deb qabul qilindi: yashirin testlar baribir serverda, talaba kodi
  tarmoqsiz va cheklangan. R2 da gVisor (`runsc`) baholanadi — launcher'da faqat runtime parametri o'zgaradi.
- Dars: `docs/learn/sandbox.md`.
