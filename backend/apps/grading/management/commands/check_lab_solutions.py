"""`manage.py check_lab_solutions ../content --python <venv python>` yoki `--docker <image>`.

Har topshiriq va har variant uchun yechim barcha (ko'rinadigan va yashirin) testlardan o'tishini
tekshiradi (I3-15; AGR-07). Xato bo'lsa — ro'yxat va chiqish kodi 1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.grading.solutions import check_labs, docker_runner, local_runner


class Command(BaseCommand):
    help = "Kontent yechimlarini sandbox runner orqali barcha variantlarda tekshiradi."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("root", type=Path)
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--python", help="sandbox/requirements.txt o'rnatilgan Python")
        group.add_argument("--docker", help="sandbox image nomi (masalan, mlab-sandbox:dev)")
        parser.add_argument("--lab", help="faqat shu topshiriq (masalan, A01)")

    def handle(self, *args: Any, **options: Any) -> None:
        root: Path = options["root"]
        if options["python"]:
            run = local_runner(options["python"], root.resolve() / "datasets")
        else:
            run = docker_runner(options["docker"])
        checked, failures = check_labs(root, run, options.get("lab"))
        for failure in failures:
            self.stderr.write(str(failure))
        if failures:
            raise CommandError(f"{len(failures)} ta xato ({checked} ta variant tekshirildi)")
        self.stdout.write(f"OK: {checked} ta variant, barcha testlar o'tdi")
