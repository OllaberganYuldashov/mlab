"""Guruh a'zoligi bo'yicha servis funksiyalari (I1-04 dan). Yozuvlar faqat shu yerdan o'tadi."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.sections.models import Membership, MembershipStatus, Section

OTHER_SECTION = _("Siz boshqa guruhga a'zosiz. O'tish uchun o'qituvchingizga murojaat qiling.")


@dataclass(frozen=True)
class JoinRefused(Exception):
    code: str
    detail: str


def approved_count(section: Section) -> int:
    return Membership.objects.approved().filter(section=section).count()


def request_membership(student: User, section_id: int) -> tuple[Membership, bool]:
    """Talaba so'rovi: (a'zolik, yangi yaratildimi). Takroriy so'rov o'sha a'zolikni qaytaradi.

    Guruh qatori qulflanadi — sig'im tekshiruvi tasdiqlash (I1-05) bilan bir tartibda.
    """
    try:
        with transaction.atomic():
            section = Section.objects.select_for_update().get(pk=section_id)
            active = Membership.objects.active().filter(student=student).first()
            if active is not None:
                if active.section_id == section.pk:
                    return active, False
                raise JoinRefused("other_section", str(OTHER_SECTION))
            if not section.join_enabled:
                raise JoinRefused(
                    "join_disabled", str(_("Bu guruhga qo'shilish hozir o'chirilgan."))
                )
            if approved_count(section) >= section.capacity:
                raise JoinRefused(
                    "section_full",
                    str(_("Guruh to'lgan. O'qituvchingizga murojaat qiling.")),
                )
            membership = Membership.objects.create(
                student=student, section=section, status=MembershipStatus.PENDING
            )
            return membership, True
    except IntegrityError:
        # Parallel so'rov (bitta faol a'zolik — partial unique): o'sha talabaning yangi yozuvi.
        active = Membership.objects.active().filter(student=student).first()
        if active is None:
            raise
        if active.section_id != section_id:
            raise JoinRefused("other_section", str(OTHER_SECTION)) from None
        return active, False
