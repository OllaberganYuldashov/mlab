"""ADM-02 (R0-12): audit jurnali — faqat qo'shiladi, secret yozilmaydi."""

from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal

import pytest
from django.contrib.admin.sites import AdminSite
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.test import RequestFactory

from apps.audit import record
from apps.audit.admin import AuditLogAdmin
from apps.audit.models import Action, AppendOnlyError, AuditLog
from config import observability
from tests.accounts.factories import make_user

pytestmark = pytest.mark.django_db


def test_adm_02_record_stores_actor_target_before_after() -> None:
    admin = make_user(role="admin", direction=None)
    student = make_user()
    entry = record(
        Action.ROLE_CHANGED,
        actor=admin,
        target=student,
        before={"role": "student"},
        after={"role": "instructor"},
    )
    entry.refresh_from_db()
    assert entry.actor == admin
    assert entry.target_type == "accounts.user"
    assert entry.target_id == str(student.pk)
    assert entry.before == {"role": "student"}
    assert entry.after == {"role": "instructor"}
    assert entry.created_at is not None


def test_adm_02_system_action_without_actor() -> None:
    entry = record(Action.PASSWORD_RESET, actor=None, target=make_user())
    assert entry.actor is None
    assert entry.before == {}
    assert entry.after == {}


def test_adm_02_record_captures_request_id() -> None:
    token = observability._request_id.set("rid-audit")
    try:
        entry = record(Action.LOGIN, actor=None, target=make_user())
    finally:
        observability._request_id.reset(token)
    assert entry.request_id == "rid-audit"


@pytest.mark.parametrize("key", ["password", "new_password", "token", "api_key", "sessionid"])
def test_adm_02_sensitive_fields_never_recorded(key: str) -> None:
    value = secrets.token_urlsafe(16)
    entry = record(
        Action.PASSWORD_RESET,
        actor=None,
        target=make_user(),
        before={key: value, "nested": {key: value}, "items": [{key: value}]},
        after={key: value, "role": "student"},
    )
    entry.refresh_from_db()
    assert value not in str(entry.before) + str(entry.after)
    assert entry.after["role"] == "student"


def test_adm_02_record_serializes_dates_and_decimals() -> None:
    entry = record(
        Action.GRADE_CHANGED,
        actor=None,
        target=make_user(),
        before={"score": Decimal("7.50"), "at": datetime(2026, 11, 22, 10, 0)},
    )
    entry.refresh_from_db()
    assert entry.before == {"score": "7.50", "at": "2026-11-22T10:00:00"}


def test_adm_02_update_forbidden_in_model() -> None:
    entry = record(Action.LOGIN, actor=None, target=make_user())
    entry.action = Action.ROLE_CHANGED
    with pytest.raises(AppendOnlyError):
        entry.save()


def test_adm_02_delete_forbidden_in_model_and_queryset() -> None:
    entry = record(Action.LOGIN, actor=None, target=make_user())
    with pytest.raises(AppendOnlyError):
        entry.delete()
    with pytest.raises(AppendOnlyError):
        AuditLog.objects.all().delete()
    with pytest.raises(AppendOnlyError):
        AuditLog.objects.update(action=Action.ROLE_CHANGED)


def test_adm_02_update_and_delete_forbidden_at_db_level() -> None:
    # ORM'ni aylanib o'tgan SQL ham rad etiladi (trigger).
    entry = record(Action.LOGIN, actor=None, target=make_user())
    table = AuditLog._meta.db_table
    with (
        pytest.raises(IntegrityError, match="append-only"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(f"UPDATE {table} SET action = 'role_changed' WHERE id = %s", [entry.pk])  # noqa: S608
    with (
        pytest.raises(IntegrityError, match="append-only"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(f"DELETE FROM {table} WHERE id = %s", [entry.pk])  # noqa: S608
    assert AuditLog.objects.filter(pk=entry.pk, action=Action.LOGIN).exists()


def test_adm_02_unknown_action_rejected_at_db_level() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        AuditLog.objects.bulk_create([AuditLog(action="hack", target_type="x.y", target_id="1")])


def test_adm_02_actor_with_history_cannot_be_deleted() -> None:
    admin = make_user(role="admin", direction=None)
    record(Action.ROLE_CHANGED, actor=admin, target=make_user())
    with pytest.raises(ProtectedError):
        admin.delete()


def test_adm_02_indexes_for_target_and_actor_timelines() -> None:
    fields = {tuple(index.fields) for index in AuditLog._meta.indexes}
    assert ("target_type", "target_id", "created_at") in fields
    assert ("actor", "created_at") in fields


def test_adm_02_admin_is_read_only() -> None:
    model_admin = AuditLogAdmin(AuditLog, AdminSite())
    request = RequestFactory().get("/")
    request.user = make_user(role="super_admin", direction=None, is_superuser=True)
    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_change_permission(request) is False
    assert model_admin.has_delete_permission(request) is False
    assert model_admin.has_view_permission(request) is True


def test_adm_02_str_has_no_personal_data() -> None:
    student = make_user()
    entry = record(Action.LOGIN, actor=None, target=student)
    assert student.hemis_id not in str(entry)
    assert student.full_name not in str(entry)
