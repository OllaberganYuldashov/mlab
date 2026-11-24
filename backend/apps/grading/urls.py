from django.urls import URLPattern, path

from apps.grading import views

urlpatterns: list[URLPattern] = [
    path("labs/<str:code>/assignment", views.MyAssignmentView.as_view(), name="lab-assignment"),
]
