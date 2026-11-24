"""CNT-06 (I2-07): mavzu testi — tasodifiy savollar, vaqt va urinishlar (kurs darajasida)."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.content import ContentError, load_course
from apps.courses.models import Course, Question, QuizAttempt, Topic
from apps.courses.quiz import finalize_expired
from apps.sections.models import MembershipStatus
from tests.accounts.factories import make_user
from tests.sections.factories import make_course, make_membership, make_section

pytestmark = pytest.mark.django_db

START = "/api/course/topics/M01/quiz/attempts"


def _bank(course: Course, n: int = 5) -> Topic:
    topic = Topic.objects.create(course=course, code="M01", title="T", order=1)
    for i in range(n):
        Question.objects.create(
            topic=topic,
            key=f"{i:064x}",
            text=f"Savol {i}",
            options=[f"to'g'ri {i}", f"xato {i}", f"yana xato {i}"],
            answer=0,
            position=i + 1,
        )
    return topic


def _student(course: Course) -> User:
    membership = make_membership(section=make_section(course=course), student=make_user())
    membership.status = MembershipStatus.APPROVED
    membership.decided_at = timezone.now()
    membership.decided_by = membership.section.instructor
    membership.save()
    return membership.student


@pytest.fixture
def course() -> Course:
    course = make_course()
    course.quiz_questions, course.quiz_minutes, course.quiz_attempts = 3, 10, 2
    course.save()
    _bank(course)
    return course


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _correct_answers(attempt: dict[str, Any]) -> dict[str, int]:
    answers = {}
    for q in attempt["questions"]:
        answers[str(q["position"])] = next(
            i for i, text in enumerate(q["options"]) if text.startswith("to'g'ri")
        )
    return answers


def test_cnt_06_start_attempt_random_questions_without_answers(course: Course) -> None:
    client = _client(_student(course))
    response = client.post(START)
    assert response.status_code == 201
    attempt = response.json()
    assert attempt["number"] == 1
    assert len(attempt["questions"]) == 3
    assert [q["position"] for q in attempt["questions"]] == [1, 2, 3]
    assert all(len(q["options"]) == 3 for q in attempt["questions"])
    assert "answer" not in str(attempt).lower().replace("answers", "")
    assert b"to'g'ri" in response.content  # variant matni bor, lekin qaysi to'g'riligi yo'q
    deadline = datetime.fromisoformat(attempt["deadline"])
    assert timedelta(minutes=9) < deadline - timezone.now() <= timedelta(minutes=10)


def test_cnt_06_start_again_returns_active_attempt(course: Course) -> None:
    client = _client(_student(course))
    first = client.post(START).json()
    again = client.post(START)
    assert again.status_code == 200
    assert again.json()["id"] == first["id"]
    assert QuizAttempt.objects.count() == 1


def test_cnt_06_submit_scores_and_reveals_answers(course: Course) -> None:
    client = _client(_student(course))
    attempt = client.post(START).json()
    answers = _correct_answers(attempt)
    first_pos = "1"
    answers[first_pos] = (answers[first_pos] + 1) % 3  # bittasi xato
    response = client.post(
        f"/api/course/quiz/attempts/{attempt['id']}/submit", {"answers": answers}, format="json"
    )
    assert response.status_code == 200
    result = response.json()
    assert result["score"] == 2
    assert result["max_score"] == 3
    item = result["questions"][0]
    assert item["chosen"] == answers[first_pos]
    assert item["correct"] is False
    assert item["options"][item["answer"]].startswith("to'g'ri")

    # Takroriy topshirish — o'sha natija, ball o'zgarmaydi.
    again = client.post(
        f"/api/course/quiz/attempts/{attempt['id']}/submit", {"answers": {}}, format="json"
    )
    assert again.status_code == 200
    assert again.json()["score"] == 2


def test_cnt_06_attempt_limit(course: Course) -> None:
    client = _client(_student(course))
    for _ in range(2):
        attempt = client.post(START).json()
        client.post(
            f"/api/course/quiz/attempts/{attempt['id']}/submit", {"answers": {}}, format="json"
        )
    response = client.post(START)
    assert response.status_code == 409
    assert response.json()["code"] == "no_attempts"
    summary = client.get("/api/course/topics/M01/quiz").json()
    assert summary["used_attempts"] == 2
    assert summary["settings"] == {"questions": 3, "minutes": 10, "attempts": 2}
    assert [a["score"] for a in summary["attempts"]] == [0, 0]


def test_cnt_06_late_submit_rejected_and_expired_attempt_finalized(course: Course) -> None:
    client = _client(_student(course))
    attempt = client.post(START).json()
    QuizAttempt.objects.filter(pk=attempt["id"]).update(
        deadline=timezone.now() - timedelta(minutes=1)
    )
    response = client.post(
        f"/api/course/quiz/attempts/{attempt['id']}/submit",
        {"answers": _correct_answers(attempt)},
        format="json",
    )
    assert response.status_code == 409
    assert response.json()["code"] == "time_over"
    stored = QuizAttempt.objects.get(pk=attempt["id"])
    assert stored.submitted_at is not None
    assert stored.score == 0
    # Yangi urinish boshlash mumkin (muddati o'tgan urinish hisoblangan).
    second = client.post(START)
    assert second.status_code == 201
    assert second.json()["number"] == 2


def test_cnt_06_small_grace_period_accepts_submit(course: Course) -> None:
    client = _client(_student(course))
    attempt = client.post(START).json()
    QuizAttempt.objects.filter(pk=attempt["id"]).update(
        deadline=timezone.now() - timedelta(seconds=5)
    )
    response = client.post(
        f"/api/course/quiz/attempts/{attempt['id']}/submit",
        {"answers": _correct_answers(attempt)},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["score"] == 3


def test_cnt_06_finalize_expired_helper(course: Course) -> None:
    client = _client(_student(course))
    attempt = client.post(START).json()
    QuizAttempt.objects.filter(pk=attempt["id"]).update(
        deadline=timezone.now() - timedelta(minutes=5)
    )
    assert finalize_expired() == 1
    assert QuizAttempt.objects.get(pk=attempt["id"]).score == 0


@pytest.mark.parametrize(
    "answers",
    [{"1": 9}, {"1": -1}, {"x": 0}, {"1": "0"}, ["0"], {"99": 0}],
)
def test_cnt_06_bad_answers_rejected(course: Course, answers: Any) -> None:
    client = _client(_student(course))
    attempt = client.post(START).json()
    response = client.post(
        f"/api/course/quiz/attempts/{attempt['id']}/submit", {"answers": answers}, format="json"
    )
    assert response.status_code == 400
    assert QuizAttempt.objects.get(pk=attempt["id"]).submitted_at is None


def test_cnt_06_other_students_attempt_is_404(course: Course) -> None:
    owner = _client(_student(course))
    attempt = owner.post(START).json()
    stranger = _client(_student(course))
    assert stranger.get(f"/api/course/quiz/attempts/{attempt['id']}").status_code == 404
    url = f"/api/course/quiz/attempts/{attempt['id']}/submit"
    assert stranger.post(url, {"answers": {}}, format="json").status_code == 404


def test_cnt_06_get_attempt_hides_answers_until_submitted(course: Course) -> None:
    client = _client(_student(course))
    attempt = client.post(START).json()
    open_view = client.get(f"/api/course/quiz/attempts/{attempt['id']}").json()
    assert "answer" not in open_view["questions"][0]
    assert open_view["submitted_at"] is None
    client.post(f"/api/course/quiz/attempts/{attempt['id']}/submit", {"answers": {}}, format="json")
    done = client.get(f"/api/course/quiz/attempts/{attempt['id']}").json()
    assert "answer" in done["questions"][0]


def test_cnt_06_non_members_and_staff_forbidden(course: Course) -> None:
    assert _client(make_user()).post(START).status_code == 403
    instructor = make_section(course=course).instructor
    assert _client(instructor).post(START).status_code == 403


def test_cnt_06_empty_bank_and_unknown_topic(course: Course) -> None:
    client = _client(_student(course))
    Question.objects.update(is_active=False)
    response = client.post(START)
    assert response.status_code == 409
    assert response.json()["code"] == "no_questions"
    assert client.post("/api/course/topics/M09/quiz/attempts").status_code == 404


def test_cnt_06_fewer_questions_than_setting_uses_all(course: Course) -> None:
    Question.objects.filter(position__gt=2).update(is_active=False)
    attempt = _client(_student(course)).post(START).json()
    assert len(attempt["questions"]) == 2


def test_cnt_06_archived_question_kept_in_old_attempt(course: Course) -> None:
    client = _client(_student(course))
    attempt = client.post(START).json()
    client.post(f"/api/course/quiz/attempts/{attempt['id']}/submit", {"answers": {}}, format="json")
    Question.objects.update(is_active=False)
    result = client.get(f"/api/course/quiz/attempts/{attempt['id']}").json()
    assert len(result["questions"]) == 3


@pytest.mark.django_db(transaction=True)
def test_cnt_06_parallel_start_creates_one_attempt() -> None:
    course = make_course()
    course.quiz_attempts = 1
    course.save()
    _bank(course)
    student = _student(course)
    codes: list[int] = []

    def start() -> None:
        try:
            codes.append(_client(student).post(START).status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=start) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert QuizAttempt.objects.count() == 1
    assert codes.count(201) == 1
    assert set(codes) <= {200, 201}


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("quiz_questions: 0", "1..50"),
        ("quiz_minutes: 500", "1..180"),
        ("quiz_attempts: 0", "1..10"),
    ],
)
def test_cnt_06_course_defaults_validated(tmp_path: Path, line: str, message: str) -> None:
    root = tmp_path / "content"
    root.mkdir()
    (root / "course.yaml").write_text(
        f'slug: k\ntitle: K\nversion: "1"\ndefaults:\n  {line}\n', encoding="utf-8"
    )
    with pytest.raises(ContentError, match=message):
        load_course(root)
