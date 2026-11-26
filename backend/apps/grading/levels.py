"""Moslashuvchan daraja (I3-10; ADP-01).

Qoida (sof funksiya `choose_level`): ko'rsatkich 0..100 — mavjud signallarning o'rtachasi:
- shu mavzu testining eng yaxshi natijasi (foiz; topshirilgan urinishlar),
- oldingi topshiriqlar (kodi kichikroq) rasmiy eng yuqori ballarining o'rtachasi.
Signal yo'q (birinchi topshiriq, test yechilmagan) — `basic`. Chegaralar kurs sozlamasida
(`course.yaml` `defaults.level_medium_from` = 60, `level_advanced_from` = 85).
Hisob `Decimal` da (float yo'q); chegarada (aynan 60 yoki 85) yuqori daraja.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Max

from apps.accounts.models import User
from apps.courses.models import QuizAttempt
from apps.grading.models import (
    Assignment,
    Level,
    Submission,
    SubmissionPolicy,
    SubmissionStatus,
)


def choose_level(
    quiz_percent: Decimal | None,
    prior_scores: list[Decimal],
    medium_from: int,
    advanced_from: int,
) -> Level:
    signals: list[Decimal] = []
    if quiz_percent is not None:
        signals.append(quiz_percent)
    if prior_scores:
        signals.append(sum(prior_scores, Decimal(0)) / len(prior_scores))
    if not signals:
        return Level.BASIC
    indicator = sum(signals, Decimal(0)) / len(signals)
    if indicator >= advanced_from:
        return Level.ADVANCED
    if indicator >= medium_from:
        return Level.MEDIUM
    return Level.BASIC


def quiz_percent(student: User, assignment: Assignment) -> Decimal | None:
    best = QuizAttempt.objects.filter(
        student=student,
        topic__course_id=assignment.course_id,
        topic__code=assignment.topic_code,
        submitted_at__isnull=False,
        score__isnull=False,
        max_score__gt=0,
    ).values_list("score", "max_score")
    rows = list(best)
    if not rows:
        return None
    return max(Decimal(score or 0) * 100 / Decimal(maximum) for score, maximum in rows)


def prior_scores(student: User, assignment: Assignment) -> list[Decimal]:
    """Oldingi topshiriqlar (shu kurs, kodi kichik) bo'yicha rasmiy eng yuqori ball (bittadan)."""
    rows = (
        Submission.objects.filter(
            student_assignment__student=student,
            student_assignment__assignment__course_id=assignment.course_id,
            student_assignment__assignment__code__lt=assignment.code,
            status=SubmissionStatus.DONE,
        )
        .exclude(policy=SubmissionPolicy.PRACTICE)
        .values("student_assignment_id")
        .annotate(best=Max("final_score"))
        .values_list("best", flat=True)
    )
    return [Decimal(best) for best in rows if best is not None]


def rule_level(student: User, assignment: Assignment) -> Level:
    course = assignment.course
    return choose_level(
        quiz_percent(student, assignment),
        prior_scores(student, assignment),
        course.level_medium_from,
        course.level_advanced_from,
    )
