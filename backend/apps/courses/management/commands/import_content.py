"""`manage.py import_content <papka>` — kurs kontentini bazaga yuklaydi (CNT-01, ADR-0002)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.courses.content import ContentError, apply, load_course
from apps.courses.models import Course
from apps.grading.content import apply_labs, load_labs


class Command(BaseCommand):
    help = "content/ papkasidagi kurs kontentini bazaga yuklaydi (idempotent, bitta tranzaksiya)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("path", type=Path, help="content/ papkasi yo'li")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            # Avval hammasi o'qiladi va tekshiriladi, keyin bitta tranzaksiyada yoziladi.
            data = load_course(options["path"])
            labs = load_labs(options["path"])
            with transaction.atomic():
                report = apply(data)
                apply_labs(Course.objects.get(slug=data.slug), labs, report)
        except ContentError as exc:
            raise CommandError(f"Kontent xatosi, baza o'zgarmadi: {exc}") from exc
        if not report.changed:
            self.stdout.write("O'zgarish yo'q.")
            return
        for kind, label in (
            ("created", "yaratildi"),
            ("updated", "yangilandi"),
            ("deleted", "o'chirildi"),
        ):
            counts = getattr(report, kind)
            if counts:
                summary = ", ".join(f"{model}: {n}" for model, n in sorted(counts.items()))
                self.stdout.write(f"{label}: {summary}")
        self.stdout.write(self.style.SUCCESS("Import tugadi."))
