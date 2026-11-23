"""Ochiq (autentifikatsiyasiz) accounts endpoint'lari — har biri aniq `AllowAny` (CLAUDE.md 5.6)."""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.accounts.backends import LOCKED_ATTR
from apps.accounts.models import Direction, User
from apps.accounts.net import client_ip
from apps.accounts.serializers import (
    DirectionSerializer,
    LoginSerializer,
    MeSerializer,
    RegisterSerializer,
)

logger = logging.getLogger("mlab.accounts")


def client_ident(request: Request, throttle: SimpleRateThrottle) -> str:
    """Throttle kaliti: lockout va audit bilan bir xil IP qoidasi (`apps.accounts.net`)."""
    return client_ip(request)


class RegisterRateThrottle(SimpleRateThrottle):
    """IP bo'yicha cheklov. Kompyuter xonasi bitta NAT ortida — limit keng (60/soat)."""

    scope = "register"

    def get_rate(self) -> str:
        return str(settings.AUTH_REGISTER_RATE)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": client_ident(request, self)}


class RegisterGlobalThrottle(SimpleRateThrottle):
    """Umumiy chegara: ko'p IP'dan kelgan hujumda ham Argon2 xeshlash serverni bosib qo'ymasin."""

    scope = "register-global"

    def get_rate(self) -> str:
        return str(settings.AUTH_REGISTER_GLOBAL_RATE)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": "all"}


class RegisterView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()  # anonim endpoint: sessiya ham, CSRF ham kerak emas
    throttle_classes = (RegisterRateThrottle, RegisterGlobalThrottle)
    # Faqat JSON: boshqa saytdagi oddiy HTML forma (preflight'siz) bu yerga so'rov yubora olmaydi.
    parser_classes = (JSONParser,)

    @extend_schema(
        request=RegisterSerializer,
        responses={201: RegisterSerializer, 400: inline_serializer("RegisterErrors", {})},
        summary="Talaba ro'yxatdan o'tadi (AUTH-01)",
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("user.registered", extra={"event": "user.registered", "user_id": user.pk})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DirectionListView(generics.ListAPIView[Direction]):
    """Ro'yxatdan o'tish formasidagi yo'nalishlar (kichik ro'yxat — sahifalashsiz)."""

    permission_classes = (AllowAny,)
    authentication_classes = ()
    serializer_class = DirectionSerializer
    queryset = Direction.objects.order_by("name")
    pagination_class = None


# --- Kirish va chiqish (AUTH-02) ---

LOGIN_FAILED = _("Hemis ID yoki parol noto'g'ri.")
LOGIN_LOCKED = _("Juda ko'p muvaffaqiyatsiz urinish. 15 daqiqadan keyin qayta urinib ko'ring.")


class LoginRateThrottle(SimpleRateThrottle):
    """IP bo'yicha cheklov (lockout'dan tashqari): ko'p Hemis ID'ni sinab ko'rishga qarshi."""

    scope = "login"

    def get_rate(self) -> str:
        return str(settings.AUTH_LOGIN_RATE)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": client_ident(request, self)}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """SPA birinchi chaqiradi: `csrftoken` cookie, keyin u `X-CSRFToken` sarlavhasida."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(responses={204: None}, summary="CSRF cookie o'rnatish")
    def get(self, request: Request) -> Response:
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (LoginRateThrottle,)
    parser_classes = (JSONParser,)

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: MeSerializer,
            400: inline_serializer("LoginFailed", {"detail": serializers.CharField()}),
            429: inline_serializer("LoginLocked", {"detail": serializers.CharField()}),
        },
        summary="Hemis ID va parol bilan kirish (AUTH-02)",
    )
    def post(self, request: Request) -> Response:
        # Anonim so'rovda DRF CSRF'ni tekshirmaydi — "login CSRF" ga qarshi qo'lda majburiy.
        SessionAuthentication().enforce_csrf(request)
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": LOGIN_FAILED}, status=status.HTTP_400_BAD_REQUEST)
        django_request = request._request
        user = authenticate(
            django_request,
            hemis_id=serializer.validated_data["hemis_id"],
            password=serializer.validated_data["password"],
        )
        if getattr(django_request, LOCKED_ATTR, False):
            return Response({"detail": LOGIN_LOCKED}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if not isinstance(user, User):
            return Response({"detail": LOGIN_FAILED}, status=status.HTTP_400_BAD_REQUEST)
        login(django_request, user)  # sessiya kaliti yangilanadi (session fixation'ga qarshi)
        return Response(MeSerializer(user).data)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(request=None, responses={204: None}, summary="Chiqish")
    def post(self, request: Request) -> Response:
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: MeSerializer}, summary="Joriy foydalanuvchi")
    def get(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)  # IsAuthenticated kafolatlaydi  # noqa: S101
        return Response(MeSerializer(user).data)
