"""Lokal demo ma'lumot (#173): `docker compose up` dan keyin darhol kirib ko'rish uchun.

Faqat lokal: prod sozlamalarida (`config.settings.prod`) ishlamaydi. Ismlar soxta ("Demo ..."),
Hemis ID'lar 9 bilan boshlanadi — haqiqiy shaxsiy ma'lumot yo'q (CLAUDE.md 5.3).
Idempotent: qayta ishga tushirilsa mavjud yozuvlarni qayta yaratmaydi va parollarni o'zgartirmaydi.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.functions import Now
from django.utils import timezone

from apps.accounts.models import Consent, Direction, Role, User
from apps.courses.models import Course
from apps.sections.models import AccessWindow, Membership, MembershipStatus, Section, WindowMode

# Faqat lokal demo paroli (docs/learn/local-run.md); prod'da buyruq ishlamaydi.
DEMO_PASSWORD = "mlab-demo-2026"  # noqa: S105  # gitleaks:allow
ADMIN_ID = "900000000001"
INSTRUCTOR_ID = "900000000002"
STUDENT_IDS = ("900000000011", "900000000012", "900000000013")
DIRECTION = "Demo yo'nalish"
SECTION = "Demo guruh"


class Command(BaseCommand):
    help = "Lokal demo: admin, o'qituvchi, 3 talaba, guruh va ochiq laboratoriya oynalari."

    def handle(self, *args: Any, **options: Any) -> None:
        if settings.SETTINGS_MODULE.endswith(".prod"):
            raise CommandError(
                "seed_demo faqat lokal muhitda ishlaydi (prod sozlamalari aniqlandi)."
            )
        course = Course.objects.order_by("pk").first()
        if course is None:
            raise CommandError("Avval kontentni yuklang: manage.py import_content ../content")
        with transaction.atomic():
            created = self._seed(course)
        self.stdout.write(
            f"Demo tayyor ({created} ta yangi yozuv). Kirish: Hemis ID {ADMIN_ID} (admin), "
            f"{INSTRUCTOR_ID} (o'qituvchi), {STUDENT_IDS[0]} (talaba); parol: {DEMO_PASSWORD}"
        )

    def _user(self, hemis_id: str, **fields: Any) -> tuple[User, bool]:
        user = User.objects.filter(hemis_id=hemis_id).first()
        if user is not None:
            return user, False
        if fields.get("role") == Role.SUPER_ADMIN:
            fields.pop("role")
            return User.objects.create_superuser(hemis_id, DEMO_PASSWORD, **fields), True
        user = User(hemis_id=hemis_id, **fields)
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user, True

    def _seed(self, course: Course) -> int:
        created = 0
        direction, new = Direction.objects.get_or_create(name=DIRECTION)
        created += new
        _, new = self._user(ADMIN_ID, role=Role.SUPER_ADMIN, full_name="Demo Admin")
        created += new
        instructor, new = self._user(
            INSTRUCTOR_ID,
            role=Role.INSTRUCTOR,
            full_name="Demo O'qituvchi",
            direction=None,
            student_limit=30,
        )
        created += new
        section, new = Section.objects.get_or_create(
            course=course,
            instructor=instructor,
            name=SECTION,
            defaults={"direction": direction},
        )
        created += new
        now = timezone.now()
        for i, hemis_id in enumerate(STUDENT_IDS, start=1):
            student, new = self._user(
                hemis_id, role=Role.STUDENT, full_name=f"Demo Talaba {i}", direction=direction
            )
            created += new
            if new:
                Consent.objects.create(user=student, policy_version=settings.PRIVACY_POLICY_VERSION)
            if not Membership.objects.filter(student=student).exists():
                Membership.objects.create(
                    student=student,
                    section=section,
                    status=MembershipStatus.APPROVED,
                    decided_at=Now(),  # requested_at bilan bir xil soat (bazadagi CHECK)
                    decided_by=instructor,
                )
                created += 1
        # Hamma laboratoriya ochiq (demo); o'qituvchi o'zgartirsa saqlanib qoladi.
        for topic in course.topics.all():
            _, new = AccessWindow.objects.get_or_create(
                section=section,
                topic=topic,
                defaults={"mode": WindowMode.OPEN_NOW, "opens_at": now},
            )
            created += new
        return created
