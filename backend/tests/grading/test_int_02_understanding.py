"""INT-02 (I3-13): topshirgandan keyin 2 ta tushunish savoli; noto'g'ri javobda ball yarmiga."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from django.core.cache import cache

from apps.courses.content import ContentError
from apps.courses.models import Topic
from apps.grading import results, service
from apps.grading.content import import_labs, load_labs
from apps.grading.models import Assignment, Submission, Understanding, Variant
from apps.grading.sandbox import fake
from apps.sections.models import Membership
from tests.grading.test_agr_02_submit_api import URL, _peer, _post
from tests.grading.test_agr_07_assignment_import import content  # noqa: F401  (fixture)
from tests.labs.test_lab_05_autosave import _approved, _client
from tests.sections.factories import make_instructor

pytestmark = pytest.mark.django_db

QUESTIONS = """questions:
  - text: "`clean` nimani saqlaydi?"
    options: ["Chegaradagi qatorlar", "Barcha qatorlar", "Faqat NaN"]
    answer: 0
  - text: "`removed` qanday hisoblanadi?"
    options: ["len(clean)", "len(df) - len(clean)"]
    answer: 1
  - text: "Indeks nega qayta tiklanadi?"
    options: ["0 dan ketma-ket bo'lishi uchun", "Tezlik uchun"]
    answer: 0
"""


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    cache.clear()
    fake.responses.clear()
    yield
    cache.clear()


@pytest.fixture
def membership(content: Path) -> Membership:  # noqa: F811
    for file in (content / "labs/A01-pandas/variants").glob("*.yaml"):
        file.write_text(file.read_text(encoding="utf-8") + QUESTIONS, encoding="utf-8")
    membership = _approved()
    Topic.objects.create(course=membership.section.course, code="M02", title="T2", order=2)
    import_labs(content, membership.section.course)
    Assignment.objects.update(topic_code="M01")
    return membership


def _graded(membership: Membership) -> dict[str, Any]:
    sid = _post(membership).json()["id"]
    service.grade(sid)
    return dict(_client(membership.student).get(f"/api/submissions/{sid}").json())


def _correct(sid: int) -> list[int]:
    submission = Submission.objects.select_related("student_assignment__variant").get(pk=sid)
    pool = submission.student_assignment.variant.questions
    return [pool[i]["answer"] for i in submission.questions or []]


def _answer(membership: Membership, sid: int, answers: Any) -> Any:
    return _client(membership.student).post(
        f"/api/submissions/{sid}/answers", {"answers": answers}, format="json"
    )


def test_int_02_import_validates_questions(content: Path) -> None:  # noqa: F811
    variant = content / "labs/A01-pandas/variants/basic-1.yaml"
    base = variant.read_text(encoding="utf-8")
    variant.write_text(base + QUESTIONS, encoding="utf-8")
    lab = load_labs(content)[0]
    assert len(lab.questions[("basic", 1)]) == 3
    assert ("basic", 2) not in lab.questions  # ixtiyoriy
    ok = '{text: "b", options: ["x", "y"], answer: 0}'
    first = (
        '{text: "a", options: ["x"], answer: 0}',  # bitta variant
        '{text: "a", options: ["x", "x"], answer: 0}',  # takror variant
        '{text: "a", options: ["x", "y"], answer: 2}',  # indeks tashqarida
        '{text: "a", options: ["x", "y"], answer: true}',  # bool
        '{text: " ", options: ["x", "y"], answer: 0}',  # bo'sh matn
        '{text: "a", options: ["x", "y"]}',  # answer yo'q
    )
    cases = [f"questions:\n  - {item}\n  - {ok}\n" for item in first]
    cases.append(f"questions:\n  - {ok}\n")  # bitta savol
    for bad in (*cases,):
        variant.write_text(base + bad, encoding="utf-8")
        with pytest.raises(ContentError, match="questions"):
            load_labs(content)


def test_int_02_two_questions_without_answers_and_pending_not_official(
    membership: Membership,
) -> None:
    body = _graded(membership)
    assert body["understanding"] == "pending"
    assert len(body["questions"]) == 2
    for q in body["questions"]:
        assert set(q) == {"text", "options"}  # to'g'ri javob yo'q
    assert (
        '"answer"'
        not in _client(membership.student).get(f"/api/submissions/{body['id']}").content.decode()
    )
    # Javob berilmaguncha ball rasmiy emas (eng yuqori ball, challenge).
    assert _client(membership.student).get(URL).json()["best_final_score"] is None
    assert _client(membership.student).get("/api/labs/M01/assignment").json()["challenge"] is None


def test_int_02_correct_answers_keep_score(membership: Membership) -> None:
    sid = _graded(membership)["id"]
    response = _answer(membership, sid, _correct(sid))
    assert response.status_code == 200
    assert (response.json()["understanding"], response.json()["final_score"]) == (
        "passed",
        "100.00",
    )
    assert _client(membership.student).get(URL).json()["best_final_score"] == "100.00"
    assert _client(membership.student).get(f"/api/submissions/{sid}").json()["questions"] is None
    # Bir marta: qayta javob — 409.
    again = _answer(membership, sid, _correct(sid))
    assert (again.status_code, again.json()["code"]) == (409, "not_awaiting_answers")


def test_int_02_wrong_answer_halves_score(membership: Membership) -> None:
    sid = _graded(membership)["id"]
    right = _correct(sid)
    wrong = [right[0], (right[1] + 1) % 2]
    body = _answer(membership, sid, wrong).json()
    assert (body["understanding"], body["final_score"]) == ("failed", "50.00")
    submission = Submission.objects.get(pk=sid)
    assert (submission.score, submission.final_score) == (100, Decimal("50.00"))
    assert submission.answers == wrong
    record = submission.student_assignment
    assert results.best_score(record) == Decimal("50.00")
    # Past ball ham yarmiga kamayadi (egasining 2026-11-27 qarori: "yarmiga kamaysin").
    fake.responses.append(
        {
            "status": "ok",
            "error": None,
            "stdout": "",
            "tests": [
                {"step": "load", "kind": "hidden", "name": "a", "passed": True, "message": ""},
                {"step": "clean", "kind": "hidden", "name": "b", "passed": False, "message": ""},
            ],
        }
    )
    low = _graded(membership)["id"]
    right = _correct(low)
    body = _answer(membership, low, [(right[0] + 1) % 2, right[1]]).json()
    assert body["final_score"] == "20.00"
    assert Submission.objects.get(pk=low).score == 40


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("100.00", "50.00"),
        ("40.00", "20.00"),
        ("70.05", "35.03"),
        ("0.01", "0.01"),
        ("0.00", "0.00"),
    ],
)
def test_int_02_halving_keeps_two_decimals(before: str, after: str) -> None:
    assert service.halve_score(Decimal(before)) == Decimal(after)


@pytest.mark.parametrize("answers", [[0], [0, 0, 0], [0, 9], ["a", 0], None])
def test_int_02_invalid_answers_400(membership: Membership, answers: Any) -> None:
    sid = _graded(membership)["id"]
    assert _answer(membership, sid, answers).status_code == 400
    assert Submission.objects.get(pk=sid).understanding == Understanding.PENDING


def test_int_02_no_questions_means_none_and_official(membership: Membership) -> None:
    Variant.objects.update(questions=[])
    body = _graded(membership)
    assert (body["understanding"], body["questions"]) == ("none", None)
    assert _client(membership.student).get(URL).json()["best_final_score"] == "100.00"


def test_int_02_idor_and_pending_attempt(membership: Membership) -> None:
    sid = _post(membership).json()["id"]  # hali baholanmagan
    assert _answer(membership, sid, [0, 0]).status_code == 409
    service.grade(sid)
    peer = _peer(membership)
    stranger = _client(peer.student).post(
        f"/api/submissions/{sid}/answers", {"answers": [0, 0]}, format="json"
    )
    assert stranger.status_code == 404
    assert (
        _client(make_instructor())
        .post(f"/api/submissions/{sid}/answers", {"answers": [0, 0]}, format="json")
        .status_code
        == 403
    )
    assert _answer(membership, 999_999, [0, 0]).status_code == 404


def test_int_02_instructor_sees_questions_correct_and_chosen(membership: Membership) -> None:
    sid = _graded(membership)["id"]
    right = _correct(sid)
    _answer(membership, sid, right)
    url = (
        f"/api/sections/{membership.section.pk}/labs/M01/students/"
        f"{membership.student.pk}/submissions"
    )
    item = _client(membership.section.instructor).get(url).json()["submissions"][0]
    assert item["understanding"] == "passed"
    detail = item["understanding_detail"]
    assert [d["chosen"] for d in detail] == right
    assert [d["answer"] for d in detail] == right
    assert all(d["text"] and d["options"] for d in detail)


def test_int_02_repo_content_every_variant_has_questions() -> None:
    from django.conf import settings

    labs = load_labs(Path(settings.BASE_DIR).parent / "content")
    assert labs
    for lab in labs:
        for level, number, _ in lab.variants:
            assert len(lab.questions.get((level, number), [])) >= 2, (lab.code, level, number)
