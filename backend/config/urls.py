from django.urls import URLPattern, path

from config import views

urlpatterns: list[URLPattern] = [
    path("healthz", views.healthz, name="healthz"),
]
