"""CNT-07 (I2-09): super admin kontentni Django Admin'da ko'radi va tuzatadi (audit bilan)."""

from __future__ import annotations

import pytest
from django.test import Client

from apps.accounts.models import Role, User
from apps.audit.models import Action, AuditLog
from apps.courses.models import Lecture, LectureImage, LectureStep, Question, Topic
from tests.accounts.factories import make_user
from tests.sections.factories import make_course

pytestmark = pytest.mark.django_db


def _user(role: Role) -> User:
    if role == Role.STUDENT:
        return make_user(role=role)
    return make_user(role=role, direction=None, is_superuser=role == Role.SUPER_ADMIN)


@pytest.fixture
def content() -> dict[str, object]:
    course = make_course()
    topic = Topic.objects.create(course=course, code="M01", title="Bir", order=1)
    lecture = Lecture.objects.create(topic=topic, title="Bir")
    step = LectureStep.objects.create(lecture=lecture, order=1, title="Kirish", body="Xato matnn.")
    question = Question.objects.create(
        topic=topic, key="a" * 64, text="Savol?", options=["a", "b"], answer=0, position=1
    )
    image = LectureImage.objects.create(
        topic=topic,
        name="x.png",
        content_type="image/png",
        sha256="b" * 64,
        size=8,
        data=b"\x89PNG\r\n\x1a\n",
    )
    return {"step": step, "question": question, "image": image, "topic": topic}


def _client(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def test_cnt_07_super_admin_fixes_step_text_and_it_is_audited(content: dict[str, object]) -> None:
    step = content["step"]
    assert isinstance(step, LectureStep)
    boss = _user(Role.SUPER_ADMIN)
    url = f"/admin/courses/lecturestep/{step.pk}/change/"
    page = _client(boss).get(url)
    assert page.status_code == 200
    assert "import_content" in page.content.decode()  # ogohlantirish: fayl — yagona manba
    response = _client(boss).post(url, {"title": "Kirish", "body": "To'g'ri matn."})
    assert response.status_code == 302
    step.refresh_from_db()
    assert step.body == "To'g'ri matn."
    log = AuditLog.objects.get(action=Action.CONTENT_EDITED)
    assert log.actor == boss
    assert log.before == {"body": "Xato matnn."}
    assert log.after == {"body": "To'g'ri matn."}


def test_cnt_07_super_admin_fixes_question(content: dict[str, object]) -> None:
    question = content["question"]
    assert isinstance(question, Question)
    url = f"/admin/courses/question/{question.pk}/change/"
    response = _client(_user(Role.SUPER_ADMIN)).post(
        url, {"text": "Savol to'g'ri?", "options": '["a", "b"]', "answer": "0", "is_active": "on"}
    )
    assert response.status_code == 302
    question.refresh_from_db()
    assert question.text == "Savol to'g'ri?"
    assert AuditLog.objects.filter(action=Action.CONTENT_EDITED).count() == 1


def test_cnt_07_unchanged_save_is_not_audited(content: dict[str, object]) -> None:
    step = content["step"]
    assert isinstance(step, LectureStep)
    url = f"/admin/courses/lecturestep/{step.pk}/change/"
    _client(_user(Role.SUPER_ADMIN)).post(url, {"title": "Kirish", "body": "Xato matnn."})
    assert not AuditLog.objects.filter(action=Action.CONTENT_EDITED).exists()


def test_cnt_07_question_answer_out_of_range_rejected(content: dict[str, object]) -> None:
    question = content["question"]
    assert isinstance(question, Question)
    url = f"/admin/courses/question/{question.pk}/change/"
    response = _client(_user(Role.SUPER_ADMIN)).post(
        url, {"text": "Savol?", "options": '["a", "b"]', "answer": "5", "is_active": "on"}
    )
    assert response.status_code == 200  # forma xatosi
    question.refresh_from_db()
    assert question.answer == 0


def test_cnt_07_admin_can_view_but_not_edit(content: dict[str, object]) -> None:
    step = content["step"]
    assert isinstance(step, LectureStep)
    client = _client(_user(Role.ADMIN))
    assert client.get("/admin/courses/lecturestep/").status_code == 200
    url = f"/admin/courses/lecturestep/{step.pk}/change/"
    client.post(url, {"title": "Kirish", "body": "Buzildi"})
    step.refresh_from_db()
    assert step.body == "Xato matnn."


@pytest.mark.parametrize("role", [Role.INSTRUCTOR, Role.STUDENT])
def test_cnt_07_non_staff_have_no_access(content: dict[str, object], role: Role) -> None:
    response = _client(_user(role)).get("/admin/courses/lecturestep/")
    assert response.status_code == 302  # admin login sahifasiga


def test_cnt_07_nothing_added_or_deleted_in_admin(content: dict[str, object]) -> None:
    client = _client(_user(Role.SUPER_ADMIN))
    for model in ("course", "topic", "lecturestep", "question", "lectureimage"):
        assert client.get(f"/admin/courses/{model}/add/").status_code == 403, model
    topic = content["topic"]
    assert isinstance(topic, Topic)
    assert client.get(f"/admin/courses/topic/{topic.pk}/delete/").status_code == 403


def test_cnt_07_image_bytes_not_rendered(content: dict[str, object]) -> None:
    image = content["image"]
    assert isinstance(image, LectureImage)
    page = _client(_user(Role.SUPER_ADMIN)).get(f"/admin/courses/lectureimage/{image.pk}/change/")
    assert page.status_code == 200
    assert "x.png" in page.content.decode()
    assert "data" not in [f.name for f in page.context["adminform"].form]
