"""Guruh a'zoligi bo'yicha servis funksiyalari (I1-04 dan). Yozuvlar faqat shu yerdan o'tadi."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models.functions import Now
from django.utils.translation import gettext_lazy as _

from apps.accounts.limits import StudentLimitExceeded, ensure_capacity
from apps.accounts.models import User
from apps.audit import record
from apps.audit.models import Action
from apps.sections import realtime
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
            section = Section.objects.select_for_update(no_key=True).filter(pk=section_id).first()
            if section is None:  # token tekshirilgandan keyin o'chirilgan
                raise Section.DoesNotExist
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


@dataclass(frozen=True)
class Decision:
    approved: list[int]
    rejected: list[int]
    skipped: list[int]


def decide_memberships(actor: User, section_id: int, ids: list[int], approve: bool) -> Decision:
    """SEC-04: bittalab yoki ommaviy qaror. Hammasi bitta tranzaksiyada.

    Qulf tartibi (deadlock'siz): o'qituvchi → guruh → a'zoliklar. Sig'im (SEC-06) va o'qituvchining
    umumiy limiti (SEC-08) qulflardan keyin hisoblanadi; oshsa — hech kim tasdiqlanmaydi.
    Shu guruhda kutilayotgan bo'lmagan id'lar (begona, eskirgan, yo'q) — `skipped`, ta'sirsiz.
    """
    with transaction.atomic():
        section = Section.objects.select_related("instructor").get(pk=section_id)
        # NO KEY UPDATE: FK tekshiruvi (`decided_by`, `student` → KEY SHARE) bilan to'qnashmaydi —
        # oddiy FOR UPDATE parallel qarorlarda deadlock berdi (test_sec_06_parallel_...).
        instructor = User.objects.select_for_update(no_key=True).get(pk=section.instructor_id)
        section = Section.objects.select_for_update(no_key=True).get(pk=section_id)
        targets = list(
            Membership.objects.select_for_update(no_key=True)
            .filter(section=section, status=MembershipStatus.PENDING, pk__in=ids)
            .order_by("id")
        )
        found = {m.pk for m in targets}
        skipped = sorted(set(ids) - found)
        if approve and targets:
            current = approved_count(section)
            if current + len(targets) > section.capacity:
                raise JoinRefused(
                    "section_full",
                    str(
                        _("Guruh sig'imi ({capacity}) yetmaydi: bo'sh joy {free} ta.").format(
                            capacity=section.capacity, free=max(section.capacity - current, 0)
                        )
                    ),
                )
            total = Membership.objects.approved().filter(section__instructor=instructor).count()
            try:
                ensure_capacity(instructor, current_students=total, adding=len(targets))
            except StudentLimitExceeded as exc:
                raise JoinRefused("instructor_limit", str(exc)) from exc
        new_status = MembershipStatus.APPROVED if approve else MembershipStatus.REJECTED
        action = Action.MEMBERSHIP_APPROVED if approve else Action.MEMBERSHIP_REJECTED
        now = Now()  # DB soati: `requested_at` (db_default) bilan bir manba — CHECK izchil
        for membership in targets:
            membership.status = new_status
            membership.decided_at = now
            membership.decided_by = actor
            membership.save(update_fields=["status", "decided_at", "decided_by"])
            record(
                action,
                actor=actor,
                target=membership,
                before={"status": MembershipStatus.PENDING.value},
                after={"status": new_status.value},
            )
        decided = sorted(found)
        return Decision(
            approved=decided if approve else [],
            rejected=[] if approve else decided,
            skipped=skipped,
        )


def _lock_sections(*ids: int) -> dict[int, Section]:
    """Bir nechta guruhni doim bir xil (id) tartibda qulflaydi — deadlock'siz."""
    locked = Section.objects.select_for_update(no_key=True).filter(pk__in=ids).order_by("id")
    return {s.pk: s for s in locked}


def move_membership(actor: User, membership_id: int, source_id: int, target_id: int) -> Membership:
    """SEC-07: tasdiqlangan a'zoni shu o'qituvchining boshqa guruhiga o'tkazish.

    Eski yozuv `removed` bo'lib qoladi (tarix), yangisi `approved`. Talabaning ishlari talabaga
    bog'langan (guruhga emas), shuning uchun o'tkazishda yo'qolmaydi.
    """
    with transaction.atomic():
        sections = _lock_sections(source_id, target_id)
        source, target = sections[source_id], sections[target_id]
        membership = (
            Membership.objects.select_for_update(no_key=True)
            .filter(pk=membership_id, section=source, status=MembershipStatus.APPROVED)
            .first()
        )
        if membership is None:
            raise Membership.DoesNotExist
        if approved_count(target) + 1 > target.capacity:
            raise JoinRefused(
                "section_full",
                str(_("Tanlangan guruh to'lgan ({capacity}).")).format(capacity=target.capacity),
            )
        now = Now()  # DB soati: `requested_at` (db_default) bilan bir manba — CHECK izchil
        membership.status = MembershipStatus.REMOVED
        membership.decided_at = now
        membership.decided_by = actor
        membership.save(update_fields=["status", "decided_at", "decided_by"])
        moved = Membership.objects.create(
            student=membership.student,
            section=target,
            status=MembershipStatus.APPROVED,
            decided_at=now,
            decided_by=actor,
        )
        moved.refresh_from_db()
        realtime.membership_changed(membership.student_id)
        record(
            Action.MEMBERSHIP_MOVED,
            actor=actor,
            target=moved,
            before={"section": source.pk},
            after={"section": target.pk},
        )
        return moved


def remove_membership(actor: User, membership_id: int, section_id: int) -> None:
    with transaction.atomic():
        membership = (
            Membership.objects.select_for_update(no_key=True)
            .filter(pk=membership_id, section_id=section_id, status=MembershipStatus.APPROVED)
            .first()
        )
        if membership is None:
            raise Membership.DoesNotExist
        membership.status = MembershipStatus.REMOVED
        membership.decided_at = Now()
        membership.decided_by = actor
        membership.save(update_fields=["status", "decided_at", "decided_by"])
        realtime.membership_changed(membership.student_id)
        record(
            Action.MEMBERSHIP_REMOVED,
            actor=actor,
            target=membership,
            before={"status": MembershipStatus.APPROVED.value},
            after={"status": MembershipStatus.REMOVED.value},
        )
