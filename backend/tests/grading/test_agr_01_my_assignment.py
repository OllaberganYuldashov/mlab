"""AGR-01, AGR-05, LAB-07 (I3-04): talabaning topshirig'i — shart, qadamlar, ko'rinadigan testlar.

Yashirin testlar javobda hech qachon bo'lmaydi; variant birinchi ochilishda beriladi va saqlanadi.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.courses.models import Topic
from apps.grading import variants
from apps.grading.content import import_labs
from apps.grading.models import Assignment, StudentAssignment, Variant
from apps.sections.models import AccessWindow, Membership
from tests.accounts.factories import make_user
from tests.grading.test_agr_07_assignment_import import content  # noqa: F401  (fixture)
from tests.labs.test_lab_05_autosave import _approved, _client
from tests.sections.factories import make_course

pytestmark = pytest.mark.django_db

URL = "/api/labs/M01/assignment"


@pytest.fixture
def membership(content: Path) -> Membership:  # noqa: F811
    membership = _approved()
    Topic.objects.create(course=membership.section.course, code="M02", title="T2", order=2)
    import_labs(content, membership.section.course)
    Assignment.objects.update(topic_code="M01")
    return membership


def _get(membership: Membership) -> Any:
    return _client(membership.student).get(URL)


def test_agr_01_student_gets_statement_steps_and_visible_tests_only(
    membership: Membership,
) -> None:
    response = _get(membership)
    assert response.status_code == 200
    body = response.json()
    record = StudentAssignment.objects.get(student=membership.student)
    variant = record.variant
    assert body["code"] == "A01"
    assert body["title"] == "Pandas bilan tozalash"
    assert body["level"] == "basic"
    assert body["params"] == variant.params
    # Shart variant parametrlari bilan to'ldirilgan.
    assert f"`{variant.params['column']}`" in body["statement"]
    assert "{column}" not in body["statement"]
    assert [(s["key"], s["points"]) for s in body["steps"]] == [("load", 40), ("clean", 60)]
    assert body["steps"][0]["visible_test"].startswith("def test_loaded")
    assert body["steps"][1]["visible_test"] is None
    # AGR-05: yashirin test kodi ham, nomi ham yo'q.
    text = response.content.decode()
    assert "test_shape" not in text
    assert "test_no_nan" not in text
    assert "hidden" not in text
    # Challenge (ADP-03) va mustaqil topshiriq bu javobda yo'q — ular keyinroq taklif qilinadi.
    assert "challenge" not in body


def test_agr_01_variant_assigned_once_and_stable(membership: Membership) -> None:
    first = _get(membership).json()
    second = _get(membership).json()
    assert first == second
    assert StudentAssignment.objects.count() == 1
    expected = variants.pick_index(membership.student.pk, "A01", "basic", 5) + 1
    assert StudentAssignment.objects.get().variant.number == expected


def test_agr_01_query_count_is_bounded(membership: Membership) -> None:
    _get(membership)  # variant berildi
    with CaptureQueriesContext(connection) as ctx:
        assert _get(membership).status_code == 200
    assert len(ctx.captured_queries) <= 9, [q["sql"] for q in ctx.captured_queries]


def test_agr_01_statement_placeholders_cannot_reach_attributes(membership: Membership) -> None:
    Assignment.objects.update(statement="{column.__class__} va {column} va {{literal}}")
    body = _get(membership).json()
    record = StudentAssignment.objects.get()
    column = record.variant.params["column"]
    assert body["statement"] == f"{{column.__class__}} va {column} va {{literal}}"


def test_agr_01_topic_without_assignment_is_404(membership: Membership) -> None:
    Assignment.objects.update(topic_code="M05")
    response = _get(membership)
    assert (response.status_code, response.json()["code"]) == (404, "no_assignment")
    assert StudentAssignment.objects.count() == 0


def test_agr_01_closed_lab_is_403_and_assigns_nothing(membership: Membership) -> None:
    AccessWindow.objects.all().delete()
    response = _get(membership)
    assert (response.status_code, response.json()["code"]) == (403, "lab_closed")
    assert StudentAssignment.objects.count() == 0


def test_agr_01_stranger_and_staff_are_refused(membership: Membership) -> None:
    # Guruhga a'zo bo'lmagan talaba (IDOR): boshqa guruh kursi topshirig'ini ololmaydi.
    assert _client(make_user()).get(URL).status_code == 403
    assert _client(membership.section.instructor).get(URL).status_code == 403
    assert StudentAssignment.objects.count() == 0


def test_agr_01_other_course_assignment_not_visible(membership: Membership) -> None:
    other = _approved(course=make_course())  # boshqa kurs, M01 oynasi ochiq, topshiriq yo'q
    response = _client(other.student).get(URL)
    assert response.status_code == 404
    assert Variant.objects.filter(assignment__course=other.section.course).count() == 0
