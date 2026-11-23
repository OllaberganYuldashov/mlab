from django.urls import URLPattern, path

from apps.accounts import views

urlpatterns: list[URLPattern] = [
    path("auth/register", views.RegisterView.as_view(), name="auth-register"),
    path("auth/csrf", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/login", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me", views.MeView.as_view(), name="auth-me"),
    path("auth/change-password", views.ChangePasswordView.as_view(), name="auth-change-password"),
    path(
        "users/<int:user_id>/reset-password",
        views.ResetPasswordView.as_view(),
        name="user-reset-password",
    ),
    path("instructors", views.InstructorCreateView.as_view(), name="instructor-create"),
    path("instructors/<int:user_id>", views.InstructorLimitView.as_view(), name="instructor-limit"),
    path("policy", views.PolicyVersionView.as_view(), name="policy-version"),
    path("directions", views.DirectionListView.as_view(), name="directions"),
]
