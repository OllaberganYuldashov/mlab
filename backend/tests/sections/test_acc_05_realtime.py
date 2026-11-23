"""ACC-05 (I1-11): WebSocket orqali "oyna ochildi" xabari va talabaning keyingi mavzusi."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import pytest
from asgiref.sync import async_to_sync
from asgiref.testing import ApplicationCommunicator
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Topic
from apps.sections.models import AccessWindow, Membership, MembershipStatus, Section, WindowMode
from config.asgi import application
from tests.accounts.factories import make_user
from tests.sections.factories import make_instructor, make_membership, make_section

pytestmark = pytest.mark.django_db(transaction=True)


def _approved(section: Section | None = None, **user: Any) -> Membership:
    membership = make_membership(section=section or make_section(), student=make_user(**user))
    membership.status = MembershipStatus.APPROVED
    membership.decided_at = timezone.now()
    membership.decided_by = membership.section.instructor
    membership.save()
    return membership


class WsClient:
    """`channels.testing.WebsocketCommunicator` o'rnini bosuvchi (u daphne'ni talab qiladi)."""

    def __init__(self, user: Any) -> None:
        scope = {
            "type": "websocket",
            "path": "/ws/student",
            "headers": [(b"host", b"localhost"), (b"origin", b"http://localhost")],
            "subprotocols": [],
            "user": user,
        }
        self.comm = ApplicationCommunicator(application, scope)

    async def connect(self) -> bool:
        await self.comm.send_input({"type": "websocket.connect"})
        reply = await self.comm.receive_output(timeout=3)
        return bool(reply["type"] == "websocket.accept")

    async def send_json_to(self, data: Any) -> None:
        await self.comm.send_input({"type": "websocket.receive", "text": json.dumps(data)})

    async def receive_json_from(self, timeout: float = 3) -> Any:
        reply = await self.comm.receive_output(timeout=timeout)
        assert reply["type"] == "websocket.send"
        return json.loads(reply["text"])

    async def receive_nothing(self, timeout: float = 0.3) -> bool:
        return bool(await self.comm.receive_nothing(timeout=timeout))

    async def disconnect(self) -> None:
        await self.comm.send_input({"type": "websocket.disconnect", "code": 1000})
        await self.comm.wait(timeout=3)


async def _connect(user: Any) -> tuple[WsClient, bool]:
    client = WsClient(user)
    return client, await client.connect()


def _connect_sync(user: Any) -> bool:
    async def run() -> bool:
        comm, ok = await _connect(user)
        if ok:
            await comm.disconnect()
        return ok

    return async_to_sync(run)()


def test_acc_05_anonymous_rejected() -> None:
    assert _connect_sync(AnonymousUser()) is False


def test_acc_05_non_student_and_unapproved_rejected() -> None:
    assert _connect_sync(make_instructor()) is False
    pending = make_membership()
    assert _connect_sync(pending.student) is False


def test_acc_05_must_change_password_and_inactive_rejected() -> None:
    m1 = _approved(must_change_password=True)
    m2 = _approved(is_active=False)
    assert _connect_sync(m1.student) is False
    assert _connect_sync(m2.student) is False


def test_acc_05_student_gets_event_when_window_opens_only_for_own_section() -> None:
    mine = _approved()
    other = _approved()
    section = mine.section
    Topic.objects.create(course=section.course, code="M01", title="T", order=1)
    instructor = section.instructor

    async def scenario() -> tuple[dict[str, Any], bool]:
        comm_mine, ok1 = await _connect(mine.student)
        comm_other, ok2 = await _connect(other.student)
        assert ok1
        assert ok2

        def open_now() -> None:
            client = APIClient()
            client.force_authenticate(instructor)
            response = client.post(
                f"/api/sections/{section.pk}/windows/M01/open-now", {}, format="json"
            )
            assert response.status_code == 200

        from asgiref.sync import sync_to_async

        await sync_to_async(open_now)()
        event = await comm_mine.receive_json_from(timeout=3)
        nothing = await comm_other.receive_nothing(timeout=0.5)
        await comm_mine.disconnect()
        await comm_other.disconnect()
        return event, nothing

    event, nothing = async_to_sync(scenario)()
    assert event["type"] == "window.changed"
    assert event["topic"] == "M01"
    assert event["state"]["status"] == "open"
    assert nothing is True


def test_acc_05_client_cannot_send_messages() -> None:
    membership = _approved()

    async def scenario() -> bool:
        comm, ok = await _connect(membership.student)
        assert ok
        await comm.send_json_to({"type": "window.changed", "topic": "X"})
        quiet = await comm.receive_nothing(timeout=0.3)
        await comm.disconnect()
        return quiet

    assert async_to_sync(scenario)() is True


# --- GET /api/me/next-window ---


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_acc_05_next_window_shows_open_then_upcoming() -> None:
    membership = _approved()
    section = membership.section
    t1 = Topic.objects.create(course=section.course, code="M01", title="Bir", order=1)
    t2 = Topic.objects.create(course=section.course, code="M02", title="Ikki", order=2)
    now = timezone.now()
    AccessWindow.objects.create(
        section=section,
        topic=t2,
        mode=WindowMode.SCHEDULED,
        opens_at=now + timedelta(days=2),
        closes_at=now + timedelta(days=2, hours=1),
    )
    body = _client(membership.student).get("/api/me/next-window").json()
    assert body["open"] == []
    assert body["next"]["topic"]["code"] == "M02"
    assert body["next"]["state"]["status"] == "upcoming"
    assert "server_time" in body
    AccessWindow.objects.create(section=section, topic=t1, mode=WindowMode.OPEN_NOW, opens_at=now)
    body = _client(membership.student).get("/api/me/next-window").json()
    assert [w["topic"]["code"] for w in body["open"]] == ["M01"]


def test_acc_05_next_window_without_approved_membership() -> None:
    body = _client(make_user()).get("/api/me/next-window").json()
    assert body["open"] == []
    assert body["next"] is None


def test_acc_05_next_window_only_for_students() -> None:
    assert _client(make_instructor()).get("/api/me/next-window").status_code == 403


def test_acc_05_broadcast_failure_does_not_break_window_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.sections import realtime

    def boom(*_: Any, **__: Any) -> None:
        raise ConnectionError("redis yo'q")

    monkeypatch.setattr(realtime, "_send", boom)
    section = make_section()
    Topic.objects.create(course=section.course, code="M01", title="T", order=1)
    response = _client(section.instructor).post(
        f"/api/sections/{section.pk}/windows/M01/open-now", {}, format="json"
    )
    assert response.status_code == 200
    assert AccessWindow.objects.get().mode == WindowMode.OPEN_NOW


def test_acc_05_removed_student_socket_is_closed() -> None:
    membership = _approved()
    instructor = membership.section.instructor

    async def scenario() -> dict[str, Any]:
        comm, ok = await _connect(membership.student)
        assert ok

        def remove() -> None:
            client = APIClient()
            client.force_authenticate(instructor)
            url = f"/api/sections/{membership.section_id}/members/{membership.pk}/remove"
            assert client.post(url).status_code == 204

        from asgiref.sync import sync_to_async

        await sync_to_async(remove)()
        reply = await comm.comm.receive_output(timeout=3)
        return dict(reply)

    reply = async_to_sync(scenario)()
    assert reply["type"] == "websocket.close"
    assert reply["code"] == 4000


def test_acc_05_connection_has_max_lifetime() -> None:
    from apps.sections import consumers

    assert consumers.MAX_LIFETIME_SECONDS <= 15 * 60
