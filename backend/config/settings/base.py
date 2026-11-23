"""Umumiy sozlamalar. Muhitga xos fayllar: dev.py, test.py, prod.py.

Hamma muhitga bog'liq qiymat muhit o'zgaruvchisidan o'qiladi (config/env.py); majburiysi
yo'q bo'lsa ilova ishga tushmaydi. Yangi sozlama: .env.example (soxta qiymat) va
docs/SECURITY.md jadvaliga qo'shiladi.
"""

from __future__ import annotations

from pathlib import Path

from config import env

BASE_DIR = Path(__file__).resolve().parents[2]

# --- Majburiy sozlamalar (fail fast) ---
SECRET_KEY = env.required("SECRET_KEY")
ALLOWED_HOSTS = env.required_list("ALLOWED_HOSTS")
DATABASES = {"default": {**env.database("DATABASE_URL"), "CONN_MAX_AGE": 60}}
REDIS_URL = env.required("REDIS_URL")

CSRF_TRUSTED_ORIGINS = env.optional_list("CSRF_TRUSTED_ORIGINS")
DEBUG = False

# django.contrib.admin AUTH_USER_MODEL'ga bog'liq migratsiyaga ega, shuning uchun custom User
# (R0-04, accounts.0001) birinchi migratsiya bo'ldi. Admin ilovasi R0-12 da yoqildi (audit — faqat
# o'qish); admin URL'i va rollar bo'yicha kirish R0-05 da ulanadi.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.accounts",
    "apps.audit",
    "apps.courses",
    "apps.sections",
]

# AUTH-01: login — Hemis ID (R0-04). Loyihaning birinchi migratsiyasi shu modelda.
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    # Birinchi: keyingi har log qatorida request_id bo'ladi (R0-14).
    "config.observability.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # AUTH-04: vaqtinchalik parol bilan faqat parol almashtirish sahifasi ochiq.
    "apps.accounts.middleware.PasswordChangeRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# AUTH-03/NFR-10: Argon2id birinchi — yangi xeshlar shu bilan;
# qolganlari faqat eski xeshlarni o'qish uchun.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        # Default atributlar (username, email) bizda yo'q — Hemis ID va FIO bilan solishtiriladi.
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("hemis_id", "full_name")},
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Til va vaqt (SRS 2.3): o'zbek (lotin), Asia/Tashkent, bazada timestamptz ---
LANGUAGE_CODE = "uz"
LANGUAGES = [("uz", "O'zbekcha")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = env.optional("TIME_ZONE", "Asia/Tashkent")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Xavfsizlik (ARCHITECTURE: sessiya cookie + CSRF) ---
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    # Ochiq endpoint faqat aniq belgilanadi (CLAUDE.md 5.6).
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Caddy ortida: X-Forwarded-For dagi oxirgi N proksi (prod'da 1). Throttle shu IP bo'yicha.
    "NUM_PROXIES": env.optional_int("TRUSTED_PROXY_COUNT", 0),
}

# OpenAPI (ADR-0003): sxema faqat xodimlarga; repodagi nusxa — docs/openapi.yaml.
SPECTACULAR_SETTINGS = {
    "TITLE": "MLab API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["config.api.IsStaffRole"],
    "COMPONENT_SPLIT_REQUEST": True,
}

# SRS 7-bo'lim: joriy siyosat versiyasi (matn o'zgarsa — yangi versiya, qayta rozilik).
PRIVACY_POLICY_VERSION = "2026-11-22"
# AUTH-01: ro'yxatdan o'tish cheklovi (IP bo'yicha). Kompyuter xonasi bitta NAT ortida —
# kamida 60/soat.
AUTH_REGISTER_RATE = env.optional("AUTH_REGISTER_RATE", "60/hour")
# Havola orqali guruhga qo'shilish (I1-04): ko'rish — IP bo'yicha (sinf bitta NAT ortida — keng),
# so'rov yuborish — talaba bo'yicha.
SECTION_JOIN_PREVIEW_RATE = env.optional("SECTION_JOIN_PREVIEW_RATE", "600/hour")
SECTION_JOIN_RATE = env.optional("SECTION_JOIN_RATE", "30/hour")
# Hamma IP uchun umumiy chegara (taqsimlangan hujum, Argon2 xotira/CPU narxi).
AUTH_REGISTER_GLOBAL_RATE = env.optional("AUTH_REGISTER_GLOBAL_RATE", "300/hour")
# AUTH-02: login so'rovlari IP bo'yicha (Hemis ID + IP lockout'dan tashqari; xona bitta NAT ortida).
AUTH_LOGIN_RATE = env.optional("AUTH_LOGIN_RATE", "120/minute")
# Hamma IP uchun umumiy login chegarasi (Argon2 xotira/CPU narxi; dars boshida 30 talaba bemalol).
AUTH_LOGIN_GLOBAL_RATE = env.optional("AUTH_LOGIN_GLOBAL_RATE", "600/minute")
# AUTH-04: parol almashtirish urinishlari (foydalanuvchi bo'yicha; eski parolni taxminlashga).
AUTH_CHANGE_PASSWORD_RATE = env.optional("AUTH_CHANGE_PASSWORD_RATE", "10/hour")
# AUTH-04: tiklovchi bo'yicha (o'qituvchi bir guruhni bemalol; ommaviy tiklashga qarshi).
AUTH_RESET_PASSWORD_RATE = env.optional("AUTH_RESET_PASSWORD_RATE", "60/hour")
# AUTH-05: o'qituvchi akkauntlarini yaratish, yaratuvchi bo'yicha.
AUTH_INSTRUCTOR_CREATE_RATE = env.optional("AUTH_INSTRUCTOR_CREATE_RATE", "30/hour")
# Sessiya 12 soat (kompyuter xonasida unutilgan sessiya uzoq yashamasin).
SESSION_COOKIE_AGE = 12 * 60 * 60
# Lockout (5 xato -> 15 daqiqa) API va Django Admin login'ida bir xil ishlaydi.
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.LockoutModelBackend"]

# --- Loglar (NFR-17, R0-14): stdout'ga bir qator JSON; maskalash formatter'da ---
LOG_LEVEL = env.optional("LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "config.observability.JsonFormatter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        # Django'ning o'z handler'lari o'rniga root (JSON) ishlatiladi — qatorlar takrorlanmaydi.
        "django": {"handlers": [], "level": LOG_LEVEL, "propagate": True},
        "django.server": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
