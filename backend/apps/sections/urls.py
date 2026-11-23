from django.urls import URLPattern, path

from apps.sections import join_views, member_views, settings_views, views

urlpatterns: list[URLPattern] = [
    path("join/<str:token>", join_views.JoinView.as_view(), name="section-join"),
    path("me/membership", join_views.MyMembershipView.as_view(), name="my-membership"),
    path("sections", views.SectionListCreateView.as_view(), name="section-list"),
    path("sections/<int:section_id>", views.SectionDetailView.as_view(), name="section-detail"),
    path(
        "sections/<int:section_id>/members",
        member_views.MemberListView.as_view(),
        name="section-members",
    ),
    path(
        "sections/<int:section_id>/members/decide",
        member_views.DecideView.as_view(),
        name="section-members-decide",
    ),
    path(
        "sections/<int:section_id>/members/<int:membership_id>/move",
        member_views.MoveView.as_view(),
        name="section-member-move",
    ),
    path(
        "sections/<int:section_id>/members/<int:membership_id>/remove",
        member_views.RemoveView.as_view(),
        name="section-member-remove",
    ),
    path(
        "sections/<int:section_id>/settings",
        settings_views.SectionSettingsView.as_view(),
        name="section-settings",
    ),
    path(
        "sections/<int:section_id>/ai/disable",
        settings_views.AiSwitchView.as_view(enable=False),
        name="section-ai-disable",
    ),
    path(
        "sections/<int:section_id>/ai/enable",
        settings_views.AiSwitchView.as_view(enable=True),
        name="section-ai-enable",
    ),
    path(
        "sections/<int:section_id>/join-token",
        views.JoinTokenView.as_view(),
        name="section-join-token",
    ),
]
