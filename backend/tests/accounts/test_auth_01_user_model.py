"""AUTH-01/AUTH-03/NFR-10 (R0-04): custom User — Hemis ID login, FIO, rol, yo'nalish, Argon2.

Cheklovlar DB darajasida tekshiriladi: ilova qatlamini aylanib o'tgan yozuv ham rad etilishi kerak.
"""

from __future__ import annotations

import secrets

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import override_settings

from apps.accounts.models import Direction, Role, User
from tests.accounts.factories import make_direction, make_user

pytestmark = pytest.mark.django_db
PASSWORD = secrets.token_urlsafe(12)


def test_auth_01_user_model_is_custom_with_hemis_id_login() -> None:
    assert get_user_model() is User
    assert User.USERNAME_FIELD == "hemis_id"


def test_auth_01_hemis_id_is_unique_at_db_level() -> None:
    user = make_user()
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [
                User(
                    hemis_id=user.hemis_id,
                    full_name="X",
                    role=Role.STUDENT,
                    direction=user.direction,
                )
            ]
        )


@pytest.mark.parametrize(
    "bad", ["12345678901", "1234567890123", "12345678901a", "", "١٢٣٤٥٦٧٨٩٠١٢"]
)
def test_auth_01_hemis_id_must_be_12_ascii_digits_at_db_level(bad: str) -> None:
    direction = make_direction()
    # 13 xona varchar(12) da DataError, qolganlari CHECK — ikkalasi ham DB rad etishi.
    with pytest.raises((IntegrityError, DataError)), transaction.atomic():
        User.objects.bulk_create(
            [User(hemis_id=bad, full_name="X", role=Role.STUDENT, direction=direction)]
        )


def test_auth_01_create_user_strips_whitespace_from_hemis_id() -> None:
    user = User.objects.create_user(
        hemis_id=" 1234 5678 9012\t",
        full_name="Test",
        direction=make_direction(),
        password=PASSWORD,
    )
    assert user.hemis_id == "123456789012"


def test_auth_01_create_user_rejects_bad_hemis_id_before_db() -> None:
    with pytest.raises(ValueError, match="Hemis ID"):
        User.objects.create_user(hemis_id="abc", full_name="Test", password=PASSWORD)


@pytest.mark.parametrize(
    "name",
    [
        "Oʻgʻiloy Gʻaniyeva",  # U+02BB (rasmiy oʻ/gʻ)
        "O'g'iloy G'aniyeva",  # ASCII apostrof
        "Oʼlmas Maʼruf",  # U+02BC tutuq belgisi
        "O‘tkir To‘rayev",  # U+2018 (Word avtozamenasi)
    ],
)
def test_auth_01_full_name_keeps_uzbek_letters_and_apostrophe_variants(name: str) -> None:
    user = make_user(full_name=name)
    user.refresh_from_db()
    assert user.full_name == name


def test_auth_01_full_name_is_nfc_normalized() -> None:
    decomposed = "Jórayev"  # o + birikuvchi aksent
    user = make_user(full_name=f"  {decomposed}  ")
    user.refresh_from_db()
    assert user.full_name == "Jórayev"


def test_auth_01_blank_full_name_rejected_at_db_level() -> None:
    direction = make_direction()
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [User(hemis_id="123456789012", full_name="   ", role=Role.STUDENT, direction=direction)]
        )


def test_auth_01_role_check_constraint_rejects_unknown_role() -> None:
    direction = make_direction()
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [User(hemis_id="123456789012", full_name="X", role="guest", direction=direction)]
        )


def test_auth_01_roles_are_fixed_set() -> None:
    assert set(Role.values) == {"super_admin", "admin", "instructor", "student"}


def test_auth_01_student_requires_direction_at_db_level() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [User(hemis_id="123456789012", full_name="X", role=Role.STUDENT, direction=None)]
        )


def test_auth_01_instructor_may_have_no_direction() -> None:
    user = make_user(role=Role.INSTRUCTOR, direction=None)
    assert user.direction is None


def test_auth_01_direction_is_chosen_from_list_and_protected() -> None:
    user = make_user()
    assert isinstance(user.direction, Direction)
    with pytest.raises(ProtectedError):
        user.direction.delete()


def test_auth_01_direction_name_unique() -> None:
    Direction.objects.create(name="Kompyuter ilmlari")
    with pytest.raises(IntegrityError), transaction.atomic():
        Direction.objects.create(name="Kompyuter ilmlari")


def test_auth_01_superuser_is_super_admin_and_staff() -> None:
    admin = User.objects.create_superuser(
        hemis_id="000000000001", full_name="Admin", password=PASSWORD
    )
    assert admin.role == Role.SUPER_ADMIN
    assert admin.is_superuser
    assert admin.is_staff
    assert admin.direction is None


def test_auth_01_superuser_flag_requires_super_admin_role_at_db_level() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [
                User(
                    hemis_id="123456789012",
                    full_name="X",
                    role=Role.INSTRUCTOR,
                    is_superuser=True,
                )
            ]
        )


@pytest.mark.parametrize(
    ("role", "staff"),
    [(Role.SUPER_ADMIN, True), (Role.ADMIN, True), (Role.INSTRUCTOR, False), (Role.STUDENT, False)],
)
def test_auth_01_is_staff_derived_from_role(role: Role, staff: bool) -> None:
    direction = None if role != Role.STUDENT else make_direction()
    assert User(role=role, direction=direction).is_staff is staff


def test_auth_01_str_does_not_expose_full_name() -> None:
    # Loglarga __str__ orqali FIO tushmasin (NFR-17 maskalash R0-14 da).
    user = make_user()
    assert user.full_name not in str(user)
    assert user.hemis_id not in str(user)


def test_auth_01_login_by_hemis_id() -> None:
    user = make_user(password=PASSWORD)
    assert authenticate(hemis_id=user.hemis_id, password=PASSWORD) == user
    assert authenticate(hemis_id=user.hemis_id, password=PASSWORD + "x") is None


def test_auth_01_inactive_user_cannot_login() -> None:
    user = make_user(password=PASSWORD, is_active=False)
    assert authenticate(hemis_id=user.hemis_id, password=PASSWORD) is None


def test_auth_03_argon2_is_first_hasher_in_base_settings() -> None:
    from config.settings import base

    assert base.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"


def test_auth_03_password_hash_is_argon2_and_never_plaintext() -> None:
    from config.settings import base

    with override_settings(PASSWORD_HASHERS=base.PASSWORD_HASHERS):
        user = make_user(password=PASSWORD)
        user.refresh_from_db()
        assert user.password.startswith("argon2")
        assert PASSWORD not in user.password
        assert user.check_password(PASSWORD)


def test_auth_01_super_admin_role_requires_superuser_flag_at_db_level() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [
                User(
                    hemis_id="123456789012",
                    full_name="X",
                    role=Role.SUPER_ADMIN,
                    is_superuser=False,
                )
            ]
        )


@pytest.mark.parametrize("raw", ["Jo\u0301rayev", " Karimov", "Karimov "])
def test_auth_01_non_canonical_full_name_rejected_at_db_level(raw: str) -> None:
    # save()'ni aylanib o'tgan yozuv (bulk_create, raw SQL) ham NFC va trim'siz saqlanmaydi.
    direction = make_direction()
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [User(hemis_id="123456789012", full_name=raw, role=Role.STUDENT, direction=direction)]
        )


def test_auth_01_direction_name_normalized_and_canonical_at_db_level() -> None:
    assert make_direction("  Sun\u02bciy intellekt ").name == "Sun\u02bciy intellekt"
    with pytest.raises(IntegrityError), transaction.atomic():
        Direction.objects.bulk_create([Direction(name=" Matematika")])


def test_auth_01_full_clean_reports_readable_uzbek_errors() -> None:
    user = User(hemis_id="12ab", full_name="X", role=Role.STUDENT, direction=None)
    user.set_unusable_password()
    with pytest.raises(ValidationError) as exc:
        user.full_clean()
    messages = str(exc.value.message_dict)
    assert "12 ta raqam" in messages
    assert "yo'nalish tanlanishi shart" in messages


def test_auth_01_updated_at_changes_on_save() -> None:
    user = make_user()
    before = user.updated_at
    user.full_name = "Yangi Ism"
    user.save()
    assert user.updated_at > before
