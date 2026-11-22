"""SRS 2.2 (R0-05): rol ruxsatlari matritsasi, Django Admin'ga kirish, parol xeshi ko'rinmasligi."""

from __future__ import annotations

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import Client
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.accounts.models import Role, User
from apps.accounts.permissions import IsAdmin, IsInstructor, IsStudent, IsSuperAdmin
from apps.audit.models import Action, AuditLog
from tests.accounts.factories import make_direction, make_user

pytestmark = pytest.mark.django_db

ALL_ROLES = (Role.SUPER_ADMIN, Role.ADMIN, Role.INSTRUCTOR, Role.STUDENT)


def _user(role: Role, **fields: Any) -> User:
    return make_user(role=role, is_superuser=role == Role.SUPER_ADMIN, **fields)


def _call(permission: Any, user: Any) -> int:
    class Protected(APIView):
        permission_classes = (permission,)

        def get(self, request: Any) -> Response:
            return Response({"ok": True})

    request = APIRequestFactory().get("/protected")
    if user is not None:
        force_authenticate(request, user=user)
    response = Protected.as_view()(request)
    return int(response.status_code)


# Matritsa: har permission va har rol. Kutilgan natija — faqat o'z roli ruxsat oladi.
MATRIX: list[tuple[type[BasePermission], Role, int]] = [
    (perm, role, 200 if role == own else 403)
    for perm, own in (
        (IsSuperAdmin, Role.SUPER_ADMIN),
        (IsAdmin, Role.ADMIN),
        (IsInstructor, Role.INSTRUCTOR),
        (IsStudent, Role.STUDENT),
    )
    for role in ALL_ROLES
]


@pytest.mark.parametrize(("permission", "role", "expected"), MATRIX)
def test_srs_2_2_permission_matrix(
    permission: type[BasePermission], role: Role, expected: int
) -> None:
    assert _call(permission, _user(role)) == expected


@pytest.mark.parametrize("permission", [IsSuperAdmin, IsAdmin, IsInstructor, IsStudent])
def test_srs_2_2_anonymous_denied(permission: type[BasePermission]) -> None:
    assert _call(permission, None) in (401, 403)
    assert _call(permission, AnonymousUser()) in (401, 403)


@pytest.mark.parametrize("role", ALL_ROLES)
def test_srs_2_2_inactive_user_denied(role: Role) -> None:
    perm = {
        Role.SUPER_ADMIN: IsSuperAdmin,
        Role.ADMIN: IsAdmin,
        Role.INSTRUCTOR: IsInstructor,
        Role.STUDENT: IsStudent,
    }[role]
    assert _call(perm, _user(role, is_active=False)) == 403


def test_srs_2_2_permissions_compose_with_or() -> None:
    either = IsAdmin | IsSuperAdmin
    assert _call(either, _user(Role.ADMIN)) == 200
    assert _call(either, _user(Role.SUPER_ADMIN)) == 200
    assert _call(either, _user(Role.INSTRUCTOR)) == 403


def test_srs_2_2_no_role_hierarchy_super_admin_is_not_student() -> None:
    # Ierarxiya yo'q: super admin talaba yoki o'qituvchi amallarini avtomatik olmaydi.
    assert _call(IsStudent, _user(Role.SUPER_ADMIN)) == 403
    assert _call(IsInstructor, _user(Role.SUPER_ADMIN)) == 403


def test_srs_2_2_default_drf_permission_is_authenticated() -> None:
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]


# --- Django Admin ---


@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        (Role.SUPER_ADMIN, True),
        (Role.ADMIN, True),
        (Role.INSTRUCTOR, False),
        (Role.STUDENT, False),
    ],
)
def test_srs_2_2_admin_site_only_for_super_admin_and_admin(
    client: Client, role: Role, allowed: bool
) -> None:
    client.force_login(_user(role))
    response = client.get("/admin/")
    if allowed:
        assert response.status_code == 200
    else:
        assert response.status_code == 302
        assert "/admin/login/" in response["Location"]


def test_srs_2_2_admin_site_anonymous_redirected(client: Client) -> None:
    response = client.get("/admin/")
    assert response.status_code == 302


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPER_ADMIN])
def test_srs_2_2_admin_never_sees_password_hash(client: Client, role: Role) -> None:
    from config.settings import base

    staff = _user(role)
    student = make_user()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(settings, "PASSWORD_HASHERS", base.PASSWORD_HASHERS)
        student.set_password("x" * 12)
        student.save()
    student.refresh_from_db()
    client.force_login(staff)
    for url in (f"/admin/accounts/user/{student.pk}/change/", "/admin/accounts/user/"):
        response = client.get(url)
        assert response.status_code == 200
        body = response.content.decode()
        assert student.password not in body
        assert "argon2" not in body
        assert 'name="password"' not in body


def test_srs_2_2_admin_role_field_read_only_for_admin(client: Client) -> None:
    admin_user = _user(Role.ADMIN, direction=None)
    student = make_user()
    client.force_login(admin_user)
    response = client.post(
        f"/admin/accounts/user/{student.pk}/change/",
        {
            "full_name": student.full_name,
            "role": Role.SUPER_ADMIN,
            "direction": student.direction_id,
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    student.refresh_from_db()
    assert student.role == Role.STUDENT
    assert not student.is_superuser


@pytest.mark.parametrize("target_role", [Role.SUPER_ADMIN, Role.ADMIN])
def test_srs_2_2_admin_cannot_edit_staff_accounts(client: Client, target_role: Role) -> None:
    client.force_login(_user(Role.ADMIN, direction=None))
    other = _user(target_role, direction=None)
    response = client.post(
        f"/admin/accounts/user/{other.pk}/change/",
        {"full_name": "Boshqa Ism", "role": target_role, "is_active": "on"},
    )
    # Xodim akkauntlari admin'ning queryset'ida yo'q: "topilmadi" -> admin indeksiga qaytaradi.
    assert response.status_code == 302
    assert response["Location"] == "/admin/"
    other.refresh_from_db()
    assert other.full_name != "Boshqa Ism"


def test_srs_2_2_super_admin_role_change_is_audited(client: Client) -> None:
    boss = _user(Role.SUPER_ADMIN, direction=None)
    student = make_user()
    client.force_login(boss)
    response = client.post(
        f"/admin/accounts/user/{student.pk}/change/",
        {"full_name": student.full_name, "role": Role.INSTRUCTOR, "is_active": "on"},
    )
    assert response.status_code == 302
    student.refresh_from_db()
    assert student.role == Role.INSTRUCTOR
    entry = AuditLog.objects.get(action=Action.ROLE_CHANGED, target_id=str(student.pk))
    assert entry.actor == boss
    assert entry.before == {"role": "student"}
    assert entry.after == {"role": "instructor"}


def test_srs_2_2_promotion_to_super_admin_syncs_superuser_flag(client: Client) -> None:
    client.force_login(_user(Role.SUPER_ADMIN, direction=None))
    instructor = _user(Role.INSTRUCTOR, direction=None)
    client.post(
        f"/admin/accounts/user/{instructor.pk}/change/",
        {"full_name": instructor.full_name, "role": Role.SUPER_ADMIN, "is_active": "on"},
    )
    instructor.refresh_from_db()
    assert instructor.role == Role.SUPER_ADMIN
    assert instructor.is_superuser


def test_srs_2_2_non_role_edit_not_audited(client: Client) -> None:
    client.force_login(_user(Role.ADMIN, direction=None))
    student = make_user()
    client.post(
        f"/admin/accounts/user/{student.pk}/change/",
        {"full_name": "Yangi Ism", "direction": student.direction_id, "is_active": "on"},
    )
    student.refresh_from_db()
    assert student.full_name == "Yangi Ism"
    assert not AuditLog.objects.filter(action=Action.ROLE_CHANGED).exists()


@pytest.mark.parametrize(("role", "status"), [(Role.SUPER_ADMIN, 200), (Role.ADMIN, 403)])
def test_srs_2_2_audit_log_visible_only_to_super_admin(
    client: Client, role: Role, status: int
) -> None:
    client.force_login(_user(role, direction=None))
    assert client.get("/admin/audit/auditlog/").status_code == status


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPER_ADMIN])
def test_srs_2_2_staff_manage_directions(client: Client, role: Role) -> None:
    client.force_login(_user(role, direction=None))
    response = client.post("/admin/accounts/direction/add/", {"name": "Sunʼiy intellekt"})
    assert response.status_code == 302
    assert client.get("/admin/accounts/direction/").status_code == 200


def test_srs_2_2_no_user_add_or_delete_in_admin(client: Client) -> None:
    client.force_login(_user(Role.SUPER_ADMIN, direction=None))
    student = make_user(direction=make_direction())
    assert client.get("/admin/accounts/user/add/").status_code == 403
    assert client.get(f"/admin/accounts/user/{student.pk}/delete/").status_code == 403


# --- security-reviewer tavsiyalari ---


def test_srs_2_2_group_admin_not_exposed(client: Client) -> None:
    client.force_login(_user(Role.SUPER_ADMIN, direction=None))
    assert client.get("/admin/auth/group/").status_code == 404


def test_srs_2_2_django_perms_never_bypass_roles() -> None:
    from django.contrib.auth.models import Permission

    admin_user = _user(Role.ADMIN, direction=None)
    admin_user.user_permissions.add(Permission.objects.get(codename="view_auditlog"))
    boss = _user(Role.SUPER_ADMIN, direction=None)
    assert not admin_user.has_perm("audit.view_auditlog")
    assert not boss.has_perm("audit.delete_auditlog")
    assert not boss.has_module_perms("audit")


def test_srs_2_2_super_admin_cannot_demote_or_deactivate_self(client: Client) -> None:
    boss = _user(Role.SUPER_ADMIN, direction=None)
    client.force_login(boss)
    response = client.post(
        f"/admin/accounts/user/{boss.pk}/change/",
        {"full_name": boss.full_name, "role": Role.STUDENT},  # is_active yo'q = o'chirishga urinish
    )
    assert response.status_code == 302
    boss.refresh_from_db()
    assert boss.role == Role.SUPER_ADMIN
    assert boss.is_active


def test_srs_2_2_deactivation_is_audited(client: Client) -> None:
    client.force_login(_user(Role.ADMIN, direction=None))
    student = make_user()
    client.post(
        f"/admin/accounts/user/{student.pk}/change/",
        {"full_name": student.full_name, "direction": student.direction_id},
    )
    student.refresh_from_db()
    assert not student.is_active
    entry = AuditLog.objects.get(action=Action.USER_ACTIVE_CHANGED, target_id=str(student.pk))
    assert entry.before == {"is_active": True}
    assert entry.after == {"is_active": False}


def test_srs_2_2_admin_does_not_see_staff_accounts(client: Client) -> None:
    client.force_login(_user(Role.ADMIN, direction=None))
    other_admin = _user(Role.ADMIN, direction=None)
    boss = _user(Role.SUPER_ADMIN, direction=None)
    body = client.get("/admin/accounts/user/").content.decode()
    assert other_admin.hemis_id not in body
    assert boss.hemis_id not in body
    # To'g'ridan-to'g'ri URL ham ochilmaydi (IDOR).
    response = client.get(f"/admin/accounts/user/{boss.pk}/change/")
    assert response.status_code == 302  # "obyekt topilmadi" — admin indeksiga qaytaradi
    assert boss.full_name not in client.get(response["Location"]).content.decode()
