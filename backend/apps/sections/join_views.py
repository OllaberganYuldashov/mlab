"""Havola orqali qo'shilish (I1-04; SEC-03, SEC-06, SEC-07) va talabaning a'zolik holati."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.net import client_ip
from apps.accounts.permissions import IsStudent
from apps.sections.models import Membership, Section
from apps.sections.services import JoinRefused, approved_count, request_membership
from apps.sections.tokens import find_section_by_token


class JoinPreviewThrottle(SimpleRateThrottle):
    """Ko'rish — IP bo'yicha, keng: kompyuter xonasi bitta NAT ortida (token 128 bit, taxminsiz)."""

    scope = "section-join-preview"

    def get_rate(self) -> str:
        return str(settings.SECTION_JOIN_PREVIEW_RATE)

    def allow_request(self, request: Request, view: APIView) -> bool:
        return request.method != "GET" or super().allow_request(request, view)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": client_ip(request)}


class JoinRequestThrottle(SimpleRateThrottle):
    """So'rov — talaba bo'yicha: bir sinfdagi boshqa talabalarning limitini yemaydi."""

    scope = "section-join-request"

    def get_rate(self) -> str:
        return str(settings.SECTION_JOIN_RATE)

    def allow_request(self, request: Request, view: APIView) -> bool:
        return request.method != "POST" or super().allow_request(request, view)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.pk)}


def _section_or_404(token: str) -> Section:
    section = find_section_by_token(token)
    if section is None:
        raise NotFound
    return section


def _membership_payload(membership: Membership) -> dict[str, Any]:
    return {
        "id": membership.pk,
        "status": membership.status,
        "section": membership.section.name,
        "instructor": membership.section.instructor.full_name,
        "requested_at": membership.requested_at,
        "decided_at": membership.decided_at,
    }


MembershipOut = inline_serializer(
    "MyMembership",
    {
        "id": serializers.IntegerField(),
        "status": serializers.CharField(),
        "section": serializers.CharField(),
        "instructor": serializers.CharField(),
        "requested_at": serializers.DateTimeField(),
        "decided_at": serializers.DateTimeField(allow_null=True),
    },
)


class JoinView(APIView):
    throttle_classes = (JoinPreviewThrottle, JoinRequestThrottle)

    def get_permissions(self) -> list[Any]:
        return [AllowAny()] if self.request.method == "GET" else [IsStudent()]

    @extend_schema(
        responses={
            200: inline_serializer(
                "JoinPreview",
                {
                    "section": serializers.CharField(),
                    "instructor": serializers.CharField(),
                    "join_enabled": serializers.BooleanField(),
                    "is_full": serializers.BooleanField(),
                },
            )
        },
        summary="Havola bo'yicha guruhni ko'rish",
    )
    def get(self, request: Request, token: str) -> Response:
        section = _section_or_404(token)
        # SEC-03: guruh nomi va o'qituvchi ko'rinadi (kirishdan oldin ham — talaba to'g'ri guruhni
        # tanlashi uchun). Proksi keshlamaydi: holat (`is_full`) eskirmasin.
        response = Response(
            {
                "section": section.name,
                "instructor": section.instructor.full_name,
                "join_enabled": section.join_enabled,
                "is_full": approved_count(section) >= section.capacity,
            }
        )
        response["Cache-Control"] = "no-store"
        return response

    @extend_schema(
        request=None,
        responses={
            200: MembershipOut,
            201: MembershipOut,
            409: inline_serializer(
                "JoinRefused", {"code": serializers.CharField(), "detail": serializers.CharField()}
            ),
        },
        summary="A'zolik so'rovini yuborish",
    )
    def post(self, request: Request, token: str) -> Response:
        section = _section_or_404(token)
        student = request.user
        assert isinstance(student, User)  # IsStudent kafolatlaydi  # noqa: S101
        try:
            membership, created = request_membership(student, section.pk)
        except Section.DoesNotExist as missing:
            raise NotFound from missing
        except JoinRefused as refused:
            return Response(
                {"code": refused.code, "detail": refused.detail}, status=status.HTTP_409_CONFLICT
            )
        return Response(
            _membership_payload(membership),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MyMembershipView(APIView):
    permission_classes = (IsStudent,)

    @extend_schema(
        responses={200: inline_serializer("MyMembershipEnvelope", {"membership": MembershipOut})},
        summary="Talabaning oxirgi a'zoligi va holati",
    )
    def get(self, request: Request) -> Response:
        membership = (
            Membership.objects.select_related("section__instructor")
            .filter(student=request.user)  # type: ignore[misc]
            .order_by("-requested_at", "-id")
            .first()
        )
        return Response({"membership": _membership_payload(membership) if membership else None})
