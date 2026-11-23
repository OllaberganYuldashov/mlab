from django.urls import path

from apps.sections.consumers import StudentConsumer

websocket_urlpatterns = [path("ws/student", StudentConsumer.as_asgi())]
