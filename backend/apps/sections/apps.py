from django.apps import AppConfig


class SectionsConfig(AppConfig):
    name = "apps.sections"
    label = "sections"
    verbose_name = "Guruhlar"

    def ready(self) -> None:
        from apps.sections import signals  # noqa: F401  # signal qabul qiluvchilarni ro'yxatga olish
