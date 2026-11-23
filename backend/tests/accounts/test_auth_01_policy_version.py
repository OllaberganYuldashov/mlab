"""AUTH-01 (R0-10): siyosat versiyasi ochiq endpoint orqali — Consent bilan bir manba."""

from __future__ import annotations

import pytest
from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_auth_01_policy_version_is_public_and_matches_setting() -> None:
    response = APIClient().get("/api/policy")
    assert response.status_code == 200
    assert response.json() == {"version": settings.PRIVACY_POLICY_VERSION}


@override_settings(PRIVACY_POLICY_VERSION="2030-01-01")
def test_auth_01_policy_version_follows_setting() -> None:
    assert APIClient().get("/api/policy").json() == {"version": "2030-01-01"}
