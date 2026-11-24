"""LAB-05, ACC-06 (I2-16): laboratoriya ishi modeli va avtosaqlash API (optimistik versiya)."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Topic
from apps.labs.models import LabWork
from apps.labs.notebook import MAX_NOTEBOOK_BYTES
from apps.sections.models import AccessWindow, Membership, MembershipStatus, WindowMode
from tests.accounts.factories import make_user
from tests.sections.factories import make_membership, make_section

pytestmark = pytest.mark.django_db

URL = "/api/labs/M01/work"


def _notebook(*sources: str) -> dict[str, Any]:
    return {
        "format": 1,
        "cells": [{"id": f"c{i}", "type": "code", "source": src} for i, src in enumerate(sources)],
    }


def _approved(open_window: bool = True, **section_fields: Any) -> Membership:
    membership = make_membership(section=make_section(**section_fields), student=make_user())
    membership.status = MembershipStatus.APPROVED
    membership.decided_at = timezone.now()
    membership.decided_by = membership.section.instructor
    membership.save()
    topic, _ = Topic.objects.get_or_create(
        course=membership.section.course, code="M01", defaults={"title": "T", "order": 1}
    )
    if open_window:
        AccessWindow.objects.create(
            section=membership.section,
            topic=topic,
            mode=WindowMode.OPEN_NOW,
            opens_at=timezone.now() - timedelta(minutes=1),
        )
    return membership


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def _put(client: APIClient, version: int, notebook: dict[str, Any], url: str = URL) -> Any:
    return client.put(url, {"version": version, "notebook": notebook}, format="json")


def test_lab_05_empty_work_then_first_save_and_reload() -> None:
    client = _client(_approved().student)
    empty = client.get(URL).json()
    assert empty["version"] == 0
    assert empty["notebook"] is None
    assert empty["policy"] == "on_time"

    saved = _put(client, 0, _notebook("print(1)"))
    assert saved.status_code == 200
    assert saved.json()["version"] == 1

    again = client.get(URL).json()
    assert again["version"] == 1
    assert again["notebook"] == _notebook("print(1)")
    assert again["saved_at"]


def test_lab_05_stale_version_conflict_returns_current() -> None:
    client = _client(_approved().student)
    _put(client, 0, _notebook("a"))
    _put(client, 1, _notebook("b"))
    stale = _put(client, 1, _notebook("eski tab"))
    assert stale.status_code == 409
    body = stale.json()
    assert body["code"] == "version_conflict"
    assert body["current_version"] == 2
    assert body["notebook"] == _notebook("b")
    assert LabWork.objects.get().notebook == _notebook("b")


def test_lab_05_replay_of_same_save_is_idempotent() -> None:
    client = _client(_approved().student)
    first = _put(client, 0, _notebook("x")).json()
    replay = _put(client, 0, _notebook("x"))  # javob yo'qolgan, mijoz qayta yubordi
    assert replay.status_code == 200
    assert replay.json() == first
    assert LabWork.objects.get().version == 1


def test_lab_05_closed_window_rejects_save_but_allows_read() -> None:
    client = _client(_approved(open_window=False).student)
    assert client.get(URL).json()["policy"] == "closed"
    response = _put(client, 0, _notebook("x"))
    assert response.status_code == 403
    assert response.json()["code"] == "lab_closed"
    assert not LabWork.objects.exists()


def test_lab_05_practice_after_close_allows_save() -> None:
    membership = _approved(open_window=False, practice_after_close=True)
    now = timezone.now()
    AccessWindow.objects.create(
        section=membership.section,
        topic=Topic.objects.get(code="M01"),
        mode=WindowMode.SCHEDULED,
        opens_at=now - timedelta(hours=2),
        closes_at=now - timedelta(hours=1),
    )
    client = _client(membership.student)
    assert client.get(URL).json()["policy"] == "practice"
    assert _put(client, 0, _notebook("x")).status_code == 200


@pytest.mark.parametrize(
    "notebook",
    [
        {"format": 2, "cells": []},
        {"format": 1},
        {"format": 1, "cells": [{"id": "a", "type": "raw", "source": ""}]},
        {"format": 1, "cells": [{"id": "a", "type": "code", "source": 5}]},
        {"format": 1, "cells": [{"id": "a", "type": "code", "source": "", "outputs": []}]},
        {"format": 1, "cells": [{"id": "a", "type": "code", "source": ""}] * 2},
        {"format": 1, "cells": [{"id": "x" * 65, "type": "code", "source": ""}]},
        {"format": 1, "cells": [{"id": "a", "type": "code", "source": ""}], "extra": 1},
        {"format": 1, "cells": [{"id": f"c{i}", "type": "code", "source": ""} for i in range(201)]},
    ],
)
def test_lab_05_invalid_notebook_rejected(notebook: dict[str, Any]) -> None:
    client = _client(_approved().student)
    response = _put(client, 0, notebook)
    assert response.status_code == 400
    assert not LabWork.objects.exists()


def test_lab_05_oversized_notebook_rejected() -> None:
    client = _client(_approved().student)
    big = _notebook("x" * MAX_NOTEBOOK_BYTES)
    assert len(json.dumps(big)) > MAX_NOTEBOOK_BYTES
    response = _put(client, 0, big)
    assert response.status_code in (400, 413)
    assert not LabWork.objects.exists()


@pytest.mark.parametrize("bad", [None, -1, "1", True])
def test_lab_05_version_must_be_non_negative_int(bad: Any) -> None:
    client = _client(_approved().student)
    response = client.put(URL, {"version": bad, "notebook": _notebook()}, format="json")
    assert response.status_code == 400


def test_lab_05_unknown_topic_404_and_non_students_403() -> None:
    membership = _approved()
    assert _client(membership.student).get("/api/labs/M99/work").status_code == 404
    assert _client(membership.section.instructor).get(URL).status_code == 403
    pending = make_membership(student=make_user())
    assert _client(pending.student).get(URL).status_code == 403


def test_lab_05_students_never_see_each_others_work() -> None:
    first = _approved()
    _put(_client(first.student), 0, _notebook("maxfiy"))
    other = make_membership(section=first.section, student=make_user())
    other.status = MembershipStatus.APPROVED
    other.decided_at = timezone.now()
    other.decided_by = first.section.instructor
    other.save()
    body = _client(other.student).get(URL).json()
    assert body["version"] == 0
    assert body["notebook"] is None


def test_lab_05_instructor_reads_own_students_work_only() -> None:
    membership = _approved()
    _put(_client(membership.student), 0, _notebook("ish"))
    url = f"/api/sections/{membership.section_id}/labs/M01/works/{membership.student_id}"
    response = _client(membership.section.instructor).get(url)
    assert response.status_code == 200
    assert response.json()["notebook"] == _notebook("ish")

    stranger = make_section(course=membership.section.course).instructor
    assert _client(stranger).get(url).status_code == 404
    assert _client(membership.student).get(url).status_code == 403
    outsider = make_user()
    other_url = f"/api/sections/{membership.section_id}/labs/M01/works/{outsider.pk}"
    assert _client(membership.section.instructor).get(other_url).status_code == 404


def test_lab_05_one_work_per_student_section_topic_in_db() -> None:
    membership = _approved()
    topic = Topic.objects.get(code="M01")
    LabWork.objects.create(
        student=membership.student, section=membership.section, topic=topic, notebook=_notebook()
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        LabWork.objects.create(
            student=membership.student,
            section=membership.section,
            topic=topic,
            notebook=_notebook(),
        )
