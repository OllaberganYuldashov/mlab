"""INT-04, INT-05, ACC-09 (I3-14): shubhali holatlar o'qituvchiga, nazorat rejimida tab qaydi.

Avtomatik jazo yo'q: ro'yxat faqat o'qiladi, ballga tegmaydi; qarorni o'qituvchi qabul qiladi.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.core.cache import cache

from apps.grading import service
from apps.grading.models import StudentAssignment, Submission
from apps.grading.sandbox import fake
from apps.labs.models import IntegrityNote, LabEvent, LabEventKind
from apps.sections.models import AccessWindow, Membership
from tests.accounts.factories import make_user
from tests.grading.test_agr_02_submit_api import _peer, _post
from tests.grading.test_agr_07_assignment_import import content  # noqa: F401  (fixture)
from tests.grading.test_int_02_understanding import (
    _answer,
    _correct,
    membership,  # noqa: F401  (fixture)
)
from tests.labs.test_lab_05_autosave import _approved, _client
from tests.sections.factories import make_instructor

pytestmark = pytest.mark.django_db

EVENTS = "/api/labs/M01/events"


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    cache.clear()
    fake.responses.clear()
    yield
    cache.clear()


@pytest.fixture
def lab(request: pytest.FixtureRequest) -> Membership:
    """Topshiriq va tushunish savollari bilan tasdiqlangan talaba (test_int_02 fixture'i)."""
    m: Membership = request.getfixturevalue("membership")
    return m


def _flags_url(lab: Membership, code: str = "M01") -> str:
    return f"/api/sections/{lab.section_id}/labs/{code}/integrity"


def _note_url(lab: Membership, student_id: int | None = None) -> str:
    sid = lab.student_id if student_id is None else student_id
    return f"/api/sections/{lab.section_id}/labs/M01/students/{sid}/integrity-note"


def _flags(lab: Membership) -> list[dict[str, Any]]:
    response = _client(lab.section.instructor).get(_flags_url(lab))
    assert response.status_code == 200
    students: list[dict[str, Any]] = response.json()["students"]
    return students


def _tab(lab: Membership) -> Any:
    return _client(lab.student).post(EVENTS, {"kind": "tab_hidden"}, format="json")


def _proctor(lab: Membership) -> None:
    AccessWindow.objects.filter(section=lab.section).update(proctored=True)


# --- INT-05: tab almashtirish qaydi -------------------------------------------------------


def test_int_05_tab_switch_is_recorded_only_in_proctored_mode() -> None:
    lab = _approved()
    ignored = _tab(lab)
    assert (ignored.status_code, ignored.json()) == (201, {"blocked": False, "recorded": False})
    assert not LabEvent.objects.exists()
    _proctor(lab)
    recorded = _tab(lab)
    assert (recorded.status_code, recorded.json()) == (201, {"blocked": False, "recorded": True})
    event = LabEvent.objects.get()
    assert (event.kind, event.size, event.cell) == (LabEventKind.TAB_HIDDEN, 0, "")


def test_int_05_paste_still_requires_size_and_cell() -> None:
    client = _client(_approved().student)
    assert client.post(EVENTS, {"kind": "paste"}, format="json").status_code == 400
    assert client.post(EVENTS, {"kind": "paste", "size": 5}, format="json").status_code == 400
    assert client.post(EVENTS, {"kind": "copy"}, format="json").status_code == 400
    ok = client.post(EVENTS, {"kind": "paste", "size": 5, "cell": "c1"}, format="json")
    assert ok.json() == {"blocked": False, "recorded": True}


# --- INT-04: shubhali holatlar ro'yxati ----------------------------------------------------


def test_int_04_flags_count_events_wrong_answers_and_fast_full_score(
    lab: Membership,
) -> None:
    _proctor(lab)
    client = _client(lab.student)
    for size in (5000, 6000):  # nazorat rejimida — rad etiladi
        client.post(EVENTS, {"kind": "paste", "size": size, "cell": "c1"}, format="json")
    for _ in range(3):
        _tab(lab)
    sid = _post(lab).json()["id"]
    service.grade(sid)  # fake sandbox — hammasi o'tadi, 100 ball, berilganidan bir zumda
    right = _correct(sid)
    _answer(lab, sid, [(right[0] + 1) % 2, right[1]])
    clean = _peer(lab)  # hech narsa qilmagan talaba ro'yxatda yo'q
    rows = _flags(lab)
    assert [r["student_id"] for r in rows] == [lab.student_id]
    row = rows[0]
    assert row["full_name"] == lab.student.full_name
    assert (row["paste_blocked"], row["tab_hidden"], row["understanding_failed"]) == (2, 3, 1)
    assert row["fast_full_score"] is True
    assert row["note"] is None
    assert clean.student_id not in [r["student_id"] for r in rows]


def test_int_04_slow_full_score_is_not_flagged(lab: Membership) -> None:
    sid = _post(lab).json()["id"]
    StudentAssignment.objects.update(
        created_at=Submission.objects.get().created_at - timedelta(hours=1)
    )
    service.grade(sid)
    assert _flags(lab) == []


def test_int_04_list_never_changes_scores(lab: Membership) -> None:
    _proctor(lab)
    _tab(lab)
    sid = _post(lab).json()["id"]
    service.grade(sid)
    before = Submission.objects.values_list("score", "final_score").get(pk=sid)
    _flags(lab)
    _client(lab.section.instructor).put(_note_url(lab), {"text": "Gaplashish"}, format="json")
    assert Submission.objects.values_list("score", "final_score").get(pk=sid) == before


def test_int_04_flags_are_per_topic(lab: Membership) -> None:
    _proctor(lab)
    _tab(lab)
    response = _client(lab.section.instructor).get(_flags_url(lab, "M02"))
    assert (response.status_code, response.json()["students"]) == (200, [])


# --- INT-04: o'qituvchi izohi --------------------------------------------------------------


def test_int_04_instructor_note_is_saved_listed_and_cleared(lab: Membership) -> None:
    instructor = _client(lab.section.instructor)
    saved = instructor.put(_note_url(lab), {"text": "  Sinfda so'rab ko'raman  "}, format="json")
    assert saved.status_code == 200
    assert saved.json()["text"] == "Sinfda so'rab ko'raman"
    row = _flags(lab)[0]  # izohi bor talaba belgisiz ham ro'yxatda
    assert row["student_id"] == lab.student_id
    assert row["note"]["text"] == "Sinfda so'rab ko'raman"
    assert row["note"]["author"] == lab.section.instructor.full_name
    updated = instructor.put(_note_url(lab), {"text": "Tushuntirib berdi"}, format="json")
    assert updated.status_code == 200
    assert IntegrityNote.objects.get().text == "Tushuntirib berdi"
    assert instructor.put(_note_url(lab), {"text": ""}, format="json").status_code == 204
    assert not IntegrityNote.objects.exists()
    assert _flags(lab) == []


@pytest.mark.parametrize("payload", [{}, {"text": None}, {"text": "x" * 1001}])
def test_int_04_note_validation(lab: Membership, payload: dict[str, Any]) -> None:
    response = _client(lab.section.instructor).put(_note_url(lab), payload, format="json")
    assert response.status_code == 400


# --- IDOR va rollar ------------------------------------------------------------------------


def test_int_04_only_own_section_instructor_sees_and_edits(lab: Membership) -> None:
    _proctor(lab)
    _tab(lab)
    stranger = _client(make_instructor())
    assert stranger.get(_flags_url(lab)).status_code == 404
    assert stranger.put(_note_url(lab), {"text": "x"}, format="json").status_code == 404
    student = _client(lab.student)
    assert student.get(_flags_url(lab)).status_code == 403
    assert student.put(_note_url(lab), {"text": "x"}, format="json").status_code == 403
    assert _client(make_user()).get(_flags_url(lab)).status_code == 403
    instructor = _client(lab.section.instructor)
    # Guruhda bo'lmagan talaba va noma'lum mavzu — 404.
    outsider = _approved(open_window=False)
    assert (
        instructor.put(
            _note_url(lab, outsider.student_id), {"text": "x"}, format="json"
        ).status_code
        == 404
    )
    assert instructor.get(_flags_url(lab, "M99")).status_code == 404
    assert not IntegrityNote.objects.exists()
