"""Celery vazifalari (I3-06; AGR-04).

Mantiq `service.py` da — bu yerda faqat qayta urinish siyosati.
"""

from __future__ import annotations

import random

from celery import Task, shared_task

from apps.grading import service

BACKOFF_BASE = 5  # s
BACKOFF_CAP = 60  # s


def backoff(retries: int) -> int:
    """Eksponensial kutish + jitter: sandbox tiklanganda hamma vazifa bir vaqtda urilmasin."""
    delay: int = min(BACKOFF_CAP, BACKOFF_BASE * 2**retries)
    return delay + random.randint(0, BACKOFF_BASE)  # noqa: S311


@shared_task(bind=True, acks_late=True, max_retries=service.MAX_ATTEMPTS)
def grade_submission(self: Task[[int], str], submission_id: int) -> str:
    try:
        return service.grade(submission_id)
    except service.RetryLater as exc:
        raise self.retry(countdown=backoff(self.request.retries), exc=exc) from exc


@shared_task
def requeue_stale_submissions() -> int:
    return service.requeue_stale()
