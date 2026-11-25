"""AGR-05, AGR-06 (I3-08): qadamlar bo'yicha natija, eng yuqori ball, yashirin testlar yashirin."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from django.core.cache import cache

from apps.grading import results, service
from apps.grading.models import Submission, SubmissionPolicy
from apps.grading.sandbox import fake
from apps.sections.models import Membership
from tests.accounts.factories import make_user
from tests.grading.test_agr_02_submit_api import URL, _peer, _post, membership  # noqa: F401
from tests.grading.test_agr_07_assignment_import import content  # noqa: F401  (fixture)
from tests.labs.test_lab_05_autosave import _client
from tests.sections.factories import make_instructor

pytestmark = pytest.mark.django_db

SECRET = "kutilgan qiymat 42 — yashirin"


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    cache.clear()
    fake.responses.clear()
    fake.calls.clear()
    yield
    cache.clear()


def _runner(*tests: tuple[str, str, bool, str], status: str = "ok", error: Any = None) -> Any:
    return {
        "status": status,
        "error": error,
        "stdout": f"talaba chiqishi va {SECRET}",
        "tests": [
            {"step": step, "kind": kind, "name": f"test_{kind}_{i}", "passed": ok, "message": msg}
            for i, (step, kind, ok, msg) in enumerate(tests)
        ],
    }


def _graded(membership: Membership, response: Any) -> int:  # noqa: F811
    fake.responses.append(response)
    sid = int(_post(membership).json()["id"])
    service.grade(sid)
    return sid


def test_agr_05_steps_scores_counts_and_messages(membership: Membership) -> None:  # noqa: F811
    sid = _graded(
        membership,
        _runner(
            ("load", "visible", False, "df topilmadi"),
            ("load", "hidden", True, ""),
            ("clean", "hidden", False, f"assert: {SECRET}"),  # runner buzilgan bo'lsa ham
            ("clean", "hidden", True, ""),
        ),
    )
    body = _client(membership.student).get(f"/api/submissions/{sid}").json()
    assert body["score"] == 50  # 40 * 1/2 + 60 * 1/2
    steps = body["result"]["steps"]
    assert [
        (s["key"], s["title"], s["points"], s["score"], s["passed"], s["total"]) for s in steps
    ] == [
        ("load", "Yuklash", 40, 20, 1, 2),
        ("clean", "Tozalash", 60, 30, 1, 2),
    ]
    assert sum(s["score"] for s in steps) == body["score"]
    assert steps[0]["tests"][0] == {
        "name": "test_visible_0",
        "visible": True,
        "passed": False,
        "message": "df topilmadi",
    }
    assert steps[1]["tests"] == [
        {"name": "yashirin test 2", "visible": False, "passed": False, "message": "O'tmadi"},
        {"name": "yashirin test 3", "visible": False, "passed": True, "message": ""},
    ]
    assert body["result"]["code_error"] is None


def test_agr_05_hidden_details_and_stdout_never_leak(membership: Membership) -> None:  # noqa: F811
    sid = _graded(membership, _runner(("load", "hidden", False, SECRET)))
    student = _client(membership.student)
    texts = [
        student.get(f"/api/submissions/{sid}").content.decode(),
        student.get(URL).content.decode(),
    ]
    for text in texts:
        assert SECRET not in text
        assert "test_hidden" not in text
        assert "stdout" not in text


def test_agr_05_code_error_shown_and_pending_has_no_result(membership: Membership) -> None:  # noqa: F811
    pending = _post(membership).json()["id"]
    assert _client(membership.student).get(f"/api/submissions/{pending}").json()["result"] is None
    service.grade(pending)
    sid = _graded(
        membership,
        _runner(("load", "hidden", False, ""), status="code_error", error="NameError: x (2-qator)"),
    )
    body = _client(membership.student).get(f"/api/submissions/{sid}").json()
    assert body["result"]["code_error"] == "NameError: x (2-qator)"
    assert body["score"] == 0


def test_agr_06_best_official_score_ignores_practice_and_errors(
    membership: Membership,  # noqa: F811
) -> None:
    def half() -> Any:
        return _runner(("load", "hidden", True, ""), ("clean", "hidden", False, ""))

    _graded(membership, half())  # 40
    _graded(membership, _runner(("load", "hidden", False, "")))  # 0
    best = _client(membership.student).get(URL).json()
    assert best["best_final_score"] == "40.00"
    assert len(best["submissions"]) == 2
    # Mashq urinishi 100 bo'lsa ham rasmiy eng yuqori ball o'zgarmaydi.
    sid = _graded(membership, _runner(("load", "hidden", True, ""), ("clean", "hidden", True, "")))
    Submission.objects.filter(pk=sid).update(policy=SubmissionPolicy.PRACTICE)
    assert _client(membership.student).get(URL).json()["best_final_score"] == "40.00"
    record = Submission.objects.get(pk=sid).student_assignment
    assert results.best_score(record) == Decimal("40.00")
    assert results.best_score(None) is None


def test_agr_06_no_attempts_yet(membership: Membership) -> None:  # noqa: F811
    body = _client(membership.student).get(URL).json()
    assert body == {"best_final_score": None, "submissions": []}


def _teacher_url(membership: Membership, student_id: int | None = None, code: str = "M01") -> str:  # noqa: F811
    sid, student = membership.section.pk, student_id or membership.student.pk
    return f"/api/sections/{sid}/labs/{code}/students/{student}/submissions"


def test_agr_06_instructor_sees_own_students_attempts_with_code(
    membership: Membership,  # noqa: F811
) -> None:
    _graded(membership, _runner(("load", "hidden", True, SECRET), ("clean", "hidden", True, "")))
    response = _client(membership.section.instructor).get(_teacher_url(membership))
    assert response.status_code == 200
    body = response.json()
    assert body["best_final_score"] == "100.00"
    (item,) = body["submissions"]
    assert item["code"] == "df = 1"
    assert item["result"]["steps"][0]["tests"][0]["name"] == "yashirin test 1"
    assert SECRET not in response.content.decode()


def test_agr_06_instructor_idor_and_wrong_targets(membership: Membership) -> None:  # noqa: F811
    _graded(membership, _runner(("load", "hidden", True, "")))
    stranger = _client(make_instructor())
    assert stranger.get(_teacher_url(membership)).status_code == 404  # begona guruh
    teacher = _client(membership.section.instructor)
    outsider = make_user()  # guruhda yo'q talaba
    assert teacher.get(_teacher_url(membership, outsider.pk)).status_code == 404
    assert teacher.get(_teacher_url(membership, code="M77")).status_code == 404
    assert _client(membership.student).get(_teacher_url(membership)).status_code == 403
    # Guruhdagi, lekin hali urinmagan talaba — bo'sh ro'yxat.
    peer = _peer(membership)
    assert teacher.get(_teacher_url(membership, peer.student.pk)).json() == {
        "best_final_score": None,
        "submissions": [],
    }
