# Celery ilovasi Django bilan birga yuklanadi: `.delay()` shu ilova sozlamalari (broker)
# bilan ishlaydi.
from config.celery import app as celery_app

__all__ = ("celery_app",)
