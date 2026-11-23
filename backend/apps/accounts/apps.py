from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"
    verbose_name = "Foydalanuvchilar"

    def ready(self) -> None:
        from apps.accounts import signals  # noqa: F401 — signal qabul qiluvchilarni ulash
