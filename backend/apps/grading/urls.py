from django.urls import URLPattern, path

from apps.grading import views

urlpatterns: list[URLPattern] = [
    path("labs/<str:code>/assignment", views.MyAssignmentView.as_view(), name="lab-assignment"),
    path("labs/<str:code>/submissions", views.MySubmissionsView.as_view(), name="lab-submissions"),
    path("submissions/<int:submission_id>", views.MySubmissionView.as_view(), name="submission"),
    path(
        "submissions/<int:submission_id>/answers",
        views.SubmissionAnswersView.as_view(),
        name="submission-answers",
    ),
    path(
        "sections/<int:section_id>/labs/<str:code>/students/<int:student_id>/submissions",
        views.StudentSubmissionsView.as_view(),
        name="section-student-submissions",
    ),
    path(
        "sections/<int:section_id>/labs/<str:code>/students/<int:student_id>/level",
        views.StudentLevelView.as_view(),
        name="section-student-level",
    ),
]
