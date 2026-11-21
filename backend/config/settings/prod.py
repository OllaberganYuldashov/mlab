"""Prod sozlamalari: universitet serveri, Caddy ortida (HTTPS Caddy'da tugaydi)."""

from config import env
from config.settings.base import *  # noqa: F403
from config.settings.base import ALLOWED_HOSTS, SECRET_KEY

env.validate_production(secret_key=SECRET_KEY, allowed_hosts=ALLOWED_HOSTS)

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.boolean("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_PRELOAD = False
