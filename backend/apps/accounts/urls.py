from django.urls import URLPattern, path

from apps.accounts import views

urlpatterns: list[URLPattern] = [
    path("auth/register", views.RegisterView.as_view(), name="auth-register"),
    path("auth/csrf", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/login", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me", views.MeView.as_view(), name="auth-me"),
    path("directions", views.DirectionListView.as_view(), name="directions"),
]
