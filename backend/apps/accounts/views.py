"""Ochiq (autentifikatsiyasiz) accounts endpoint'lari — har biri aniq `AllowAny` (CLAUDE.md 5.6)."""

from __future__ import annotations

import logging
import secrets

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.accounts.backends import LOCKED_ATTR
from apps.accounts.models import Direction, Role, User
from apps.accounts.net import client_ip
from apps.accounts.permissions import IsAdmin, IsSuperAdmin
from apps.accounts.policies import RESET_ROLES, can_reset_password
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    DirectionSerializer,
    InstructorCreatedSerializer,
    InstructorCreateSerializer,
    InstructorSerializer,
    LoginSerializer,
    MeSerializer,
    RegisterSerializer,
    TemporaryPasswordSerializer,
)
from apps.audit import record
from apps.audit.models import Action

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


class PolicyVersionView(APIView):
    """Ro'yxatdan o'tish formasi yuboradigan siyosat versiyasi — `Consent` bilan bir manba."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        responses={200: inline_serializer("PolicyVersion", {"version": serializers.CharField()})},
        summary="Joriy siyosat versiyasi",
    )
    def get(self, request: Request) -> Response:
        return Response({"version": settings.PRIVACY_POLICY_VERSION})


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


# --- Parolni tiklash va almashtirish (AUTH-04) ---


class ChangePasswordThrottle(SimpleRateThrottle):
    scope = "change-password"

    def get_rate(self) -> str:
        return str(settings.AUTH_CHANGE_PASSWORD_RATE)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.pk)}


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (ChangePasswordThrottle,)
    parser_classes = (JSONParser,)

    @extend_schema(
        request=ChangePasswordSerializer, responses={204: None}, summary="Parolni almashtirish"
    )
    def post(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)  # IsAuthenticated kafolatlaydi  # noqa: S101
        serializer = ChangePasswordSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["new_password"])
        user.save()  # must_change_password o'chadi, PASSWORD_CHANGED audit (User.save)
        update_session_auth_hash(request._request, user)  # joriy sessiya saqlanadi
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResetPasswordThrottle(SimpleRateThrottle):
    """Tiklovchi bo'yicha: o'g'irlangan xodim sessiyasi bilan ommaviy tiklashga qarshi."""

    scope = "reset-password"

    def get_rate(self) -> str:
        return str(settings.AUTH_RESET_PASSWORD_RATE)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.pk)}


class ResetPasswordView(APIView):
    """Vaqtinchalik parol faqat shu javobda bir marta qaytadi; saqlanmaydi va loglanmaydi."""

    permission_classes = (IsAuthenticated,)
    throttle_classes = (ResetPasswordThrottle,)

    @extend_schema(
        request=None, responses={200: TemporaryPasswordSerializer}, summary="Parolni tiklash"
    )
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user
        assert isinstance(actor, User)  # noqa: S101
        if actor.role not in RESET_ROLES:
            raise PermissionDenied
        temporary = secrets.token_urlsafe(12)
        with transaction.atomic():
            # Qatorni qulflab qayta o'qish: parallel rol/faollik o'zgarishi yo'qolmaydi, qaror yangi
            # ma'lumot bo'yicha.
            target = User.objects.select_for_update().filter(pk=user_id).first()
            if target is None or not can_reset_password(actor, target):
                raise NotFound  # begona yoki mavjud bo'lmagan foydalanuvchi — bir xil javob (IDOR)
            target.set_temporary_password(temporary)
            # Parol xeshi o'zgardi — talabaning eski sessiyalari bekor bo'ladi.
            target.save(
                update_fields=[
                    "password",
                    "must_change_password",
                    "temporary_password_expires_at",
                    "updated_at",
                ]
            )
            record(Action.PASSWORD_RESET, actor=actor, target=target)
        logger.info(
            "user.password_reset",
            extra={"event": "user.password_reset", "actor_id": actor.pk, "user_id": target.pk},
        )
        response = Response({"temporary_password": temporary})
        response["Cache-Control"] = "no-store"
        return response


# --- O'qituvchi akkauntlari (AUTH-05, SEC-08) ---


class InstructorCreateThrottle(SimpleRateThrottle):
    """Yaratuvchi bo'yicha: o'g'irlangan admin sessiyasi bilan ommaviy akkaunt yaratishga qarshi."""

    scope = "instructor-create"

    def get_rate(self) -> str:
        return str(settings.AUTH_INSTRUCTOR_CREATE_RATE)

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": str(request.user.pk)}


class InstructorCreateView(APIView):
    """Admin yoki super admin o'qituvchi yaratadi; vaqtinchalik parol javobda bir marta."""

    permission_classes = (IsAdmin | IsSuperAdmin,)
    throttle_classes = (InstructorCreateThrottle,)
    parser_classes = (JSONParser,)

    @extend_schema(
        request=InstructorCreateSerializer,
        responses={201: InstructorCreatedSerializer},
        summary="O'qituvchi akkauntini yaratish",
    )
    def post(self, request: Request) -> Response:
        serializer = InstructorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        temporary = secrets.token_urlsafe(12)
        try:
            with transaction.atomic():
                instructor = User.objects.create_user(
                    hemis_id=data["hemis_id"],
                    password=None,
                    full_name=data["full_name"],
                    role=Role.INSTRUCTOR,
                    direction=None,
                    student_limit=data["student_limit"],
                )
                instructor.set_temporary_password(temporary)
                instructor.save(
                    update_fields=[
                        "password",
                        "must_change_password",
                        "temporary_password_expires_at",
                    ]
                )
                record(
                    Action.INSTRUCTOR_CREATED,
                    actor=request.user,  # type: ignore[arg-type]
                    target=instructor,
                    after={"role": instructor.role, "student_limit": instructor.student_limit},
                )
        except IntegrityError as exc:
            # Faqat parallel so'rov bir xil Hemis ID bilan — 400; boshqa cheklov xatosi — bug.
            if not User.objects.filter(hemis_id=data["hemis_id"]).exists():
                raise
            raise ValidationError(
                {"hemis_id": [_("Bu Hemis ID bilan foydalanuvchi allaqachon bor.")]}
            ) from exc
        body = {**InstructorSerializer(instructor).data, "temporary_password": temporary}
        response = Response(body, status=status.HTTP_201_CREATED)
        response["Cache-Control"] = "no-store"
        return response


class InstructorLimitView(APIView):
    permission_classes = (IsAdmin | IsSuperAdmin,)
    parser_classes = (JSONParser,)

    @extend_schema(
        request=InstructorSerializer,
        responses={200: InstructorSerializer},
        summary="O'qituvchining talaba limitini o'zgartirish",
    )
    def patch(self, request: Request, user_id: int) -> Response:
        if "student_limit" not in request.data:
            raise ValidationError({"student_limit": [_("Bu maydon majburiy.")]})
        with transaction.atomic():
            instructor = (
                User.objects.select_for_update().filter(pk=user_id, role=Role.INSTRUCTOR).first()
            )
            if instructor is None:
                raise NotFound
            serializer = InstructorSerializer(instructor, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            before = instructor.student_limit
            after = serializer.validated_data.get("student_limit", before)
            if after != before:
                instructor.student_limit = after
                instructor.save(update_fields=["student_limit", "updated_at"])
                record(
                    Action.STUDENT_LIMIT_CHANGED,
                    actor=request.user,  # type: ignore[arg-type]
                    target=instructor,
                    before={"student_limit": before},
                    after={"student_limit": after},
                )
        return Response(InstructorSerializer(instructor).data)
