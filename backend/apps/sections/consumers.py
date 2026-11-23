"""Talabaning WebSocket ulanishi (ACC-05). Faqat serverdan xabar; mijoz yozgani o'qilmaydi.

Ulanish shartlari HTTP bilan bir xil: tizimga kirgan, faol, `student`, parol almashtirish talab
qilinmagan (`must_change_password`) va tasdiqlangan a'zo. Faqat o'z guruhi kanaliga yoziladi.

Ruxsat ulanishda tekshiriladi, shuning uchun (security-reviewer):
- ulanish ko'pi bilan `MAX_LIFETIME` yashaydi — mijoz qayta ulanadi va tekshiruv qayta o'tadi
  (nofaol qilish, parol tiklash, sessiya tugashi shu muddatda kuchga kiradi);
- a'zolik o'zgarsa (chiqarish, o'tkazish) talabaning `user-<id>` kanaliga `force.close` keladi.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.accounts.models import Role, User
from apps.sections.models import Membership
from apps.sections.realtime import section_group, user_group

logger = logging.getLogger("mlab.realtime")
MAX_LIFETIME_SECONDS = 15 * 60
CLOSE_FORBIDDEN = 4403
CLOSE_ERROR = 1011
CLOSE_RECONNECT = 4000  # mijoz qayta ulanadi (muddat tugadi yoki a'zolik o'zgardi)


def _approved_section_id_sync(user: Any) -> int | None:
    if not isinstance(user, User) or not user.is_authenticated or not user.is_active:
        return None
    if user.role != Role.STUDENT or user.must_change_password:
        return None
    membership = Membership.objects.approved().filter(student=user).first()
    return membership.section_id if membership else None


class StudentConsumer(AsyncJsonWebsocketConsumer):  # type: ignore[misc]
    groups_joined: list[str]
    expiry: asyncio.TimerHandle | None = None

    async def connect(self) -> None:
        self.groups_joined = []
        user = self.scope.get("user")
        try:
            section_id = await database_sync_to_async(_approved_section_id_sync)(user)
            if section_id is None:
                await self.close(code=CLOSE_FORBIDDEN)
                return
            for group in (section_group(section_id), user_group(user.pk)):
                await self.channel_layer.group_add(group, self.channel_name)
                self.groups_joined.append(group)
        except Exception:  # DB yoki Redis ishlamayapti — toza yopish
            logger.exception("realtime.connect_failed", extra={"event": "realtime.connect_failed"})
            await self.close(code=CLOSE_ERROR)
            return
        await self.accept()
        loop = asyncio.get_running_loop()
        self.expiry = loop.call_later(
            MAX_LIFETIME_SECONDS, lambda: asyncio.ensure_future(self.close(code=CLOSE_RECONNECT))
        )

    async def disconnect(self, code: int) -> None:
        if self.expiry is not None:
            self.expiry.cancel()
        for group in getattr(self, "groups_joined", []):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        return  # mijoz freymlari o'qilmaydi va parse qilinmaydi

    async def window_changed(self, event: dict[str, Any]) -> None:
        await self.send_json(event)

    async def force_close(self, event: dict[str, Any]) -> None:
        await self.close(code=CLOSE_RECONNECT)
