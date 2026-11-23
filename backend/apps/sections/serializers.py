"""Guruh API serializer'lari (I1-02).

`course` va `instructor` faqat o'qiladi (mass assignment yo'q).
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.accounts.models import normalize_full_name
from apps.sections.models import MAX_CAPACITY, MIN_CAPACITY, Section


class InstructorBriefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class SectionSerializer(serializers.ModelSerializer[Section]):
    instructor = InstructorBriefSerializer(read_only=True)
    approved_count = serializers.IntegerField(read_only=True, default=0)
    has_join_token = serializers.SerializerMethodField()
    capacity = serializers.IntegerField(
        min_value=MIN_CAPACITY, max_value=MAX_CAPACITY, required=False
    )

    class Meta:
        model = Section
        fields = (
            "id",
            "name",
            "direction",
            "course",
            "instructor",
            "capacity",
            "join_enabled",
            "approved_count",
            "has_join_token",
            "created_at",
        )
        read_only_fields: tuple[str, ...] = (
            "id",
            "course",
            "instructor",
            "approved_count",
            "has_join_token",
            "created_at",
        )

    def get_has_join_token(self, section: Section) -> bool:
        return section.join_token_hash is not None

    def validate_name(self, value: str) -> str:
        name = normalize_full_name(value)
        if not name:
            raise serializers.ValidationError(_("Guruh nomi bo'sh bo'lmasligi kerak."))
        return name


class SectionUpdateSerializer(SectionSerializer):
    class Meta(SectionSerializer.Meta):
        read_only_fields = (*SectionSerializer.Meta.read_only_fields, "direction")


class JoinTokenSerializer(serializers.Serializer[Any]):
    token = serializers.CharField()
    join_path = serializers.CharField()
