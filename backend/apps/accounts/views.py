"""Ochiq (autentifikatsiyasiz) accounts endpoint'lari — har biri aniq `AllowAny` (CLAUDE.md 5.6)."""

from __future__ import annotations

import ipaddress
import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import Direction
from apps.accounts.serializers import DirectionSerializer, RegisterSerializer

logger = logging.getLogger("mlab.accounts")


def client_ident(request: Request, throttle: SimpleRateThrottle) -> str:
    """Mijoz IP'si (NUM_PROXIES bo'yicha); IPv6 uchun /64 prefiks — bitta tarmoq, bitta kalit."""
    ident = throttle.get_ident(request)
    try:
        address = ipaddress.ip_address(ident)
    except ValueError:
        return ident
    if address.version == 6:
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return ident


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
