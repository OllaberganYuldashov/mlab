"""Talabaning topshirig'i (I3-04; AGR-01, AGR-05, LAB-07).

`GET /api/labs/{mavzu}/assignment` — shart (variant parametrlari bilan), qadamlar va faqat
ko'rinadigan testlar. Yashirin testlar so'rovga umuman kirmaydi (AGR-05). Variant birinchi
ochilishda beriladi (`variants.assign`) va keyin o'zgarmaydi (AGR-08).
Laboratoriya yopiq bo'lsa — 403 `lab_closed` (variant ham berilmaydi).
"""

from __future__ import annotations

import string
from typing import Any

from django.db.models import Prefetch
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudent
from apps.grading import variants
from apps.grading.models import Assignment, AssignmentStep, TestFile, TestKind
from apps.labs.views import _student_context
from apps.sections.policy import SubmissionStatus, submission_policy


class AssignmentStepOut(serializers.Serializer[dict[str, Any]]):
    key = serializers.CharField()
    title = serializers.CharField()
    points = serializers.IntegerField()
    visible_test = serializers.CharField(allow_null=True)


AssignmentOut = inline_serializer(
    "MyAssignmentOut",
    {
        "code": serializers.CharField(),
        "title": serializers.CharField(),
        "level": serializers.CharField(),
        "statement": serializers.CharField(),
        "params": serializers.JSONField(),
        "steps": AssignmentStepOut(many=True),
    },
)


def render_statement(template: str, params: dict[str, Any]) -> str:
    """`{nom}` o'rniga parametr qiymati. `{a.b}`, `{a[0]}`, `{a:fmt}` — o'zgarishsiz matn.

    `str.format` ishlatilmaydi: u atributlarga kirishga yo'l qo'yadi (`{x.__class__}`).
    Noma'lum maydon ham o'zgarishsiz qoladi; `{{` va `}}` — oddiy qavs.
    """
    out: list[str] = []
    for literal, field, spec, conversion in string.Formatter().parse(template):
        out.append(literal)
        if field is None:
            continue
        if field in params and not spec and conversion is None:
            out.append(str(params[field]))
        else:
            suffix = (f"!{conversion}" if conversion else "") + (f":{spec}" if spec else "")
            out.append("{" + field + suffix + "}")
    return "".join(out)


class MyAssignmentView(APIView):
    permission_classes = (IsStudent,)

    @extend_schema(responses={200: AssignmentOut}, summary="Mening topshirig'im (shart va testlar)")
    def get(self, request: Request, code: str) -> Response:
        student, section, topic = _student_context(request.user, code)
        if submission_policy(section, topic, timezone.now()) == SubmissionStatus.CLOSED:
            return Response(
                {"code": "lab_closed", "detail": "Laboratoriya yopiq."},
                status=status.HTTP_403_FORBIDDEN,
            )
        assignment = (
            Assignment.objects.filter(course_id=section.course_id, topic_code=topic.code)
            .order_by("code")
            .first()
        )
        if assignment is None:
            return Response(
                {"code": "no_assignment", "detail": "Bu mavzuda topshiriq yo'q."},
                status=status.HTTP_404_NOT_FOUND,
            )
        record = variants.assign(student, assignment)
        params = record.variant.params
        steps = AssignmentStep.objects.filter(assignment=assignment).prefetch_related(
            Prefetch(
                "tests",
                queryset=TestFile.objects.filter(kind=TestKind.VISIBLE),
                to_attr="visible",
            )
        )
        return Response(
            {
                "code": assignment.code,
                "title": assignment.title,
                "level": record.level,
                "statement": render_statement(assignment.statement, params),
                "params": params,
                "steps": [
                    {
                        "key": s.key,
                        "title": s.title,
                        "points": s.points,
                        "visible_test": s.visible[0].source if s.visible else None,
                    }
                    for s in steps
                ],
            }
        )
