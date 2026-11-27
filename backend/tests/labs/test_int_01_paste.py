"""INT-01, ACC-09 (I3-12): paste chegarasi va qaydi."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.courses.content import ContentError, load_course
from apps.labs.models import LabEvent, LabEventKind
from apps.sections.models import AccessWindow
from tests.accounts.factories import make_user
from tests.labs.test_lab_05_autosave import _approved, _client

pytestmark = pytest.mark.django_db

URL = "/api/labs/M01/events"


@pytest.fixture(autouse=True)
def _clean_cache() -> Any:
    cache.clear()
    yield
    cache.clear()


def _paste(client: APIClient, size: int, cell: str = "c1", url: str = URL) -> Any:
    return client.post(url, {"kind": "paste", "size": size, "cell": cell}, format="json")


def test_int_01_work_reports_paste_rules_with_course_default_200() -> None:
    body = _client(_approved().student).get("/api/labs/M01/work").json()
    assert body["paste_limit"] == 200
    assert body["proctored"] is False


def test_int_01_small_paste_logged_large_paste_blocked() -> None:
    membership = _approved()
    client = _client(membership.student)
    small = _paste(client, 200)
    large = _paste(client, 201, cell="c2")
    assert (small.status_code, small.json()) == (201, {"blocked": False, "recorded": True})
    assert (large.status_code, large.json()) == (201, {"blocked": True, "recorded": True})
    events = list(LabEvent.objects.order_by("pk").values_list("kind", "size", "cell", "student"))
    assert events == [
        (LabEventKind.PASTE, 200, "c1", membership.student.pk),
        (LabEventKind.PASTE_BLOCKED, 201, "c2", membership.student.pk),
    ]


def test_int_01_course_limit_is_used() -> None:
    membership = _approved()
    course = membership.section.course
    course.paste_limit = 1000
    course.save(update_fields=["paste_limit"])
    client = _client(membership.student)
    assert client.get("/api/labs/M01/work").json()["paste_limit"] == 1000
    assert _paste(client, 999).json() == {"blocked": False, "recorded": True}


def test_acc_09_proctored_window_blocks_any_paste() -> None:
    membership = _approved()
    AccessWindow.objects.filter(section=membership.section).update(proctored=True)
    client = _client(membership.student)
    assert client.get("/api/labs/M01/work").json()["proctored"] is True
    assert _paste(client, 1).json() == {"blocked": True, "recorded": True}
    assert LabEvent.objects.get().kind == LabEventKind.PASTE_BLOCKED


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "paste", "size": -1, "cell": "c1"},
        {"kind": "copy", "size": 5, "cell": "c1"},
        {"kind": "paste", "size": 5, "cell": "../x"},
        {"kind": "paste", "size": "5x", "cell": "c1"},
        {"kind": "paste", "size": 10_000_001, "cell": "c1"},
    ],
)
def test_int_01_invalid_event_rejected(payload: dict[str, Any]) -> None:
    client = _client(_approved().student)
    assert client.post(URL, payload, format="json").status_code == 400
    assert not LabEvent.objects.exists()


def test_int_01_event_only_for_own_approved_membership() -> None:
    _approved()
    outsider = _client(make_user())  # guruhsiz talaba
    assert _paste(outsider, 5).status_code == 403
    assert _paste(_client(_approved().student), 5, url="/api/labs/M99/events").status_code == 404
    anon = APIClient()
    assert _paste(anon, 5).status_code in (401, 403)
    instructor = APIClient()
    instructor.force_authenticate(_approved().section.instructor)
    assert _paste(instructor, 5).status_code == 403
    assert LabEvent.objects.count() == 0


def test_int_01_events_throttled_per_student() -> None:
    client = _client(_approved().student)
    with override_settings(LAB_EVENT_RATE="2/min"):
        codes = [_paste(client, 1).status_code for _ in range(3)]
    assert codes == [201, 201, 429]


def test_int_01_event_text_is_never_stored() -> None:
    client = _client(_approved().student)
    response = client.post(
        URL, {"kind": "paste", "size": 3, "cell": "c1", "text": "abc"}, format="json"
    )
    assert response.status_code == 201
    assert {f.name for f in LabEvent._meta.get_fields()} == {
        "id",
        "student",
        "section",
        "topic",
        "kind",
        "size",
        "cell",
        "at",
    }


def test_int_01_paste_limit_from_course_yaml(tmp_path: Path) -> None:
    root = tmp_path / "content"
    root.mkdir()
    yaml = 'slug: k\ntitle: K\nversion: "1"\ndefaults:\n  paste_limit: {}\n'
    (root / "course.yaml").write_text(yaml.format(500), encoding="utf-8")
    assert load_course(root).defaults["paste_limit"] == 500
    (root / "course.yaml").write_text(yaml.format(10_001), encoding="utf-8")
    with pytest.raises(ContentError, match=r"0\.\.10000"):
        load_course(root)
