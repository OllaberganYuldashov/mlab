"""ADP-03 (I3-11): tez va to'liq bajarganga challenge ochiladi; asosiy ballga ta'sir qilmaydi."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

import pytest
from django.core.cache import cache

from apps.grading import results, service
from apps.grading.models import Assignment, Submission, SubmissionPolicy
from apps.grading.sandbox import fake
from apps.sections.models import Membership
from tests.grading.test_agr_02_submit_api import URL, _peer, _post, membership  # noqa: F401
from tests.grading.test_agr_07_assignment_import import content  # noqa: F401  (fixture)
from tests.labs.test_lab_05_autosave import _client

pytestmark = pytest.mark.django_db

TASK = "/api/labs/M01/assignment"
CHALLENGE = "Outlier'larni IQR bilan toping."


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    cache.clear()
    fake.responses.clear()
    yield
    cache.clear()


def _half() -> dict[str, object]:
    tests = [
        {"step": "load", "kind": "hidden", "name": "a", "passed": True, "message": ""},
        {"step": "clean", "kind": "hidden", "name": "b", "passed": False, "message": ""},
    ]
    return {"status": "ok", "error": None, "stdout": "", "tests": tests}


def _challenge(membership: Membership) -> object:  # noqa: F811
    return _client(membership.student).get(TASK).json()["challenge"]


def test_adp_03_locked_until_full_score_then_stays_open(membership: Membership) -> None:  # noqa: F811
    fake.responses.append(_half())
    service.grade(_post(membership).json()["id"])  # 40 ball
    assert _challenge(membership) is None
    service.grade(_post(membership).json()["id"])  # soxta sandbox: hammasi o'tdi — 100
    assert _challenge(membership) == CHALLENGE
    fake.responses.append(_half())
    service.grade(_post(membership).json()["id"])  # keyingi urinish past — baribir ochiq
    assert _challenge(membership) == CHALLENGE
    # Asosiy ball challenge'dan o'zgarmaydi (GRD-01): eng yuqori rasmiy ball — 100.
    record = Submission.objects.first().student_assignment  # type: ignore[union-attr]
    assert results.best_score(record) == Decimal("100.00")


@pytest.mark.parametrize("policy", [SubmissionPolicy.LATE, SubmissionPolicy.PRACTICE])
def test_adp_03_late_or_practice_full_score_does_not_unlock(
    membership: Membership,  # noqa: F811
    policy: str,
) -> None:
    sid = _post(membership).json()["id"]
    Submission.objects.filter(pk=sid).update(policy=policy)
    service.grade(sid)
    assert Submission.objects.get(pk=sid).final_score == Decimal("100.00")
    assert _challenge(membership) is None


def test_adp_03_own_attempts_only_and_no_challenge_text(membership: Membership) -> None:  # noqa: F811
    service.grade(_post(membership).json()["id"])
    peer = _peer(membership)
    assert _challenge(peer) is None  # boshqa talabaning 100 bali ochmaydi
    Assignment.objects.update(challenge="")
    body = _client(membership.student).get(TASK).json()
    assert (body["has_challenge"], body["challenge"]) == (False, None)
    assert _client(membership.student).get(URL).status_code == 200
