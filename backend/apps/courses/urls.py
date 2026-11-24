from django.urls import URLPattern, path

from apps.courses import quiz_views, views

urlpatterns: list[URLPattern] = [
    path("course/topics", views.TopicListView.as_view(), name="course-topics"),
    path("course/topics/<str:code>/lecture", views.LectureView.as_view(), name="course-lecture"),
    path("course/images/<str:sha256>", views.LectureImageView.as_view(), name="course-image"),
    path("course/topics/<str:code>/quiz", quiz_views.QuizSummaryView.as_view(), name="quiz"),
    path(
        "course/topics/<str:code>/quiz/attempts",
        quiz_views.QuizStartView.as_view(),
        name="quiz-start",
    ),
    path(
        "course/quiz/attempts/<int:attempt_id>",
        quiz_views.QuizAttemptView.as_view(),
        name="quiz-attempt",
    ),
    path(
        "course/quiz/attempts/<int:attempt_id>/submit",
        quiz_views.QuizSubmitView.as_view(),
        name="quiz-submit",
    ),
]
