"""ASGI: HTTP (Django) va WebSocket (Channels, ACC-05). uvicorn shu `application` ni ishlatadi."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

# Avval Django ilovalari yuklanadi, keyin ularga bog'liq routing.
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from apps.sections.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # Origin ALLOWED_HOSTS bo'yicha (cross-site WebSocket hijacking'ga qarshi), keyin sessiya.
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
