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

# django.contrib.admin R0-05 da qo'shiladi: u AUTH_USER_MODEL'ga bog'liq migratsiyaga ega,
# custom User (R0-04) esa loyihaning birinchi migratsiyasi bo'lishi shart.
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
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
}
