"""Lokal ishlab chiqish. Qiymatlar .env.example asosida (soxta)."""

from config import env
from config.settings.base import *  # noqa: F403

DEBUG = env.boolean("DEBUG", default=False)
