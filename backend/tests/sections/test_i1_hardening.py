"""#95 (I1 security-reviewer takliflari): WebSocket ulanishlar chegarasi, soketni darhol yopish,
guruh yaratish cheklovi."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.sections import consumers, realtime
from tests.accounts.factories import make_direction, make_user
from tests.sections.factories import make_course, make_instructor
from tests.sections.test_acc_05_realtime import WsClient, _approved

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clean_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        realtime, "_safe_send", lambda group, message: calls.append((group, message))
    )
    return calls


def test_95_deactivated_user_socket_closed(
    sent: list[tuple[str, dict[str, Any]]], django_capture_on_commit_callbacks: Any
) -> None:
    student = make_user()
    with django_capture_on_commit_callbacks(execute=True):
        student.is_active = False
        student.save(update_fields=["is_active"])
    assert (realtime.user_group(student.pk), {"type": "force.close"}) in sent


def test_95_password_reset_closes_socket(
    sent: list[tuple[str, dict[str, Any]]], django_capture_on_commit_callbacks: Any
) -> None:
    student = make_user()
    admin = make_user(role=Role.ADMIN, direction=None)
    client = APIClient()
    client.force_authenticate(admin)
    with django_capture_on_commit_callbacks(execute=True):
        assert client.post(f"/api/users/{student.pk}/reset-password").status_code == 200
    assert (realtime.user_group(student.pk), {"type": "force.close"}) in sent


def test_95_ordinary_save_does_not_close(
    sent: list[tuple[str, dict[str, Any]]], django_capture_on_commit_callbacks: Any
) -> None:
    student = make_user()
    with django_capture_on_commit_callbacks(execute=True):
        student.full_name = "Yangi Ism"
        student.save(update_fields=["full_name"])
    assert sent == []


@pytest.mark.django_db(transaction=True)
def test_95_websocket_connections_per_user_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(consumers, "MAX_CONNECTIONS_PER_USER", 2)
    membership = _approved()

    async def scenario() -> list[bool]:
        clients = [WsClient(membership.student) for _ in range(3)]
        results = [await c.connect() for c in clients]
        await clients[0].disconnect()  # biri yopilsa — joy bo'shaydi
        results.append(await WsClient(membership.student).connect())
        return results

    assert async_to_sync(scenario)() == [True, True, False, True]


def test_95_section_create_throttled_per_instructor() -> None:
    make_course()
    instructor = make_instructor()
    client = APIClient()
    client.force_authenticate(instructor)
    direction = make_direction()
    with override_settings(SECTION_CREATE_RATE="2/hour"):
        codes = [
            client.post(
                "/api/sections", {"name": f"G{i}", "direction": direction.pk}, format="json"
            ).status_code
            for i in range(3)
        ]
        other = APIClient()
        other.force_authenticate(make_instructor())
        other_code = other.post(
            "/api/sections", {"name": "X", "direction": direction.pk}, format="json"
        ).status_code
    assert codes == [201, 201, 429]
    assert other_code == 201  # cheklov o'qituvchi bo'yicha
