"""Django Admin: kurs kontenti (I2-09; CNT-07, ADM-02).

- Ko'rish: super admin va admin. Tahrir: faqat super admin va faqat matn (kichik tuzatish).
- Qo'shish/o'chirish yo'q: kontentning yagona manbai — `content/` fayllari (CNT-01). Keyingi
  `import_content` fayldagi matn bilan ustidan yozadi — sahifada ogohlantirish bor.
- Har o'zgarish `content_edited` bilan audit jurnaliga yoziladi (faqat o'zgargan maydonlar).
"""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from apps.accounts.admin_access import RoleAccessAdmin
from apps.accounts.models import Role
from apps.audit import record
from apps.audit.models import Action
from apps.courses.models import Course, LectureImage, LectureStep, Question, Topic

STAFF = (Role.SUPER_ADMIN, Role.ADMIN)
WARNING = _(
    "Diqqat: kontentning manbai — content/ fayllari. Keyingi import_content bu tuzatishni fayldagi "
    "matn bilan ustidan yozadi, shuning uchun tuzatishni faylga ham kiriting (PR orqali)."
)


class ContentAdmin(RoleAccessAdmin):
    view_roles = STAFF
    change_roles = (Role.SUPER_ADMIN,)
    edited: tuple[str, ...] = ()

    def save_model(self, request: HttpRequest, obj: Any, form: ModelForm, change: bool) -> None:  # type: ignore[type-arg]
        previous = type(obj).objects.filter(pk=obj.pk).values(*self.edited).first() or {}
        super().save_model(request, obj, form, change)
        before = {k: v for k, v in previous.items() if v != getattr(obj, k)}
        if before:
            record(
                Action.CONTENT_EDITED,
                actor=request.user,  # type: ignore[arg-type]
                target=obj,
                before=before,
                after={k: getattr(obj, k) for k in before},
            )


@admin.register(Course)
class CourseAdmin(RoleAccessAdmin):
    view_roles = STAFF
    list_display = ("title", "slug", "version", "imported_at")
    readonly_fields = ("slug", "title", "version", "content_hash", "imported_at")


@admin.register(Topic)
class TopicAdmin(RoleAccessAdmin):
    view_roles = STAFF
    list_display = ("code", "title", "order")
    ordering = ("order",)
    search_fields = ("code", "title")


@admin.register(LectureStep)
class LectureStepAdmin(ContentAdmin):
    edited = ("title", "body")
    list_display = ("topic_code", "order", "title")
    list_filter = ("lecture__topic__code",)
    search_fields = ("title", "body")
    ordering = ("lecture__topic__order", "order")
    list_select_related = ("lecture__topic",)
    fieldsets = (
        (
            None,
            {"description": WARNING, "fields": ("lecture", "order", "title", "body", "question")},
        ),
    )
    readonly_fields = ("lecture", "order", "question")

    @admin.display(description=_("mavzu"), ordering="lecture__topic__order")
    def topic_code(self, obj: LectureStep) -> str:
        return obj.lecture.topic.code


class QuestionForm(forms.ModelForm):  # type: ignore[type-arg]  # runtime generic emas
    class Meta:
        model = Question
        fields = ("text", "options", "answer", "is_active")

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        if "options" not in self.fields:  # qulflangan savol — faqat `is_active` o'zgaradi
            return data
        options, answer = data.get("options"), data.get("answer")
        if not isinstance(options, list) or not 2 <= len(options) <= 6:
            raise forms.ValidationError(_("Variantlar 2..6 ta matn ro'yxati bo'lishi kerak."))
        if not all(isinstance(o, str) and o.strip() for o in options):
            raise forms.ValidationError(_("Variant bo'sh bo'lmasligi kerak."))
        if answer is None or answer >= len(options):
            raise forms.ValidationError(
                _("To'g'ri variant raqami variantlar sonidan kichik bo'lishi kerak.")
            )
        return data


@admin.register(Question)
class QuestionAdmin(ContentAdmin):
    form = QuestionForm
    edited = ("text", "options", "answer", "is_active")
    list_display = ("topic", "position", "short_text", "is_active")
    list_filter = ("topic__code", "is_active")
    search_fields = ("text",)
    ordering = ("topic__order", "position")
    list_select_related = ("topic",)
    fieldsets = (
        (None, {"description": WARNING, "fields": ("text", "options", "answer", "is_active")}),
    )

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        # Urinishlarda ishlatilgan savolning matni, variantlari va javobi o'zgarmaydi:
        # `QuizItem.order` eski variantlarga ishora qiladi (I2 security-review).
        if obj is not None and obj.quiz_items.exists():
            return ("text", "options", "answer")
        return ()

    @admin.display(description=_("savol"))
    def short_text(self, obj: Question) -> str:
        return obj.text[:80]


@admin.register(LectureImage)
class LectureImageAdmin(RoleAccessAdmin):
    view_roles = STAFF
    list_display = ("topic", "name", "content_type", "size")
    list_select_related = ("topic",)
    fields = ("topic", "name", "content_type", "size", "sha256")  # baytlar sahifaga chiqmaydi
    readonly_fields = fields
