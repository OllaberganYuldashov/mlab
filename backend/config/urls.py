from django.contrib import admin
from django.urls import URLPattern, URLResolver, path

from config import views

urlpatterns: list[URLPattern | URLResolver] = [
    # Faqat super admin va admin (SRS 2.2); boshqa rollar login sahifasiga qaytariladi.
    path("admin/", admin.site.urls),
    path("healthz", views.healthz, name="healthz"),
    path("readyz", views.readyz, name="readyz"),
]
