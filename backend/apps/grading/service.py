"""Baholash navbati (I3-06; AGR-02, AGR-04, AGR-06; ADR-0007).

Oqim: `enqueue()` yozuvni yaratadi va tranzaksiya commit bo'lgach Celery vazifasini qo'yadi →
`grade()` (worker'da) yozuvni qulf ostida "egallaydi", sandbox'ni chaqiradi, natijani yozadi.

Idempotentlik: vazifa bir necha marta yetkazilsa ham (acks_late, worker o'ldi, sweeper) yozuv
faqat `queued` (yoki osilib qolgan `running`) bo'lsa egallanadi; natija faqat o'sha egallashning
`attempts` raqami mos kelsa yoziladi — ikki worker bir yozuvni ikki marta baholamaydi.

Qayta urinish faqat infratuzilma xatosida (`SandboxUnavailable`), `MAX_ATTEMPTS` gacha, eksponensial
kutish va jitter bilan (vazifada). Talaba kodi xatosi — oddiy natija (0 ball), qayta urinilmaydi.
Commit va navbatga qo'yish orasida broker yiqilsa — `requeue_stale()` (davriy) qayta qo'yadi.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.grading.models import (
    AssignmentStep,
    StudentAssignment,
    Submission,
    SubmissionStatus,
    TestFile,
    TestKind,
)
from apps.grading.sandbox import SandboxUnavailable, get_sandbox

logger = logging.getLogger("mlab.grading")

MAX_ATTEMPTS = 3
TIME_LIMIT = 10  # s: talaba kodi va har test uchun (runner ichida)
# Celery `task_time_limit` (90 s) dan uzoq "running" — worker o'lgan; qayta egallash mumkin.
STALE_RUNNING = timedelta(seconds=180)
# Shuncha vaqt "queued" turgan yozuv navbatga yetib bormagan bo'lishi mumkin (broker yiqilgan).
STALE_QUEUED = timedelta(minutes=2)


class RetryLater(Exception):
    """Infratuzilma xatosi: vazifa keyinroq qayta urinsin (yozuv `queued` ga qaytarildi)."""


def _dispatch(submission_id: int) -> None:
    from apps.grading.tasks import grade_submission

    grade_submission.delay(submission_id)


def enqueue(
    record: StudentAssignment,
    code: str,
    dispatch: Callable[[int], None] = _dispatch,
) -> Submission:
    """Yangi urinish (AGR-06: har biri alohida yozuv). Vazifa faqat commit'dan keyin qo'yiladi."""
    submission = Submission.objects.create(student_assignment=record, code=code)
    transaction.on_commit(lambda: dispatch(submission.pk))
    logger.info(
        "grading.queued",
        extra={"event": "grading.queued", "submission_id": submission.pk, **queue_depth()},
    )
    return submission


def queue_depth() -> dict[str, int]:
    """AGR-04 kuzatuvi: navbatdagi va tekshirilayotgan yozuvlar soni (qisman indeks bo'yicha)."""
    counts = Submission.objects.filter(
        status__in=[SubmissionStatus.QUEUED, SubmissionStatus.RUNNING]
    ).aggregate(
        queued=Count("pk", filter=Q(status=SubmissionStatus.QUEUED)),
        running=Count("pk", filter=Q(status=SubmissionStatus.RUNNING)),
    )
    return {"queued": counts["queued"], "running": counts["running"]}


def _claim(submission_id: int) -> Submission | None:
    now = timezone.now()
    with transaction.atomic():
        submission = (
            Submission.objects.select_for_update()
            .select_related("student_assignment__variant")
            .filter(pk=submission_id)
            .first()
        )
        if submission is None:
            return None
        stale = (
            submission.status == SubmissionStatus.RUNNING
            and submission.started_at is not None
            and submission.started_at < now - STALE_RUNNING
        )
        if submission.status != SubmissionStatus.QUEUED and not stale:
            return None
        submission.status = SubmissionStatus.RUNNING
        submission.started_at = now
        submission.attempts += 1
        submission.save(update_fields=["status", "started_at", "attempts"])
    return submission


def build_payload(submission: Submission) -> dict[str, Any]:
    """Runner kirishi: kod, variant parametrlari va barcha testlar.

    Yashirinlar ham — ular faqat sandbox'ga boradi (AGR-05).
    """
    record = submission.student_assignment
    tests = (
        TestFile.objects.filter(step__assignment_id=record.assignment_id)
        .select_related("step")
        .order_by("step__order", "kind")  # hidden < visible alifbo bo'yicha; tartib barqaror
    )
    return {
        "code": submission.code,
        "params": record.variant.params,
        "time_limit": TIME_LIMIT,
        "tests": [{"step": t.step.key, "kind": t.kind, "source": t.source} for t in tests],
    }


def compute_score(result: dict[str, Any], steps: list[tuple[str, int]]) -> int:
    """Qadam bali * o'tgan testlar ulushi (butun son, pastga yaxlitlash — float yo'q).

    Qadamda test natijasi bo'lmasa (test fayli xato) — 0. Jami 100 dan oshmaydi.
    """
    total = 0
    for key, points in steps:
        own = [t for t in result["tests"] if t.get("step") == key]
        if own:
            total += points * sum(1 for t in own if t.get("passed") is True) // len(own)
    return min(total, 100)


def _valid_result(result: dict[str, Any]) -> bool:
    tests = result.get("tests")
    return (
        result.get("status") in ("ok", "code_error")
        and isinstance(tests, list)
        and all(
            isinstance(t, dict)
            and isinstance(t.get("step"), str)
            and t.get("kind") in (TestKind.VISIBLE, TestKind.HIDDEN)
            and isinstance(t.get("passed"), bool)
            for t in tests
        )
    )


def _finish(submission: Submission, **values: Any) -> bool:
    """Faqat o'zimiz egallagan urinishni yozamiz (boshqa worker qayta egallagan bo'lsa — yo'q)."""
    updated = Submission.objects.filter(
        pk=submission.pk, status=SubmissionStatus.RUNNING, attempts=submission.attempts
    ).update(finished_at=timezone.now(), **values)
    return updated == 1


def _log(event: str, submission: Submission, started: float, **fields: Any) -> None:
    logger.info(
        event,
        extra={
            "event": event,
            "submission_id": submission.pk,
            "attempt": submission.attempts,
            "duration_ms": int((time.monotonic() - started) * 1000),
            **fields,
        },
    )


def grade(submission_id: int) -> str:
    """Bitta urinishni baholaydi. Natija: done | error | skipped. `RetryLater` — keyinroq."""
    submission = _claim(submission_id)
    if submission is None:
        logger.info(
            "grading.skipped",
            extra={"event": "grading.skipped", "submission_id": submission_id},
        )
        return "skipped"
    started = time.monotonic()
    payload = build_payload(submission)
    try:
        result = get_sandbox().run(payload)
    except SandboxUnavailable as exc:
        if submission.attempts >= MAX_ATTEMPTS:
            _finish(submission, status=SubmissionStatus.ERROR, error="sandbox_unavailable")
            logger.error(
                "grading.failed",
                extra={
                    "event": "grading.failed",
                    "submission_id": submission.pk,
                    "attempt": submission.attempts,
                    "reason": str(exc),
                },
            )
            return "error"
        Submission.objects.filter(
            pk=submission.pk, status=SubmissionStatus.RUNNING, attempts=submission.attempts
        ).update(status=SubmissionStatus.QUEUED)
        _log("grading.retry", submission, started, reason=str(exc))
        raise RetryLater(str(exc)) from exc
    if not _valid_result(result):
        # Runner `bad_input` yoki tushunarsiz javob — bizning xato; qayta urinish yordam bermaydi.
        _finish(submission, status=SubmissionStatus.ERROR, error="bad_result")
        logger.error(
            "grading.bad_result",
            extra={
                "event": "grading.bad_result",
                "submission_id": submission.pk,
                "runner_status": str(result.get("status"))[:32],
            },
        )
        return "error"
    steps = list(
        AssignmentStep.objects.filter(assignment_id=submission.student_assignment.assignment_id)
        .order_by("order")
        .values_list("key", "points")
    )
    score = compute_score(result, steps)
    if _finish(submission, status=SubmissionStatus.DONE, score=score, result=result):
        _log("grading.done", submission, started, score=score, runner_status=result["status"])
    return "done"


def requeue_stale(dispatch: Callable[[int], None] = _dispatch, limit: int = 100) -> int:
    """Navbatga yetib bormagan yoki worker o'lgani sababli osilgan yozuvlarni qayta qo'yadi.

    `grade()` idempotent — keraksiz qayta qo'yish zarar qilmaydi. Davriy (Celery beat) — I3-18.
    """
    now = timezone.now()
    ids = list(
        Submission.objects.filter(
            Q(status=SubmissionStatus.QUEUED, created_at__lt=now - STALE_QUEUED)
            | Q(status=SubmissionStatus.RUNNING, started_at__lt=now - STALE_RUNNING)
        )
        .order_by("created_at")
        .values_list("pk", flat=True)[:limit]
    )
    for pk in ids:
        dispatch(pk)
    if ids:
        logger.warning(
            "grading.requeued",
            extra={"event": "grading.requeued", "count": len(ids), **queue_depth()},
        )
    return len(ids)
