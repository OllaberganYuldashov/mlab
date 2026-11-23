from django.urls import URLPattern, path

from apps.accounts import views

urlpatterns: list[URLPattern] = [
    path("auth/register", views.RegisterView.as_view(), name="auth-register"),
    path("directions", views.DirectionListView.as_view(), name="directions"),
]
