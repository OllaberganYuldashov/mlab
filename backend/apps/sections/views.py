"""Guruh API (I1-02; SEC-01, SEC-08, SET-03).

Obyekt darajasidagi qoida (CLAUDE.md 5.6): o'qituvchi faqat o'z guruhlarini ko'radi va o'zgartiradi,
admin va super admin — hammasini. Begona guruh — 404 (mavjudligi oshkor qilinmaydi).
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers
from rest_framework.exceptions import NotFound
from rest_framework.pagination import CursorPagination
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import Role, User
from apps.accounts.permissions import IsAdmin, IsInstructor, IsSuperAdmin
from apps.audit import record
from apps.audit.models import Action
from apps.courses.models import Course
from apps.sections.models import Membership, MembershipStatus, Section
from apps.sections.serializers import SectionSerializer, SectionUpdateSerializer

EDITABLE = ("name", "capacity", "join_enabled")


class SectionCursorPagination(CursorPagination):
    ordering = "-id"
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


def sections_for(user: User) -> QuerySet[Section]:
    """Foydalanuvchi ko'ra oladigan guruhlar (bitta joyda — har endpoint shu yerdan)."""
    qs = Section.objects.select_related("instructor").annotate(
        approved_count=Count("memberships", filter=Q(memberships__status=MembershipStatus.APPROVED))
    )
    if user.role == Role.INSTRUCTOR:
        return qs.filter(instructor=user)
    if user.role in (Role.ADMIN, Role.SUPER_ADMIN):
        return qs
    return qs.none()


def _snapshot(section: Section) -> dict[str, Any]:
    return {field: getattr(section, field) for field in EDITABLE}


class SectionListCreateView(generics.ListCreateAPIView[Section]):
    serializer_class = SectionSerializer
    pagination_class = SectionCursorPagination
    parser_classes = (JSONParser,)

    def get_permissions(self) -> list[Any]:
        if self.request.method == "POST":
            return [IsInstructor()]
        return [(IsInstructor | IsAdmin | IsSuperAdmin)()]

    def get_queryset(self) -> QuerySet[Section]:
        return sections_for(self.request.user)  # type: ignore[arg-type]

    def perform_create(self, serializer: serializers.BaseSerializer[Section]) -> None:
        # MVP'da bitta kurs (SRS 1): import qilinmagan bo'lsa — tushunarli xato.
        course = Course.objects.order_by("id").first()
        if course is None:
            raise serializers.ValidationError(
                {"course": [_("Kurs hali import qilinmagan. Administratorga murojaat qiling.")]}
            )
        with transaction.atomic():
            section = serializer.save(instructor=self.request.user, course=course)
            record(
                Action.SECTION_CREATED,
                actor=self.request.user,  # type: ignore[arg-type]
                target=section,
                after=_snapshot(section),
            )
        section.approved_count = 0  # type: ignore[attr-defined]


class SectionDetailView(generics.RetrieveUpdateAPIView[Section]):
    serializer_class = SectionUpdateSerializer
    permission_classes = ((IsInstructor | IsAdmin | IsSuperAdmin),)
    parser_classes = (JSONParser,)
    http_method_names = ("get", "patch", "options", "head")
    lookup_url_kwarg = "section_id"

    def get_queryset(self) -> QuerySet[Section]:
        return sections_for(self.request.user)  # type: ignore[arg-type]

    @extend_schema(summary="Guruhni o'zgartirish (nomi, sig'im, qo'shilish)")
    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        with transaction.atomic():
            # Qatorni qulflab qayta o'qish: parallel tasdiqlash (I1-05) bilan ham sig'im to'g'ri.
            visible = (
                self.get_queryset().filter(pk=kwargs["section_id"]).values_list("pk", flat=True)
            )
            section = Section.objects.select_for_update().filter(pk__in=list(visible)).first()
            if section is None:
                raise NotFound
            serializer = self.get_serializer(section, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            new_capacity = serializer.validated_data.get("capacity")
            approved = Membership.objects.approved().filter(section=section).count()
            if new_capacity is not None and new_capacity < approved:
                raise serializers.ValidationError(
                    {
                        "capacity": [
                            _(
                                "Sig'im tasdiqlangan a'zolar sonidan ({count}) kam bo'lmaydi."
                            ).format(count=approved)
                        ]
                    }
                )
            before = _snapshot(section)
            serializer.save()
            after = _snapshot(section)
            if before != after:
                changed = [k for k in EDITABLE if before[k] != after[k]]
                record(
                    Action.SECTION_UPDATED,
                    actor=request.user,  # type: ignore[arg-type]
                    target=section,
                    before={k: before[k] for k in changed},
                    after={k: after[k] for k in changed},
                )
        section.approved_count = approved  # type: ignore[attr-defined]
        return Response(self.get_serializer(section).data)
