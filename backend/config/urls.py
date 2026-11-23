from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView

from config import views

urlpatterns: list[URLPattern | URLResolver] = [
    # Faqat super admin va admin (SRS 2.2); boshqa rollar login sahifasiga qaytariladi.
    path("admin/", admin.site.urls),
    path("healthz", views.healthz, name="healthz"),
    path("readyz", views.readyz, name="readyz"),
    path("api/", include("apps.accounts.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="openapi-schema"),
]
