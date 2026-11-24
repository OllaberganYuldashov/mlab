"""Test sozlamalari (pytest).

Faqat testlarda soxta default qiymatlar beriladi, shunda `uv run pytest` qo'shimcha
sozlashsiz ishlaydi.
Baza va Redis — haqiqiy lokal servislar (bulutda setup skript, kompyuterda compose.yaml).
Fail-fast xatti-harakati dev/prod sozlamalarida tekshiriladi:
tests/test_nfr_16_settings_fail_fast.py.
"""

import os

for _name, _value in {
    "SECRET_KEY": "test-only-not-a-secret",
    "DATABASE_URL": "postgres://mlab:mlab@localhost:5432/mlab",
    "REDIS_URL": "redis://localhost:6379/15",
    "ALLOWED_HOSTS": "testserver,localhost",
}.items():
    os.environ.setdefault(_name, _value)

from config.settings.base import *  # noqa: E402, F403

DEBUG = False
# Testlar tezroq ishlashi uchun; Argon2 o'z testida alohida tekshiriladi (R0-04).
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Avtobaholovchi testlarda: soxta sandbox (talaba kodi bajarilmaydi), xotiradagi broker.
SANDBOX_BACKEND = "fake"
CELERY_BROKER_URL = "memory://"
