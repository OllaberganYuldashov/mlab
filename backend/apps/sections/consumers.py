"""Talabaning WebSocket ulanishi (ACC-05). Faqat serverdan xabar; mijoz yozgani e'tiborsiz.

Ulanish shartlari HTTP bilan bir xil: tizimga kirgan, faol, `student`, parol almashtirish talab
qilinmagan (`must_change_password`) va tasdiqlangan a'zo. Faqat o'z guruhi kanaliga yoziladi.
"""

from __future__ import annotations

from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.accounts.models import Role, User
from apps.sections.models import Membership
from apps.sections.realtime import section_group


def _approved_section_id_sync(user: Any) -> int | None:
    if not isinstance(user, User) or not user.is_authenticated or not user.is_active:
        return None
    if user.role != Role.STUDENT or user.must_change_password:
        return None
    membership = Membership.objects.approved().filter(student=user).first()
    return membership.section_id if membership else None


class StudentConsumer(AsyncJsonWebsocketConsumer):  # type: ignore[misc]
    group: str | None = None

    async def connect(self) -> None:
        section_id = await database_sync_to_async(_approved_section_id_sync)(self.scope.get("user"))
        if section_id is None:
            await self.close(code=4403)
            return
        self.group = section_group(section_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        if self.group is not None:
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content: Any, **kwargs: Any) -> None:
        return  # mijozdan buyruq qabul qilinmaydi

    async def window_changed(self, event: dict[str, Any]) -> None:
        await self.send_json(event)
