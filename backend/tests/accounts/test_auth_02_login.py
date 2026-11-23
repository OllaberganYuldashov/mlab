"""AUTH-02, NFR-10, ADM-02 (R0-07): kirish/chiqish, CSRF, lockout (Hemis ID + IP), audit."""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from apps.accounts import lockout
from apps.accounts.models import Role, User
from apps.audit.models import Action, AuditLog
from tests.accounts.factories import make_user

pytestmark = pytest.mark.django_db

PASSWORD = secrets.token_urlsafe(12)
LOGIN = "/api/auth/login"
GENERIC = "Hemis ID yoki parol noto'g'ri."


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


@pytest.fixture
def csrf_client() -> Client:
    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/csrf")
    return client


def _post(client: Client, url: str, data: dict[str, Any] | None = None, **extra: Any) -> Any:
    token = client.cookies["csrftoken"].value
    return client.post(
        url, data or {}, content_type="application/json", HTTP_X_CSRFTOKEN=token, **extra
    )


def _login(client: Client, hemis_id: str, password: str, **extra: Any) -> Any:
    return _post(client, LOGIN, {"hemis_id": hemis_id, "password": password}, **extra)


@pytest.fixture
def student() -> User:
    return make_user(hemis_id="123456789012", password=PASSWORD)


# --- Kirish / chiqish / me ---


def test_auth_02_csrf_endpoint_sets_cookie() -> None:
    client = Client()
    response = client.get("/api/auth/csrf")
    assert response.status_code == 204
    assert "csrftoken" in response.cookies


def test_auth_02_login_success_sets_session_and_me(csrf_client: Client, student: User) -> None:
    response = _login(csrf_client, " 1234 5678 9012 ", PASSWORD)
    assert response.status_code == 200
    assert response.json()["hemis_id"] == "123456789012"
    assert response.cookies["sessionid"]["httponly"]
    assert response.cookies["sessionid"]["samesite"] == "Lax"
    me = csrf_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {
        "hemis_id": "123456789012",
        "full_name": student.full_name,
        "role": "student",
        "direction": student.direction_id,
        "must_change_password": False,
    }


def test_auth_02_login_rotates_session_key(csrf_client: Client, student: User) -> None:
    csrf_client.session.save()
    before = csrf_client.session.session_key
    _login(csrf_client, student.hemis_id, PASSWORD)
    assert csrf_client.session.session_key != before


def test_auth_02_login_requires_csrf(student: User) -> None:
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        LOGIN,
        {"hemis_id": student.hemis_id, "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert "_auth_user_id" not in client.session


def test_auth_02_me_requires_login() -> None:
    assert Client().get("/api/auth/me").status_code == 403


def test_auth_02_logout(csrf_client: Client, student: User) -> None:
    _login(csrf_client, student.hemis_id, PASSWORD)
    response = _post(csrf_client, "/api/auth/logout")
    assert response.status_code == 204
    assert csrf_client.get("/api/auth/me").status_code == 403
    assert AuditLog.objects.filter(action=Action.LOGOUT, actor=student).exists()


def test_auth_02_logout_requires_csrf(csrf_client: Client, student: User) -> None:
    _login(csrf_client, student.hemis_id, PASSWORD)
    response = csrf_client.post("/api/auth/logout")
    assert response.status_code == 403


# --- Bir xil xato javobi (foydalanuvchi bor-yo'qligi oshkor qilinmaydi) ---


@pytest.mark.parametrize(
    ("hemis_id", "password"),
    [
        ("123456789012", "noto-g-ri-parol"),  # mavjud, parol xato
        ("999999999999", PASSWORD),  # mavjud emas
        ("abc", PASSWORD),  # format noto'g'ri
    ],
)
def test_auth_02_failure_response_is_identical(
    csrf_client: Client, student: User, hemis_id: str, password: str
) -> None:
    response = _login(csrf_client, hemis_id, password)
    assert response.status_code == 400
    assert response.json() == {"detail": GENERIC}


def test_auth_02_inactive_user_gets_same_generic_error(csrf_client: Client) -> None:
    make_user(hemis_id="123456789012", password=PASSWORD, is_active=False)
    response = _login(csrf_client, "123456789012", PASSWORD)
    assert response.status_code == 400
    assert response.json() == {"detail": GENERIC}


def test_auth_02_missing_fields(csrf_client: Client) -> None:
    response = _post(csrf_client, LOGIN, {})
    assert response.status_code == 400


# --- Lockout: 5 xato -> 15 daqiqa, kalit Hemis ID + IP ---


def _fail(client: Client, n: int, hemis_id: str = "123456789012", **extra: Any) -> None:
    for _ in range(n):
        assert _login(client, hemis_id, "xato-parol", **extra).status_code == 400


def test_auth_02_lockout_after_5_failures_even_with_correct_password(
    csrf_client: Client, student: User
) -> None:
    _fail(csrf_client, 5)
    response = _login(csrf_client, student.hemis_id, PASSWORD)
    assert response.status_code == 429
    assert "15 daqiqa" in response.json()["detail"]
    assert "_auth_user_id" not in csrf_client.session


def test_auth_02_four_failures_do_not_lock(csrf_client: Client, student: User) -> None:
    _fail(csrf_client, 4)
    assert _login(csrf_client, student.hemis_id, PASSWORD).status_code == 200


def test_auth_02_success_resets_failure_counter(csrf_client: Client, student: User) -> None:
    _fail(csrf_client, 4)
    assert _login(csrf_client, student.hemis_id, PASSWORD).status_code == 200
    _post(csrf_client, "/api/auth/logout")
    csrf_client.get("/api/auth/csrf")
    _fail(csrf_client, 4)
    assert _login(csrf_client, student.hemis_id, PASSWORD).status_code == 200


def test_auth_02_lockout_expires_after_15_minutes(csrf_client: Client, student: User) -> None:
    start = timezone.now()
    with mock.patch.object(lockout, "now", return_value=start):
        _fail(csrf_client, 5)
    with mock.patch.object(lockout, "now", return_value=start + timedelta(minutes=14, seconds=59)):
        assert _login(csrf_client, student.hemis_id, PASSWORD).status_code == 429
    with mock.patch.object(lockout, "now", return_value=start + timedelta(minutes=15, seconds=1)):
        assert _login(csrf_client, student.hemis_id, PASSWORD).status_code == 200


def test_auth_02_lockout_is_per_hemis_id_and_ip(csrf_client: Client, student: User) -> None:
    # Egasining qarori: begona IP'dan 5 xato talabaning o'z kompyuterini bloklamaydi.
    _fail(csrf_client, 5, REMOTE_ADDR="10.0.0.66")
    assert (
        _login(csrf_client, student.hemis_id, PASSWORD, REMOTE_ADDR="10.0.0.66").status_code == 429
    )
    assert (
        _login(csrf_client, student.hemis_id, PASSWORD, REMOTE_ADDR="10.0.0.7").status_code == 200
    )


def test_auth_02_lockout_does_not_spill_to_other_accounts(csrf_client: Client) -> None:
    make_user(hemis_id="111111111111", password=PASSWORD)
    _fail(csrf_client, 5)
    assert _login(csrf_client, "111111111111", PASSWORD).status_code == 200


def test_auth_02_lockout_also_for_unknown_hemis_id(csrf_client: Client) -> None:
    # Bloklash mavjud bo'lmagan ID uchun ham bir xil — bu orqali ham ID borligi bilinmaydi.
    _fail(csrf_client, 5, hemis_id="999999999999")
    assert _login(csrf_client, "999999999999", "x").status_code == 429


def test_auth_02_lockout_applies_to_admin_login(student: User) -> None:
    admin_user = make_user(role=Role.ADMIN, direction=None, password=PASSWORD)
    client = Client()
    for _ in range(5):
        client.post("/admin/login/", {"username": admin_user.hemis_id, "password": "xato"})
    response = client.post("/admin/login/", {"username": admin_user.hemis_id, "password": PASSWORD})
    assert response.status_code == 200  # forma qayta ko'rsatiladi — kirish yo'q
    assert "_auth_user_id" not in client.session


# --- Audit ---


def test_auth_02_successful_login_audited(csrf_client: Client, student: User) -> None:
    _login(csrf_client, student.hemis_id, PASSWORD, REMOTE_ADDR="10.2.3.4")
    entry = AuditLog.objects.get(action=Action.LOGIN)
    assert entry.actor == student
    assert entry.target_id == str(student.pk)
    assert entry.after == {"ip": "10.2.3.x"}


def test_auth_02_failed_login_for_existing_user_audited(csrf_client: Client, student: User) -> None:
    _fail(csrf_client, 1)
    entry = AuditLog.objects.get(action=Action.LOGIN_FAILED)
    assert entry.actor is None
    assert entry.target_id == str(student.pk)
    assert "xato-parol" not in str(entry.before) + str(entry.after)


def test_auth_02_failed_login_for_unknown_id_not_audited(csrf_client: Client) -> None:
    _fail(csrf_client, 1, hemis_id="999999999999")
    assert not AuditLog.objects.filter(action=Action.LOGIN_FAILED).exists()


def test_auth_02_admin_login_audited(student: User) -> None:
    admin_user = make_user(role=Role.ADMIN, direction=None, password=PASSWORD)
    client = Client()
    response = client.post("/admin/login/", {"username": admin_user.hemis_id, "password": PASSWORD})
    assert response.status_code == 302
    assert AuditLog.objects.filter(action=Action.LOGIN, actor=admin_user).exists()


def test_auth_02_session_cookie_settings() -> None:
    from django.conf import settings

    assert settings.SESSION_COOKIE_HTTPONLY
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.AUTHENTICATION_BACKENDS == ["apps.accounts.backends.LockoutModelBackend"]


def test_auth_02_client_ip_behind_one_trusted_proxy() -> None:
    from django.conf import settings
    from django.test import RequestFactory, override_settings

    from apps.accounts.net import client_ip

    factory = RequestFactory()
    spoofed = factory.get("/", REMOTE_ADDR="172.18.0.2", HTTP_X_FORWARDED_FOR="6.6.6.6, 10.9.8.7")
    with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}):
        # Caddy oxirgi elementni qo'shadi; mijoz yozgan "6.6.6.6" e'tiborga olinmaydi.
        assert client_ip(spoofed) == "10.9.8.7"
        assert client_ip(factory.get("/", REMOTE_ADDR="172.18.0.2")) == "172.18.0.2"
    assert client_ip(spoofed) == "172.18.0.2"


# --- security-reviewer tavsiyalari ---


def test_auth_02_parallel_guesses_cannot_exceed_5_attempts() -> None:
    # Poyga: 20 ta parallel urinish — faqat 5 tasi parolni tekshirishgacha yetadi (atomik INCR).
    from concurrent.futures import ThreadPoolExecutor

    def attempt(_: int) -> bool:
        return lockout.begin("123456789012", "10.0.0.1").allowed

    with ThreadPoolExecutor(max_workers=20) as pool:
        allowed = list(pool.map(attempt, range(20)))
    assert allowed.count(True) == 5
    assert lockout.is_locked("123456789012", "10.0.0.1")


def test_auth_02_success_does_not_consume_attempts() -> None:
    for _ in range(10):
        attempt = lockout.begin("123456789012", "10.0.0.1")
        assert attempt.allowed
        lockout.succeeded("123456789012", "10.0.0.1")


def test_auth_02_ip_rate_applies_to_admin_login_across_hemis_ids() -> None:
    # Password spraying: bitta IP'dan ko'p Hemis ID — admin login'da ham IP chegarasi ishlaydi.
    from django.test import override_settings

    admin_user = make_user(role=Role.ADMIN, direction=None, password=PASSWORD)
    client = Client()
    with override_settings(AUTH_LOGIN_RATE="3/minute"):
        for i in range(3):
            client.post("/admin/login/", {"username": f"{i:012d}", "password": "x"})
        client.post("/admin/login/", {"username": admin_user.hemis_id, "password": PASSWORD})
    assert "_auth_user_id" not in client.session


def test_auth_02_global_login_cap() -> None:
    from django.test import override_settings

    with override_settings(AUTH_LOGIN_GLOBAL_RATE="2/minute"):
        assert not lockout.over_rate("10.0.0.1")
        assert not lockout.over_rate("10.0.0.2")
        assert lockout.over_rate("10.0.0.3")


def test_auth_02_ipv6_lockout_per_64(csrf_client: Client, student: User) -> None:
    _fail(csrf_client, 5, REMOTE_ADDR="2001:db8:1:2::1")
    same_net = _login(csrf_client, student.hemis_id, PASSWORD, REMOTE_ADDR="2001:db8:1:2::abcd")
    assert same_net.status_code == 429


def test_auth_02_ipv4_mapped_ipv6_is_same_client() -> None:
    from django.test import RequestFactory

    from apps.accounts.net import client_ip

    factory = RequestFactory()
    assert client_ip(factory.get("/", REMOTE_ADDR="::ffff:10.0.0.5")) == "10.0.0.5"
    assert client_ip(factory.get("/", REMOTE_ADDR="2001:db8:1:2::1")) == "2001:db8:1:2::/64"
    assert client_ip(factory.get("/", REMOTE_ADDR="bad")) == "bad"


def test_auth_02_failed_login_audit_only_first_and_lock(csrf_client: Client, student: User) -> None:
    _fail(csrf_client, 5)
    _login(csrf_client, student.hemis_id, PASSWORD)  # blok paytida — yozilmaydi
    entries = list(AuditLog.objects.filter(action=Action.LOGIN_FAILED).order_by("id"))
    assert [e.after["lock_started"] for e in entries] == [False, True]


def test_auth_02_session_lifetime_12_hours() -> None:
    from django.conf import settings

    assert settings.SESSION_COOKIE_AGE == 12 * 60 * 60
