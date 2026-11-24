"""CNT-02, ACC-01, SEC-05 (I2-03): mavzular ro'yxati, ma'ruza qadamlari va rasmlar API'si."""

from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.courses.models import Course, Lecture, LectureImage, LectureStep, Question, Topic
from apps.sections.models import AccessWindow, Membership, MembershipStatus, WindowMode
from tests.accounts.factories import make_user
from tests.sections.factories import make_course, make_instructor, make_membership, make_section

pytestmark = pytest.mark.django_db

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32
SHA = hashlib.sha256(PNG).hexdigest()


@pytest.fixture
def course() -> Course:
    course = make_course()
    for n in (1, 2):
        topic = Topic.objects.create(course=course, code=f"M0{n}", title=f"Mavzu {n}", order=n)
        lecture = Lecture.objects.create(topic=topic, title=f"Ma'ruza {n}")
        LectureStep.objects.create(
            lecture=lecture, order=1, title="Kirish", body="Rasm: ![Chiziq](images/line.png)"
        )
        LectureStep.objects.create(
            lecture=lecture,
            order=2,
            title="Savol",
            body="",
            question={"question": "?", "options": ["a", "b"], "answer": 0, "explain": ""},
        )
    m01 = Topic.objects.get(code="M01")
    LectureImage.objects.create(
        topic=m01, name="line.png", content_type="image/png", sha256=SHA, size=len(PNG), data=PNG
    )
    Question.objects.create(
        topic=m01, key="0" * 64, text="Q", options=["a", "b"], answer=1, position=1
    )
    Question.objects.create(
        topic=m01,
        key="1" * 64,
        text="Old",
        options=["a", "b"],
        answer=0,
        position=2,
        is_active=False,
    )
    return course


def _client(user: User | None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def _student(course: Course, status: str = MembershipStatus.APPROVED) -> tuple[User, Membership]:
    membership = make_membership(section=make_section(course=course), student=make_user())
    if status == MembershipStatus.APPROVED:
        membership.status = status
        membership.decided_at = timezone.now()
        membership.decided_by = membership.section.instructor
        membership.save()
    return membership.student, membership


def test_cnt_02_student_sees_topics_with_lab_state(course: Course) -> None:
    student, membership = _student(course)
    now = timezone.now()
    AccessWindow.objects.create(
        section=membership.section,
        topic=Topic.objects.get(code="M02"),
        mode=WindowMode.OPEN_NOW,
        opens_at=now - timedelta(minutes=5),
    )
    body = _client(student).get("/api/course/topics").json()
    assert body["course"] == {"slug": course.slug, "title": course.title}
    m01, m02 = body["topics"]
    assert m01 == {
        "code": "M01",
        "title": "Mavzu 1",
        "order": 1,
        "steps": 2,
        "questions": 1,
        "lab": {"status": "closed", "opens_at": None, "closes_at": None},
    }
    assert m02["lab"]["status"] == "open"


def test_cnt_02_staff_topics_have_no_lab_state(course: Course) -> None:
    instructor = make_section(course=course).instructor
    body = _client(instructor).get("/api/course/topics").json()
    assert [t["lab"] for t in body["topics"]] == [None, None]


def test_cnt_02_lecture_steps_with_image_urls_and_question(course: Course) -> None:
    student, _ = _student(course)
    body = _client(student).get("/api/course/topics/M01/lecture").json()
    assert body["topic"] == {"code": "M01", "title": "Mavzu 1"}
    assert body["title"] == "Ma'ruza 1"
    assert body["prev"] is None
    assert body["next"] == "M02"
    first, second = body["steps"]
    assert first["body"] == f"Rasm: ![Chiziq](/api/course/images/{SHA})"
    assert first["question"] is None
    assert second["question"]["options"] == ["a", "b"]
    # M02 da rasm fayli yo'q — havola o'zgarmaydi (frontend uni ko'rsatmaydi).
    m02 = _client(student).get("/api/course/topics/M02/lecture").json()
    assert m02["steps"][0]["body"] == "Rasm: ![Chiziq](images/line.png)"
    assert m02["prev"] == "M01"
    assert m02["next"] is None


def test_cnt_02_image_served_with_immutable_cache(course: Course) -> None:
    student, _ = _student(course)
    response = _client(student).get(f"/api/course/images/{SHA}")
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response.content == PNG
    assert "immutable" in response["Cache-Control"]
    assert "private" in response["Cache-Control"]
    assert response["X-Content-Type-Options"] == "nosniff"


def test_cnt_02_unknown_topic_or_image_404(course: Course) -> None:
    student, _ = _student(course)
    client = _client(student)
    assert client.get("/api/course/topics/M09/lecture").status_code == 404
    assert client.get(f"/api/course/images/{'a' * 64}").status_code == 404
    assert client.get("/api/course/images/not-a-hash").status_code == 404


@pytest.mark.parametrize("who", ["anonymous", "outsider", "pending", "instructor_without_section"])
def test_cnt_02_non_members_cannot_read(course: Course, who: str) -> None:
    user: User | None
    if who == "anonymous":
        user = None
    elif who == "outsider":
        user = make_user()
    elif who == "pending":
        user, _ = _student(course, status=MembershipStatus.PENDING)
    else:
        user = make_instructor()
    client = _client(user)
    assert client.get("/api/course/topics").status_code in (401, 403)
    assert client.get("/api/course/topics/M01/lecture").status_code in (401, 403)
    assert client.get(f"/api/course/images/{SHA}").status_code in (401, 403, 404)


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPER_ADMIN])
def test_cnt_02_admins_can_read(course: Course, role: Role) -> None:
    client = _client(make_user(role=role, direction=None, is_superuser=role == Role.SUPER_ADMIN))
    assert client.get("/api/course/topics").status_code == 200
    assert client.get("/api/course/topics/M01/lecture").status_code == 200


def test_cnt_02_correct_quiz_bank_answers_never_exposed(course: Course) -> None:
    student, _ = _student(course)
    client = _client(student)
    text = (
        client.get("/api/course/topics").content
        + client.get("/api/course/topics/M01/lecture").content
    )
    assert b'"Old"' not in text
    assert b'"Q"' not in text


def test_cnt_02_query_count_independent_of_steps(course: Course) -> None:
    student, _ = _student(course)
    client = _client(student)

    def count(url: str) -> int:
        with CaptureQueriesContext(connection) as ctx:
            assert client.get(url).status_code == 200
        return len(ctx.captured_queries)

    lecture_before = count("/api/course/topics/M01/lecture")
    topics_before = count("/api/course/topics")
    lecture = Lecture.objects.get(topic__code="M01")
    for n in range(3, 9):
        LectureStep.objects.create(lecture=lecture, order=n, title=f"Q{n}", body="x")
    for n in range(3, 7):
        Topic.objects.create(course=course, code=f"M0{n}", title=f"T{n}", order=n)
    assert count("/api/course/topics/M01/lecture") == lecture_before
    assert count("/api/course/topics") == topics_before
