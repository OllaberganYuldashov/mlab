"""Celery ilovasi (ADR-0001, ADR-0007; I3-06).

Sozlamalar Django settings'dan `CELERY_` prefiksi bilan.

Worker: `celery -A config.celery worker --concurrency=2` (compose — I3-18).
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("mlab")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
