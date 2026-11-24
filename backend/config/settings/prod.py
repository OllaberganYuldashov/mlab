"""Prod sozlamalari: universitet serveri, Caddy ortida (HTTPS Caddy'da tugaydi)."""

from django.core.exceptions import ImproperlyConfigured

from config import env
from config.settings.base import *  # noqa: F403
from config.settings.base import ALLOWED_HOSTS, SANDBOX_BACKEND, SECRET_KEY

env.validate_production(
    secret_key=SECRET_KEY,
    allowed_hosts=ALLOWED_HOSTS,
    trusted_proxy_count=env.optional_int("TRUSTED_PROXY_COUNT", 0),
)

if SANDBOX_BACKEND == "fake":  # soxta sandbox baho qo'ymasin (AGR-03)
    raise ImproperlyConfigured("SANDBOX_BACKEND=fake prod'da taqiqlangan")

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.boolean("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_PRELOAD = False
