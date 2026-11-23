"""AUTH-01, SRS 7-bo'lim (R0-06): ro'yxatdan o'tish API, rozilik, yo'nalishlar ro'yxati."""

from __future__ import annotations

import secrets
from typing import Any

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Consent, Role, User
from tests.accounts.factories import make_direction, make_user

pytestmark = pytest.mark.django_db

URL = "/api/auth/register"
PASSWORD = secrets.token_urlsafe(12)


@pytest.fixture(autouse=True)
def _clear_throttle() -> None:
    cache.clear()


@pytest.fixture
def api() -> APIClient:
    return APIClient()


def _payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "hemis_id": "123456789012",
        "full_name": "Oʻgʻiloy Gʻaniyeva",
        "direction": make_direction().pk,
        "password": PASSWORD,
        "consent": True,
        "policy_version": settings.PRIVACY_POLICY_VERSION,
    }
    data.update(overrides)
    return data


def test_auth_01_register_creates_student_with_consent(api: APIClient) -> None:
    response = api.post(URL, _payload(), format="json")
    assert response.status_code == 201
    user = User.objects.get(hemis_id="123456789012")
    assert user.role == Role.STUDENT
    assert not user.is_superuser
    assert user.check_password(PASSWORD)
    consent = Consent.objects.get(user=user)
    assert consent.policy_version == settings.PRIVACY_POLICY_VERSION
    assert consent.accepted_at is not None
    body = response.json()
    assert body == {
        "hemis_id": "123456789012",
        "full_name": "Oʻgʻiloy Gʻaniyeva",
        "role": "student",
        "direction": user.direction_id,
    }
    assert PASSWORD not in response.content.decode()


def test_auth_01_register_does_not_log_in(api: APIClient) -> None:
    api.post(URL, _payload(), format="json")
    assert "sessionid" not in api.cookies


@pytest.mark.parametrize(
    "extra",
    [
        {"role": "super_admin"},
        {"role": "admin", "is_superuser": True},
        {"is_staff": True, "is_active": False},
    ],
)
def test_auth_01_mass_assignment_ignored(api: APIClient, extra: dict[str, Any]) -> None:
    response = api.post(URL, _payload(**extra), format="json")
    assert response.status_code == 201
    user = User.objects.get(hemis_id="123456789012")
    assert user.role == Role.STUDENT
    assert not user.is_superuser
    assert user.is_active


@pytest.mark.parametrize("consent", [False, None, "false", ""])
def test_auth_01_register_without_consent_rejected(api: APIClient, consent: Any) -> None:
    data = _payload(consent=consent)
    if consent is None:
        data.pop("consent")
    response = api.post(URL, data, format="json")
    assert response.status_code == 400
    assert "consent" in response.json()
    assert not User.objects.exists()
    assert not Consent.objects.exists()


def test_auth_01_stale_policy_version_rejected(api: APIClient) -> None:
    response = api.post(URL, _payload(policy_version="2000-01-01"), format="json")
    assert response.status_code == 400
    assert "policy_version" in response.json()
    assert not User.objects.exists()


def test_auth_01_duplicate_hemis_id_rejected(api: APIClient) -> None:
    make_user(hemis_id="123456789012")
    response = api.post(URL, _payload(hemis_id=" 1234 5678 9012 "), format="json")
    assert response.status_code == 400
    assert "allaqachon" in str(response.json()["hemis_id"])
    assert User.objects.count() == 1


@pytest.mark.parametrize("hemis_id", ["12345", "abcdefghijkl", "1234567890123", ""])
def test_auth_01_invalid_hemis_id_rejected(api: APIClient, hemis_id: str) -> None:
    response = api.post(URL, _payload(hemis_id=hemis_id), format="json")
    assert response.status_code == 400
    assert "hemis_id" in response.json()


def test_auth_01_hemis_id_whitespace_stripped(api: APIClient) -> None:
    response = api.post(URL, _payload(hemis_id="1234 5678 9012"), format="json")
    assert response.status_code == 201
    assert User.objects.filter(hemis_id="123456789012").exists()


@pytest.mark.parametrize("password", ["12345678", "qwerty", "password123"])
def test_auth_01_weak_password_rejected_by_django_validators(api: APIClient, password: str) -> None:
    response = api.post(URL, _payload(password=password), format="json")
    assert response.status_code == 400
    assert "password" in response.json()


def test_auth_01_password_similar_to_hemis_id_rejected(api: APIClient) -> None:
    response = api.post(URL, _payload(password="123456789012a"), format="json")
    assert response.status_code == 400


def test_auth_01_unknown_direction_rejected(api: APIClient) -> None:
    response = api.post(URL, _payload(direction=999999), format="json")
    assert response.status_code == 400
    assert "direction" in response.json()


@pytest.mark.parametrize("full_name", ["", "   ", "x" * 151])
def test_auth_01_invalid_full_name_rejected(api: APIClient, full_name: str) -> None:
    response = api.post(URL, _payload(full_name=full_name), format="json")
    assert response.status_code == 400
    assert "full_name" in response.json()


@override_settings(AUTH_REGISTER_RATE="10/hour")
def test_auth_01_register_is_throttled(api: APIClient) -> None:
    statuses = [
        api.post(URL, _payload(hemis_id=f"{i:012d}"), format="json").status_code
        for i in range(1, 13)
    ]
    assert statuses.count(201) == 10
    assert statuses[-1] == 429


def test_auth_01_default_rate_fits_a_computer_lab_behind_one_nat() -> None:
    # Bir xonadagi 30 talaba bitta IP orqali bir vaqtda ro'yxatdan o'tadi.
    count, period = settings.AUTH_REGISTER_RATE.split("/")
    assert int(count) >= 60
    assert period == "hour"


def test_auth_01_register_only_post(api: APIClient) -> None:
    assert api.get(URL).status_code == 405


# --- Yo'nalishlar ---


def test_auth_01_directions_list_public_and_sorted(api: APIClient) -> None:
    make_direction("Matematika")
    make_direction("Kompyuter ilmlari")
    response = api.get("/api/directions")
    assert response.status_code == 200
    assert [d["name"] for d in response.json()] == ["Kompyuter ilmlari", "Matematika"]
    assert set(response.json()[0]) == {"id", "name"}


def test_auth_01_directions_read_only(api: APIClient) -> None:
    assert api.post("/api/directions", {"name": "X"}, format="json").status_code == 405


# --- OpenAPI ---


def test_openapi_schema_restricted_to_staff(api: APIClient) -> None:
    assert api.get("/api/schema/").status_code in (401, 403)
    api.force_authenticate(make_user())
    assert api.get("/api/schema/").status_code == 403
    api.force_authenticate(make_user(role=Role.ADMIN, direction=None))
    response = api.get("/api/schema/")
    assert response.status_code == 200
    assert b"/api/auth/register" in response.content


def test_openapi_committed_schema_is_up_to_date() -> None:
    # docs/openapi.yaml har API o'zgarishida yangilanadi (DoD): farq bo'lsa test yiqiladi.
    from io import StringIO
    from pathlib import Path

    from django.core.management import call_command

    out = StringIO()
    call_command("spectacular", "--validate", "--fail-on-warn", stdout=out)
    committed = Path(settings.BASE_DIR).parent / "docs" / "openapi.yaml"
    assert committed.read_text(encoding="utf-8") == out.getvalue(), (
        "OpenAPI eskirgan: cd backend && uv run python manage.py spectacular "
        "--validate --file ../docs/openapi.yaml"
    )


def test_auth_01_concurrent_duplicate_returns_400_not_500() -> None:
    # Ikki so'rov bir vaqtda: tekshiruvdan keyin, saqlashdan oldin boshqasi yaratib ulgurdi.
    from rest_framework.exceptions import ValidationError

    from apps.accounts.serializers import RegisterSerializer

    serializer = RegisterSerializer(data=_payload())
    assert serializer.is_valid(), serializer.errors
    make_user(hemis_id="123456789012")
    with pytest.raises(ValidationError) as exc:
        serializer.save()
    assert "hemis_id" in exc.value.detail
    assert not Consent.objects.exists()


# --- security-reviewer tavsiyalari ---


@override_settings(AUTH_REGISTER_RATE="2/hour")
def test_auth_01_spoofed_forwarded_for_does_not_bypass_throttle(api: APIClient) -> None:
    # NUM_PROXIES=0: X-Forwarded-For e'tiborga olinmaydi — soxta IP limitni yangilamaydi.
    statuses = [
        api.post(
            URL,
            _payload(hemis_id=f"{i:012d}"),
            format="json",
            HTTP_X_FORWARDED_FOR=f"10.0.0.{i}",
        ).status_code
        for i in range(1, 4)
    ]
    assert statuses == [201, 201, 429]


@override_settings(AUTH_REGISTER_RATE="1/hour")
def test_auth_01_ipv6_throttled_per_64_prefix(api: APIClient) -> None:
    first = api.post(
        URL, _payload(hemis_id="000000000001"), format="json", REMOTE_ADDR="2001:db8:1:2::1"
    )
    same_net = api.post(
        URL, _payload(hemis_id="000000000002"), format="json", REMOTE_ADDR="2001:db8:1:2::ffff"
    )
    other_net = api.post(
        URL, _payload(hemis_id="000000000003"), format="json", REMOTE_ADDR="2001:db8:1:3::1"
    )
    assert (first.status_code, same_net.status_code, other_net.status_code) == (201, 429, 201)


@override_settings(AUTH_REGISTER_RATE="100/hour", AUTH_REGISTER_GLOBAL_RATE="2/hour")
def test_auth_01_global_register_cap(api: APIClient) -> None:
    statuses = [
        api.post(
            URL, _payload(hemis_id=f"{i:012d}"), format="json", REMOTE_ADDR=f"10.1.0.{i}"
        ).status_code
        for i in range(1, 4)
    ]
    assert statuses == [201, 201, 429]


def test_auth_01_form_encoded_post_rejected(api: APIClient) -> None:
    # Boshqa saytdagi HTML forma (preflight'siz) ishlamaydi: faqat JSON.
    response = api.post(URL, _payload())
    assert response.status_code == 415
    assert not User.objects.exists()


def test_auth_01_non_duplicate_integrity_error_is_not_masked() -> None:
    from unittest import mock

    from django.db import IntegrityError

    from apps.accounts.serializers import RegisterSerializer

    serializer = RegisterSerializer(data=_payload())
    assert serializer.is_valid(), serializer.errors
    with (
        mock.patch.object(User.objects, "create_user", side_effect=IntegrityError("boshqa")),
        pytest.raises(IntegrityError),
    ):
        serializer.save()
