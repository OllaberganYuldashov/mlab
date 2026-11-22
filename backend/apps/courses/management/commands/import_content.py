"""`manage.py import_content <papka>` — kurs kontentini bazaga yuklaydi (CNT-01, ADR-0002)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.courses.content import ContentError, import_content


class Command(BaseCommand):
    help = "content/ papkasidagi kurs kontentini bazaga yuklaydi (idempotent, bitta tranzaksiya)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("path", type=Path, help="content/ papkasi yo'li")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            report = import_content(options["path"])
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
