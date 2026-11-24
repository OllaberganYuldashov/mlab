"""Mavzu testi (I2-07; CNT-06): urinish boshlash, topshirish, muddati o'tganini yakunlash.

- Savollar faol bankdan tasodifiy (`secrets.SystemRandom`), variantlar tartibi ham
  aralashtiriladi va `QuizItem.order` da qotiriladi — sahifa yangilansa o'sha savollar.
- Vaqt serverda: `deadline` = boshlanish + `quiz_minutes`; topshirish `deadline + GRACE` gacha qabul
  qilinadi (tarmoq kechikishi), keyin urinish 0 ball bilan yopiladi.
- Urinishlar soni talaba qatori qulfi ostida sanaladi (parallel "Boshlash" bosishlar bitta urinish).
- To'g'ri javob topshirilgandan keyingina qaytariladi.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.courses.models import Course, Question, QuizAttempt, QuizItem, Topic

GRACE = timedelta(seconds=30)
_random = secrets.SystemRandom()


class QuizRefused(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code, self.detail = code, detail


def _finalize(attempt: QuizAttempt, at: datetime) -> None:
    """Hali topshirilmagan urinishni saqlangan javoblar bo'yicha yopadi (chaqiruvchi qulflagan)."""
    attempt.score = sum(
        1
        for item in attempt.items.select_related("question")
        if item.chosen is not None and item.order[item.chosen] == item.question.answer
    )
    attempt.submitted_at = at
    attempt.save(update_fields=["score", "submitted_at"])


def finalize_expired(now: datetime | None = None) -> int:
    """Muddati (+ GRACE) o'tgan ochiq urinishlarni yopadi.

    Keyin Celery beat'dan ham chaqiriladi (I3).
    """
    now = now or timezone.now()
    done = 0
    with transaction.atomic():
        expired = QuizAttempt.objects.select_for_update(skip_locked=True).filter(
            submitted_at__isnull=True, deadline__lt=now - GRACE
        )
        for attempt in expired:
            _finalize(attempt, now)
            done += 1
    return done


def start_attempt(student: User, course: Course, topic: Topic) -> tuple[QuizAttempt, bool]:
    """(urinish, yangimi). Ochiq urinish bo'lsa — o'sha qaytadi (idempotent)."""
    now = timezone.now()
    with transaction.atomic():
        User.objects.select_for_update(no_key=True).filter(pk=student.pk).first()
        attempts = list(
            QuizAttempt.objects.select_for_update()
            .filter(student=student, topic=topic)
            .order_by("number")
        )
        for attempt in attempts:
            if attempt.submitted_at is None:
                if attempt.deadline + GRACE >= now:
                    return attempt, False
                _finalize(attempt, now)
        if len(attempts) >= course.quiz_attempts:
            raise QuizRefused("no_attempts", "Urinishlar tugagan.")
        bank = list(Question.objects.filter(topic=topic, is_active=True).only("id", "options"))
        if not bank:
            raise QuizRefused("no_questions", "Bu mavzuda hali test savollari yo'q.")
        chosen = _random.sample(bank, min(course.quiz_questions, len(bank)))
        attempt = QuizAttempt.objects.create(
            student=student,
            topic=topic,
            number=len(attempts) + 1,
            deadline=now + timedelta(minutes=course.quiz_minutes),
            max_score=len(chosen),
        )
        items = []
        for position, question in enumerate(chosen, start=1):
            order = list(range(len(question.options)))
            _random.shuffle(order)
            items.append(
                QuizItem(attempt=attempt, question=question, position=position, order=order)
            )
        QuizItem.objects.bulk_create(items)
    return attempt, True


def submit_attempt(attempt_id: int, student: User, answers: dict[int, int]) -> QuizAttempt:
    """Javoblarni yozib, ballni hisoblaydi. Takror topshirish — o'sha natija. Kech — `time_over`."""
    now = timezone.now()
    with transaction.atomic():
        attempt = (
            QuizAttempt.objects.select_for_update().filter(pk=attempt_id, student=student).first()
        )
        if attempt is None:
            raise QuizAttempt.DoesNotExist
        if attempt.submitted_at is not None:
            return attempt
        late = now > attempt.deadline + GRACE
        if not late:
            items = {item.position: item for item in attempt.items.all()}
            for position, chosen in answers.items():
                item = items.get(position)
                if item is None or not 0 <= chosen < len(item.order):
                    raise ValueError(f"{position}-savol uchun noto'g'ri javob")
                item.chosen = chosen
            QuizItem.objects.bulk_update(list(items.values()), ["chosen"])
        _finalize(attempt, now)  # kech bo'lsa — saqlangan (bo'sh) javoblar bilan yopiladi
    if late:  # tranzaksiyadan tashqarida: yopilish bekor bo'lmasin
        raise QuizRefused("time_over", "Test vaqti tugagan — javoblar qabul qilinmadi.")
    return attempt


def attempt_payload(attempt: QuizAttempt) -> dict[str, Any]:
    items = attempt.items.select_related("question").order_by("position")
    submitted = attempt.submitted_at is not None
    questions = []
    for item in items:
        options = [item.question.options[i] for i in item.order]
        row: dict[str, Any] = {
            "position": item.position,
            "text": item.question.text,
            "options": options,
        }
        if submitted:
            answer = item.order.index(item.question.answer)
            row |= {"chosen": item.chosen, "answer": answer, "correct": item.chosen == answer}
        questions.append(row)
    return {
        "id": attempt.pk,
        "number": attempt.number,
        "deadline": attempt.deadline,
        "server_time": timezone.now(),
        "submitted_at": attempt.submitted_at,
        "score": attempt.score,
        "max_score": attempt.max_score,
        "questions": questions,
    }
