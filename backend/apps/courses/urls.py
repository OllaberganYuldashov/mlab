from django.urls import URLPattern, path

from apps.courses import views

urlpatterns: list[URLPattern] = [
    path("course/topics", views.TopicListView.as_view(), name="course-topics"),
    path("course/topics/<str:code>/lecture", views.LectureView.as_view(), name="course-lecture"),
    path("course/images/<str:sha256>", views.LectureImageView.as_view(), name="course-image"),
]
