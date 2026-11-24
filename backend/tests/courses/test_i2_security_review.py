"""I2-21 security-reviewer topilmalari: regressiya testlari."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from django.test import Client
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.courses.content import ContentError, load_course
from apps.courses.models import Question, Topic
from apps.sections.models import MembershipStatus
from tests.accounts.factories import make_user
from tests.sections.factories import make_course, make_membership, make_section

pytestmark = pytest.mark.django_db


def _student_with_attempt() -> tuple[APIClient, int, Question]:
    course = make_course()
    course.quiz_questions = 1
    course.save()
    topic = Topic.objects.create(course=course, code="M01", title="T", order=1)
    q = Question.objects.create(
        topic=topic, key="a" * 64, text="S", options=["a", "b"], answer=0, position=1
    )
    m = make_membership(section=make_section(course=course), student=make_user())
    m.status = MembershipStatus.APPROVED
    m.decided_at = timezone.now()
    m.decided_by = m.section.instructor
    m.save()
    client = APIClient()
    client.force_authenticate(m.student)
    attempt = client.post("/api/course/topics/M01/quiz/attempts").json()
    return client, attempt["id"], q


@pytest.mark.parametrize("answers", [{"²": 0}, {"1" * 50: 0}, {str(i): 0 for i in range(101)}])
def test_i2_quiz_odd_answer_keys_are_400_not_500(answers: dict[str, int]) -> None:
    client, attempt_id, _ = _student_with_attempt()
    response = client.post(
        f"/api/course/quiz/attempts/{attempt_id}/submit", {"answers": answers}, format="json"
    )
    assert response.status_code == 400


def test_i2_used_question_locked_in_admin() -> None:
    _, _, question = _student_with_attempt()
    boss = make_user(role=Role.SUPER_ADMIN, direction=None, is_superuser=True)
    client = Client()
    client.force_login(boss)
    url = f"/admin/courses/question/{question.pk}/change/"
    response = client.post(
        url, {"text": "Boshqa", "options": '["x"]', "answer": "5", "is_active": ""}
    )
    assert response.status_code == 302
    question.refresh_from_db()
    assert (question.text, question.options, question.answer) == ("S", ["a", "b"], 0)
    assert question.is_active is False  # faollikni o'zgartirish mumkin


def _content(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    (root / "topics/M01-bir").mkdir(parents=True)
    (root / "course.yaml").write_text('slug: k\ntitle: K\nversion: "1"\n', encoding="utf-8")
    (root / "topics/M01-bir/meta.yaml").write_text(
        "code: M01\ntitle: Bir\norder: 1\n", encoding="utf-8"
    )
    return root


def test_i2_symlinked_content_file_rejected(tmp_path: Path) -> None:
    root = _content(tmp_path)
    secret = tmp_path / "maxfiy.md"
    secret.write_text("# Sir\n\n## Qadam\n\nMaxfiy matn\n", encoding="utf-8")
    os.symlink(secret, root / "topics/M01-bir/lecture.md")
    with pytest.raises(ContentError, match="symlink"):
        load_course(root)


def test_i2_symlinked_topic_dir_rejected(tmp_path: Path) -> None:
    root = _content(tmp_path)
    (root / "topics/M01-bir/lecture.md").write_text("# B\n\n## Q\n\nM\n", encoding="utf-8")
    outside = tmp_path / "tashqi"
    outside.mkdir()
    (outside / "meta.yaml").write_text("code: M02\ntitle: Ikki\norder: 2\n", encoding="utf-8")
    (outside / "lecture.md").write_text("# I\n\n## Q\n\nM\n", encoding="utf-8")
    os.symlink(outside, root / "topics/M02-ikki")
    with pytest.raises(ContentError, match="symlink"):
        load_course(root)


def test_i2_visual_nan_rejected(tmp_path: Path) -> None:
    root = _content(tmp_path)
    (root / "topics/M01-bir/lecture.md").write_text(
        "# B\n\n## Q\n\n```visual\nwidget: line-fit\npoints: [[.nan, 1], [2, 3]]\n```\n",
        encoding="utf-8",
    )
    with pytest.raises(ContentError, match="points"):
        load_course(root)
