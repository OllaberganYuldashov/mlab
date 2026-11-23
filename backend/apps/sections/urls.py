from django.urls import URLPattern, path

from apps.sections import views

urlpatterns: list[URLPattern] = [
    path("sections", views.SectionListCreateView.as_view(), name="section-list"),
    path("sections/<int:section_id>", views.SectionDetailView.as_view(), name="section-detail"),
    path(
        "sections/<int:section_id>/join-token",
        views.JoinTokenView.as_view(),
        name="section-join-token",
    ),
]
