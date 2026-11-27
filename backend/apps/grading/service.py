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
import random
import time
from collections.abc import Callable
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.grading.models import (
    AssignmentStep,
    StudentAssignment,
    Submission,
    SubmissionPolicy,
    SubmissionStatus,
    TestFile,
    TestKind,
    Understanding,
)
from apps.grading.results import step_breakdown
from apps.grading.sandbox import SandboxUnavailable, get_sandbox
from apps.sections.policy import apply_late_penalty
from apps.sections.realtime import user_event

logger = logging.getLogger("mlab.grading")

MAX_ATTEMPTS = 3
QUESTIONS_PER_ATTEMPT = 2  # INT-02
POSITIONS_BROADCAST_LIMIT = 200  # navbat bundan uzun bo'lsa, qolganlar o'rnini API'dan oladi
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


class SubmissionPending(Exception):
    """Shu topshiriqda navbatda yoki tekshirilayotgan urinish bor (bir vaqtda bittasi)."""


def enqueue(
    record: StudentAssignment,
    code: str,
    policy: str = SubmissionPolicy.ON_TIME,
    penalty_percent: int = 0,
    dispatch: Callable[[int], None] | None = None,
) -> Submission:
    """Yangi urinish (AGR-06: har biri alohida yozuv). Vazifa faqat commit'dan keyin qo'yiladi.

    Ochiq urinish bo'lsa — `SubmissionPending` (qisman unique indeks; poyga ham to'xtaydi).
    """
    try:
        with transaction.atomic():
            submission = Submission.objects.create(
                student_assignment=record,
                code=code,
                policy=policy,
                penalty_percent=penalty_percent if policy == SubmissionPolicy.LATE else 0,
            )
    except IntegrityError as exc:
        raise SubmissionPending from exc
    send = dispatch or _dispatch
    transaction.on_commit(lambda: send(submission.pk))
    notify(submission, record.student_id)
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


def position(submission: Submission) -> int:
    """Navbatdagi o'rin: 1 — keyingisi; 0 — tekshirilmoqda yoki tugagan (FIFO, created_at)."""
    if submission.status != SubmissionStatus.QUEUED:
        return 0
    ahead = Submission.objects.filter(
        status=SubmissionStatus.QUEUED, created_at__lt=submission.created_at
    ).count()
    return ahead + 1


def status_payload(submission: Submission, place: int | None = None) -> dict[str, Any]:
    """WebSocket va API uchun umumiy shakl (yashirin test natijasi bu yerda yo'q)."""
    return {
        "id": submission.pk,
        "status": submission.status,
        "position": position(submission) if place is None else place,
        "policy": submission.policy,
        "score": submission.score,
        "final_score": (None if submission.final_score is None else str(submission.final_score)),
        "understanding": submission.understanding,
    }


def notify(submission: Submission, student_id: int) -> None:
    user_event(student_id, {"type": "submission.status", **status_payload(submission)})


def _notify_by_id(submission_id: int) -> None:
    submission = (
        Submission.objects.select_related("student_assignment").filter(pk=submission_id).first()
    )
    if submission is not None:
        notify(submission, submission.student_assignment.student_id)


def broadcast_positions() -> None:
    """Navbat siljidi: navbatdagilarga yangi o'rin (bitta so'rov, ko'pi bilan LIMIT ta xabar)."""
    queued = Submission.objects.filter(status=SubmissionStatus.QUEUED).order_by("created_at")
    rows = queued.select_related("student_assignment")[:POSITIONS_BROADCAST_LIMIT]
    for place, submission in enumerate(rows, start=1):
        user_event(
            submission.student_assignment.student_id,
            {"type": "submission.status", **status_payload(submission, place)},
        )


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
    Hisob `results.step_breakdown` bilan bir xil (talaba ko'rgan qadamlar yig'indisi = ball).
    """
    rows = step_breakdown(result, [(key, "", points) for key, points in steps])
    total: int = sum(row["score"] for row in rows)
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
    if submission is not None:
        _notify_by_id(submission.pk)
        broadcast_positions()
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
            _notify_by_id(submission.pk)
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
        _notify_by_id(submission.pk)
        _log("grading.retry", submission, started, reason=str(exc))
        raise RetryLater(str(exc)) from exc
    if not _valid_result(result):
        # Runner `bad_input` yoki tushunarsiz javob — bizning xato; qayta urinish yordam bermaydi.
        _finish(submission, status=SubmissionStatus.ERROR, error="bad_result")
        _notify_by_id(submission.pk)
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
    # ACC-07: kechikkan bo'lsa jarima (topshirish paytidagi foiz); mashq — ball bor, rasmiy emas.
    final = apply_late_penalty(score, submission.penalty_percent)
    done: dict[str, Any] = {
        "status": SubmissionStatus.DONE,
        "score": score,
        "final_score": final,
        "result": result,
    }
    pool = submission.student_assignment.variant.questions
    if len(pool) >= QUESTIONS_PER_ATTEMPT:
        # INT-02: har urinishga 2 ta savol (urinish raqamidan barqaror tanlov, javoblar serverda).
        rng = random.Random(submission.pk)  # noqa: S311 — xavfsizlik emas, xilma-xillik
        done["understanding"] = Understanding.PENDING
        done["questions"] = sorted(rng.sample(range(len(pool)), QUESTIONS_PER_ATTEMPT))
    if _finish(submission, **done):
        _notify_by_id(submission.pk)
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


class NotAwaitingAnswers(Exception):
    """Urinish baholanmagan yoki savollarga allaqachon javob berilgan."""


def halve_score(score: Decimal) -> Decimal:
    """INT-02: noto'g'ri javobda yakuniy ball yarmiga kamayadi (2 xona, 0.005 yuqoriga)."""
    return (score / 2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def answer(submission_id: int, student_id: int, answers: list[int]) -> Submission:
    """INT-02: tushunish savollariga javob (bir marta). Biri noto'g'ri — ball 50 bilan cheklanadi.

    Javobsiz urinish rasmiy hisoblanmaydi (eng yuqori ball, challenge, daraja qoidasi) — `results`.
    `ValueError` — javoblar shakli noto'g'ri; `Submission.DoesNotExist` — begona yoki yo'q.
    """
    with transaction.atomic():
        submission = (
            Submission.objects.select_for_update(of=("self",))
            .select_related("student_assignment__variant")
            .get(pk=submission_id, student_assignment__student_id=student_id)
        )
        if (
            submission.status != SubmissionStatus.DONE
            or submission.understanding != Understanding.PENDING
        ):
            raise NotAwaitingAnswers
        pool = submission.student_assignment.variant.questions
        chosen = [pool[i] for i in submission.questions or []]
        if len(answers) != len(chosen) or not all(
            type(a) is int and 0 <= a < len(q["options"])
            for a, q in zip(answers, chosen, strict=True)
        ):
            raise ValueError("javoblar")
        correct = all(a == q["answer"] for a, q in zip(answers, chosen, strict=True))
        submission.understanding = Understanding.PASSED if correct else Understanding.FAILED
        submission.answers = answers
        submission.answered_at = timezone.now()
        fields = ["understanding", "answers", "answered_at"]
        if not correct and submission.final_score is not None:
            submission.final_score = halve_score(submission.final_score)
            fields.append("final_score")
        submission.save(update_fields=fields)
    notify(submission, student_id)
    logger.info(
        "grading.understanding",
        extra={
            "event": "grading.understanding",
            "submission_id": submission.pk,
            "passed": correct,
        },
    )
    return submission
