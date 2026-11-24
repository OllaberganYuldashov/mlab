"""Kurs kontenti (CNT-01, ADR-0002): Course → Topic → Lecture → LectureStep.

Manba — `content/` dagi fayllar; bazadagi nusxa `import_content` bilan yangilanadi.
"""

from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AiMode(models.TextChoices):
    """AI-01 rejimlari, kuchayish tartibida (chegara solishtirish shu tartib bo'yicha)."""

    OFF = "off", _("O'chiq")
    GUIDE = "guide", _("Yo'naltiruvchi")
    EXPLAIN = "explain", _("Tushuntirish")
    FULL = "full", _("To'liq yordam")


AI_MODE_ORDER = [AiMode.OFF, AiMode.GUIDE, AiMode.EXPLAIN, AiMode.FULL]
MAX_LATE_HOURS = 168  # 7 kun


MAX_QUIZ_QUESTIONS = 50
MAX_QUIZ_MINUTES = 180
MAX_QUIZ_ATTEMPTS = 10
MAX_PASTE_LIMIT = 10_000


class Course(models.Model):
    slug = models.SlugField(_("slug"), max_length=50, unique=True)
    title = models.TextField(_("nomi"))
    version = models.CharField(_("kontent versiyasi"), max_length=32)
    content_hash = models.CharField(_("fayllar xeshi (SHA-256)"), max_length=64)
    imported_at = models.DateTimeField(_("import vaqti"), default=timezone.now)
    # Kurs default sozlamalari (SET, `course.yaml` → `defaults:`); guruh override qiladi.
    ai_enabled = models.BooleanField(_("AI tutor yoqilgan"), default=True)
    ai_max_mode = models.CharField(
        _("AI maksimal rejimi"), max_length=16, choices=AiMode.choices, default=AiMode.EXPLAIN
    )
    practice_after_close = models.BooleanField(_("yopilgandan keyin mashq"), default=False)
    late_hours = models.PositiveSmallIntegerField(_("kechikish muddati (soat)"), default=0)
    late_penalty_percent = models.PositiveSmallIntegerField(_("kechikish jarimasi (%)"), default=0)
    chat_enabled = models.BooleanField(_("guruh chati"), default=True)
    # CNT-06: mavzu testi sozlamalari — faqat kurs darajasida.
    quiz_questions = models.PositiveSmallIntegerField(_("testdagi savollar soni"), default=10)
    quiz_minutes = models.PositiveSmallIntegerField(_("test vaqti (daqiqa)"), default=15)
    quiz_attempts = models.PositiveSmallIntegerField(_("urinishlar soni"), default=3)
    # INT-01: laboratoriyada bir martada joylashtirish mumkin bo'lgan belgilar soni.
    paste_limit = models.PositiveSmallIntegerField(_("paste chegarasi (belgi)"), default=200)

    class Meta:
        verbose_name = _("kurs")
        verbose_name_plural = _("kurslar")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(ai_max_mode__in=AiMode.values), name="courses_course_ai_mode"
            ),
            models.CheckConstraint(
                condition=Q(late_hours__lte=MAX_LATE_HOURS), name="courses_course_late_hours"
            ),
            models.CheckConstraint(
                condition=Q(late_penalty_percent__lte=100), name="courses_course_late_penalty"
            ),
            models.CheckConstraint(condition=Q(title__regex=r"\S"), name="courses_course_title"),
            models.CheckConstraint(
                condition=Q(quiz_questions__gte=1, quiz_questions__lte=MAX_QUIZ_QUESTIONS),
                name="courses_course_quiz_questions",
            ),
            models.CheckConstraint(
                condition=Q(quiz_minutes__gte=1, quiz_minutes__lte=MAX_QUIZ_MINUTES),
                name="courses_course_quiz_minutes",
            ),
            models.CheckConstraint(
                condition=Q(quiz_attempts__gte=1, quiz_attempts__lte=MAX_QUIZ_ATTEMPTS),
                name="courses_course_quiz_attempts",
            ),
            models.CheckConstraint(
                condition=Q(paste_limit__lte=MAX_PASTE_LIMIT), name="courses_course_paste_limit"
            ),
            models.CheckConstraint(
                condition=Q(content_hash__regex=r"^[0-9a-f]{64}$"), name="courses_course_hash"
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Topic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="topics")
    code = models.CharField(_("kod"), max_length=8)
    title = models.TextField(_("nomi"))
    order = models.PositiveSmallIntegerField(_("tartib"))

    class Meta:
        verbose_name = _("mavzu")
        verbose_name_plural = _("mavzular")
        ordering = ("order",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["course", "code"], name="courses_topic_code_uniq"),
            # DEFERRED: import mavzular tartibini almashtirsa (1<->2), oxirida tekshiriladi.
            models.UniqueConstraint(
                fields=["course", "order"],
                name="courses_topic_order_uniq",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(
                condition=Q(code__regex=r"^[A-Z][0-9]{2}$"), name="courses_topic_code_format"
            ),
            models.CheckConstraint(condition=Q(title__regex=r"\S"), name="courses_topic_title"),
        ]

    def __str__(self) -> str:
        return f"{self.code} {self.title}"


class Lecture(models.Model):
    topic = models.OneToOneField(Topic, on_delete=models.CASCADE, related_name="lecture")
    title = models.TextField(_("nomi"))

    class Meta:
        verbose_name = _("ma'ruza")
        verbose_name_plural = _("ma'ruzalar")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(condition=Q(title__regex=r"\S"), name="courses_lecture_title"),
        ]

    def __str__(self) -> str:
        return self.title


class LectureStep(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveSmallIntegerField(_("tartib"))
    title = models.TextField(_("sarlavha"))
    # Bo'sh bo'lishi mumkin, agar qadamda faqat tezkor savol bo'lsa (CNT-02).
    body = models.TextField(_("matn (Markdown)"), blank=True)
    # CNT-02 tezkor savol: {"question", "options": [..], "answer": indeks, "explain"}.
    # Baholanmaydi — shuning uchun to'g'ri javob talabaga ham beriladi (mijozda darhol
    # tekshiriladi). Shakli importda tekshiriladi.
    question = models.JSONField(_("tezkor savol"), null=True, blank=True)

    class Meta:
        verbose_name = _("ma'ruza qadami")
        verbose_name_plural = _("ma'ruza qadamlari")
        ordering = ("order",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["lecture", "order"], name="courses_step_order_uniq"),
            models.CheckConstraint(condition=Q(order__gte=1), name="courses_step_order_positive"),
            models.CheckConstraint(condition=Q(title__regex=r"\S"), name="courses_step_title"),
        ]

    def __str__(self) -> str:
        return f"{self.order}. {self.title}"


MAX_IMAGE_BYTES = 500 * 1024


class ImageType(models.TextChoices):
    PNG = "image/png", "PNG"
    JPEG = "image/jpeg", "JPEG"
    WEBP = "image/webp", "WebP"


class LectureImage(models.Model):
    """Ma'ruza rasmi (CNT-02). Baytlar bazada: kichik (<= 500 KB), zaxira (`deploy/backup.sh`) bilan
    birga saqlanadi va media volume kerak emas. SVG qabul qilinmaydi (skript ichishi mumkin)."""

    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="images", db_index=False
    )
    name = models.CharField(_("fayl nomi"), max_length=64)
    content_type = models.CharField(_("turi"), max_length=16, choices=ImageType.choices)
    sha256 = models.CharField(_("SHA-256"), max_length=64)
    size = models.PositiveIntegerField(_("hajmi (bayt)"))
    data = models.BinaryField(_("baytlar"))

    class Meta:
        verbose_name = _("ma'ruza rasmi")
        verbose_name_plural = _("ma'ruza rasmlari")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # Prefiks (topic) FK indeksini ham qoplaydi.
            models.UniqueConstraint(fields=["topic", "name"], name="courses_image_name_uniq"),
            models.CheckConstraint(
                condition=Q(name__regex=r"^[A-Za-z0-9_-]+\.(png|jpg|jpeg|webp)$"),
                name="courses_image_name_format",
            ),
            models.CheckConstraint(
                condition=Q(content_type__in=ImageType.values), name="courses_image_type"
            ),
            models.CheckConstraint(
                condition=Q(sha256__regex=r"^[0-9a-f]{64}$"), name="courses_image_sha256"
            ),
            models.CheckConstraint(
                condition=Q(size__gte=1, size__lte=MAX_IMAGE_BYTES), name="courses_image_size"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.topic_id}/{self.name}"


class Question(models.Model):
    """Mavzu savollar banki (CNT-05/06). Manba — `topics/<KOD>/quiz.aiken`.

    Tabiiy kalit `key` — savol matnining NFC xeshi (`apps.courses.aiken.question_key`).
    Fayldan olib tashlangan savol o'chirilmaydi, `is_active=False` bo'ladi: test urinishlari
    (I2-07) unga bog'lanadi. To'g'ri javob (`answer`) talaba API'siga topshirishdan oldin chiqmaydi.
    """

    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="questions", db_index=False
    )
    key = models.CharField(_("kalit (matn xeshi)"), max_length=64)
    text = models.TextField(_("savol"))
    options = models.JSONField(_("variantlar"))
    answer = models.PositiveSmallIntegerField(_("to'g'ri variant (0 dan)"))
    position = models.PositiveSmallIntegerField(_("fayldagi tartib"))
    is_active = models.BooleanField(_("faol"), default=True)

    class Meta:
        verbose_name = _("savol")
        verbose_name_plural = _("savollar")
        ordering = ("topic", "position")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # Prefiks (topic) FK indeksini ham qoplaydi.
            models.UniqueConstraint(fields=["topic", "key"], name="courses_question_key_uniq"),
            models.CheckConstraint(
                condition=Q(key__regex=r"^[0-9a-f]{64}$"), name="courses_question_key_format"
            ),
            models.CheckConstraint(condition=Q(text__regex=r"\S"), name="courses_question_text"),
            models.CheckConstraint(condition=Q(answer__lte=5), name="courses_question_answer"),
            models.CheckConstraint(condition=Q(position__gte=1), name="courses_question_position"),
        ]

    def __str__(self) -> str:
        return f"{self.topic_id}/{self.position}: {self.text[:40]}"


class QuizAttempt(models.Model):
    """Mavzu testiga urinish (CNT-06). Savollar va variantlar tartibi `QuizItem` da qotiriladi."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="quiz_attempts",
        db_index=False,
    )
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT, related_name="quiz_attempts")
    number = models.PositiveSmallIntegerField(_("urinish raqami"))
    started_at = models.DateTimeField(_("boshlangan"), db_default=Now())
    deadline = models.DateTimeField(_("muddat"))
    submitted_at = models.DateTimeField(_("topshirilgan"), null=True, blank=True)
    score = models.PositiveSmallIntegerField(_("ball"), null=True, blank=True)
    max_score = models.PositiveSmallIntegerField(_("maksimal ball"))

    class Meta:
        verbose_name = _("test urinishi")
        verbose_name_plural = _("test urinishlari")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # Prefiks (student) FK indeksini ham qoplaydi.
            models.UniqueConstraint(
                fields=["student", "topic", "number"], name="courses_attempt_number_uniq"
            ),
            models.CheckConstraint(condition=Q(number__gte=1), name="courses_attempt_number"),
            models.CheckConstraint(
                condition=Q(submitted_at__isnull=True, score__isnull=True)
                | Q(submitted_at__isnull=False, score__isnull=False),
                name="courses_attempt_submitted_score",
            ),
            models.CheckConstraint(
                condition=Q(score__isnull=True) | Q(score__lte=models.F("max_score")),
                name="courses_attempt_score_max",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_id}/{self.topic_id} #{self.number}"


class QuizItem(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="quiz_items")
    position = models.PositiveSmallIntegerField(_("tartib"))
    # Talabaga ko'rsatilgan tartib: order[i] — i-o'rindagi variantning savoldagi indeksi.
    order = models.JSONField(_("variantlar tartibi"))
    chosen = models.PositiveSmallIntegerField(_("tanlangan (ko'rsatilgan indeks)"), null=True)

    class Meta:
        verbose_name = _("test savoli")
        verbose_name_plural = _("test savollari")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["attempt", "position"], name="courses_item_position_uniq"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.attempt_id}/{self.position}"


MAX_DATASET_BYTES = 5 * 1024 * 1024  # DAT-01: R1 da faqat kichik datasetlar

# DAT-03: faqat ochiq litsenziyalar — SPDX identifikatori -> rasmiy matn havolasi.
LICENSES = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "ODbL-1.0": "https://opendatacommons.org/licenses/odbl/1-0/",
    "PDDL-1.0": "https://opendatacommons.org/licenses/pddl/1-0/",
}


class Dataset(models.Model):
    """Kurs dataseti (DAT-01..03). Manba — `content/datasets/sources.yaml`.

    Baytlar bazada (rasmlar kabi — zaxira bilan birga, media volume kerak emas).
    """

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="datasets", db_index=False
    )
    name = models.CharField(_("nomi (mlab.load)"), max_length=64)
    title = models.TextField(_("sarlavha"))
    description = models.TextField(_("tavsif"))
    source_url = models.URLField(_("manba"), max_length=500)
    license = models.CharField(_("litsenziya (SPDX)"), max_length=32)
    sha256 = models.CharField(_("SHA-256"), max_length=64)
    size = models.PositiveIntegerField(_("hajmi (bayt)"))
    rows = models.PositiveIntegerField(_("qatorlar"))
    columns = models.JSONField(_("ustunlar"))
    data = models.BinaryField(_("CSV"))

    class Meta:
        verbose_name = _("dataset")
        verbose_name_plural = _("datasetlar")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # Prefiks (course) FK indeksini ham qoplaydi.
            models.UniqueConstraint(fields=["course", "name"], name="courses_dataset_name_uniq"),
            models.CheckConstraint(
                condition=Q(name__regex=r"^[a-z0-9_]{1,64}$"), name="courses_dataset_name_format"
            ),
            models.CheckConstraint(
                condition=Q(license__in=list(LICENSES)), name="courses_dataset_license"
            ),
            models.CheckConstraint(
                condition=Q(sha256__regex=r"^[0-9a-f]{64}$"), name="courses_dataset_sha256"
            ),
            models.CheckConstraint(
                condition=Q(size__gte=1, size__lte=MAX_DATASET_BYTES), name="courses_dataset_size"
            ),
        ]

    def __str__(self) -> str:
        return self.name
