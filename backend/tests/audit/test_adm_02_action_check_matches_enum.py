"""ADM-02: bazadagi `audit_auditlog_action_valid` CHECK `Action` ro'yxati bilan bir xil (tasdiqlangan).

Audit migratsiyalari qo'lda (`NOT VALID` + `VALIDATE`) yozilganda ro'yxat adashib ketmasligi uchun.
"""

from __future__ import annotations

import re

import pytest
from django.db import connection

from apps.audit.models import Action

pytestmark = pytest.mark.django_db


def test_adm_02_db_check_equals_action_values() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT convalidated, pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'audit_auditlog_action_valid'"
        )
        validated, definition = cursor.fetchone()
    assert validated is True
    assert sorted(re.findall(r"'([a-z_]+)'", definition)) == sorted(Action.values)
