"""#173: lokal demo ma'lumot — idempotent, kirish mumkin, prod'da ishlamaydi."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.courses.models import Topic
from apps.sections.management.commands import seed_demo
from apps.sections.models import AccessWindow, Membership, MembershipStatus, Section
from apps.sections.windows import window_state
from tests.sections.factories import make_course

pytestmark = pytest.mark.django_db


def _course_with_topics() -> None:
    course = make_course()
    for i in (1, 2):
        Topic.objects.create(course=course, code=f"M0{i}", title=f"T{i}", order=i)


def test_173_seed_demo_creates_users_section_and_open_windows() -> None:
    _course_with_topics()
    call_command("seed_demo")
    roles = dict(User.objects.values_list("hemis_id", "role"))
    assert roles[seed_demo.ADMIN_ID] == Role.SUPER_ADMIN
    assert roles[seed_demo.INSTRUCTOR_ID] == Role.INSTRUCTOR
    assert all(roles[h] == Role.STUDENT for h in seed_demo.STUDENT_IDS)
    section = Section.objects.get()
    assert Membership.objects.filter(section=section, status=MembershipStatus.APPROVED).count() == 3
    states = [window_state(w, timezone.now()).status for w in AccessWindow.objects.all()]
    assert states == ["open", "open"]


def test_173_seed_demo_is_idempotent() -> None:
    _course_with_topics()
    call_command("seed_demo")
    counts = (User.objects.count(), Membership.objects.count(), AccessWindow.objects.count())
    call_command("seed_demo")
    assert (
        User.objects.count(),
        Membership.objects.count(),
        AccessWindow.objects.count(),
    ) == counts


def test_173_demo_student_can_log_in_and_open_lab() -> None:
    _course_with_topics()
    call_command("seed_demo")
    client = APIClient()
    login = client.post(
        "/api/auth/login",
        {"hemis_id": seed_demo.STUDENT_IDS[0], "password": seed_demo.DEMO_PASSWORD},
        format="json",
    )
    assert login.status_code == 200
    assert client.get("/api/labs/M01/work").json()["policy"] == "on_time"


def test_173_seed_demo_refused_in_prod_and_without_content() -> None:
    with pytest.raises(CommandError, match="import_content"):
        call_command("seed_demo")
    _course_with_topics()
    with (
        override_settings(SETTINGS_MODULE="config.settings.prod"),
        pytest.raises(CommandError, match="lokal"),
    ):
        call_command("seed_demo")
    assert not User.objects.exists()
