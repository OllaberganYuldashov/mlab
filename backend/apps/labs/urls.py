from django.urls import URLPattern, path

from apps.labs import integrity, views

urlpatterns: list[URLPattern] = [
    path("labs/<str:code>/work", views.MyLabWorkView.as_view(), name="lab-work"),
    path("labs/<str:code>/events", views.MyLabEventView.as_view(), name="lab-events"),
    path(
        "sections/<int:section_id>/labs/<str:code>/works/<int:student_id>",
        views.StudentLabWorkView.as_view(),
        name="section-lab-work",
    ),
    path(
        "sections/<int:section_id>/labs/<str:code>/integrity",
        integrity.IntegrityFlagsView.as_view(),
        name="section-lab-integrity",
    ),
    path(
        "sections/<int:section_id>/labs/<str:code>/students/<int:student_id>/integrity-note",
        integrity.IntegrityNoteView.as_view(),
        name="section-lab-integrity-note",
    ),
]
