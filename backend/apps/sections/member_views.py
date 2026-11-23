"""A'zolar ro'yxati va qaror (I1-05; SEC-04, SEC-06, SEC-08).

Faqat ko'rinadigan guruh (begona — 404).
"""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import CursorPagination
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin, IsInstructor, IsSuperAdmin
from apps.sections.models import Membership, MembershipStatus
from apps.sections.services import JoinRefused, decide_memberships
from apps.sections.views import sections_for

MAX_BULK = 500
STAFF_OR_INSTRUCTOR = (IsInstructor | IsAdmin | IsSuperAdmin,)


class StudentBriefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    hemis_id = serializers.CharField()
    full_name = serializers.CharField()


class MemberSerializer(serializers.ModelSerializer[Membership]):
    student = StudentBriefSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "student", "status", "requested_at", "decided_at")
        read_only_fields = fields


class MemberCursorPagination(CursorPagination):
    ordering = "id"
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 200


class DecideSerializer(serializers.Serializer[Any]):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), min_length=1, max_length=MAX_BULK
    )
    decision = serializers.ChoiceField(choices=("approve", "reject"))


def _visible_section_id(user: Any, section_id: int) -> int:
    if not sections_for(user).filter(pk=section_id).exists():
        raise NotFound
    return section_id


@extend_schema(
    parameters=[
        OpenApiParameter("status", enum=["pending", "approved"], required=False, default="pending")
    ]
)
class MemberListView(generics.ListAPIView[Membership]):
    serializer_class = MemberSerializer
    permission_classes = STAFF_OR_INSTRUCTOR
    pagination_class = MemberCursorPagination

    def get_queryset(self) -> QuerySet[Membership]:
        section_id = _visible_section_id(self.request.user, self.kwargs["section_id"])
        wanted = self.request.query_params.get("status", MembershipStatus.PENDING)
        if wanted not in (MembershipStatus.PENDING, MembershipStatus.APPROVED):
            raise serializers.ValidationError({"status": ["pending yoki approved"]})
        return Membership.objects.select_related("student").filter(
            section_id=section_id, status=wanted
        )


class DecideView(APIView):
    permission_classes = STAFF_OR_INSTRUCTOR
    parser_classes = (JSONParser,)

    @extend_schema(
        request=DecideSerializer,
        responses={
            200: inline_serializer(
                "DecideResult",
                {
                    "approved": serializers.ListField(child=serializers.IntegerField()),
                    "rejected": serializers.ListField(child=serializers.IntegerField()),
                    "skipped": serializers.ListField(child=serializers.IntegerField()),
                },
            ),
            409: inline_serializer(
                "DecideRefused",
                {"code": serializers.CharField(), "detail": serializers.CharField()},
            ),
        },
        summary="So'rovlarni tasdiqlash yoki rad etish (bittalab yoki ommaviy)",
    )
    def post(self, request: Request, section_id: int) -> Response:
        _visible_section_id(request.user, section_id)
        payload = DecideSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = request.user
        assert isinstance(actor, User)  # noqa: S101
        try:
            result = decide_memberships(
                actor,
                section_id,
                list(dict.fromkeys(payload.validated_data["ids"])),
                approve=payload.validated_data["decision"] == "approve",
            )
        except JoinRefused as refused:
            return Response(
                {"code": refused.code, "detail": refused.detail}, status=status.HTTP_409_CONFLICT
            )
        return Response(
            {"approved": result.approved, "rejected": result.rejected, "skipped": result.skipped}
        )
