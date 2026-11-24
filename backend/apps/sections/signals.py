"""#95: akkaunt nofaol qilinganda yoki paroli o'zgarganda (tiklash) ochiq WebSocket darhol yopiladi.

Aks holda ulanish 15 daqiqagacha (`MAX_LIFETIME_SECONDS`) ochiq qolardi.
Har qanday yo'l (API, admin) — signal orqali.
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.accounts.models import User
from apps.sections.realtime import close_user_sockets


@receiver(pre_save, sender=User, dispatch_uid="sections.user_access_before")
def _remember(sender: type[User], instance: User, **kwargs: Any) -> None:
    instance._access_before = (  # type: ignore[attr-defined]
        User.objects.filter(pk=instance.pk).values_list("is_active", "password").first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=User, dispatch_uid="sections.user_access_after")
def _close_if_access_changed(
    sender: type[User], instance: User, created: bool, **kwargs: Any
) -> None:
    before = getattr(instance, "_access_before", None)
    if created or before is None:
        return
    was_active, old_password = before
    if (was_active and not instance.is_active) or old_password != instance.password:
        close_user_sockets(instance.pk)
