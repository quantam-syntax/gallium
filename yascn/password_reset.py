"""Password reset without exposing tokens through the public JSON API."""
import logging
import os
from smtplib import SMTPException
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import get_connection, send_mail
from django.db import transaction
from django.db.models import F
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .models import User
from .validators import validate_password

logger = logging.getLogger(__name__)


class ResetThrottle(SimpleRateThrottle):
    scope = "password_reset"
    rate = "5/hour"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class ConfirmThrottle(ResetThrottle):
    scope = "password_reset_confirm"
    rate = "10/hour"


class ResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=200)
    password = serializers.CharField(trim_whitespace=False, write_only=True, validators=[validate_password])


def _connection():
    if settings.EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
        return get_connection()
    # Root settings need no changes; support standard Django settings plus env.
    def flag(name, fallback):
        return os.environ.get(name, str(fallback)).lower() in ("1", "true", "yes")
    return get_connection(
        host=os.environ.get("BRIGHTLOOP_SMTP_HOST", settings.EMAIL_HOST),
        port=int(os.environ.get("BRIGHTLOOP_SMTP_PORT", settings.EMAIL_PORT)),
        username=os.environ.get("BRIGHTLOOP_SMTP_USER", settings.EMAIL_HOST_USER),
        password=os.environ.get("BRIGHTLOOP_SMTP_PASSWORD", settings.EMAIL_HOST_PASSWORD),
        use_tls=flag("BRIGHTLOOP_SMTP_TLS", settings.EMAIL_USE_TLS),
        use_ssl=flag("BRIGHTLOOP_SMTP_SSL", settings.EMAIL_USE_SSL),
        timeout=10,
    )


class ResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ResetThrottle]

    def post(self, request):
        serializer = ResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"].strip(), is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            base = os.environ.get("BRIGHTLOOP_PASSWORD_RESET_URL", "http://localhost:5173/reset-password")
            url = base + ("&" if "?" in base else "?") + urlencode({"uid": uid, "token": token})
            try:
                send_mail("Reset your Brightloop password",
                    f"Use this link to choose a new password:\n{url}\n\nIf you did not request this, ignore this email.",
                    os.environ.get("BRIGHTLOOP_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL),
                    [user.email], connection=_connection(), fail_silently=False)
            except (OSError, SMTPException, ValueError):
                # Keep the response identical for absent/inactive accounts and
                # transport failures; never log the user's email or reset token.
                logger.warning("Password reset email delivery unavailable; check email configuration.")
        return Response({"detail": "If the account can receive mail, password reset instructions will be sent."})


class ResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ConfirmThrottle]

    def post(self, request):
        serializer = ResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            pk = int(force_str(urlsafe_base64_decode(data["uid"])))
            if not 0 < pk <= 2**63 - 1:
                raise ValueError
        except (TypeError, ValueError, UnicodeDecodeError, OverflowError):
            raise ValidationError({"detail": "Invalid or expired reset link."})
        with transaction.atomic():
            User.objects.filter(pk=pk, is_active=True).update(is_active=F("is_active"))
            user = User.objects.select_for_update().filter(pk=pk, is_active=True).first()
            if user is None or not default_token_generator.check_token(user, data["token"]):
                raise ValidationError({"detail": "Invalid or expired reset link."})
            user.set_password(data["password"])
            user.save(update_fields=["password"])
            Token.objects.filter(user=user).delete()
        return Response({"detail": "Password updated. Log in with your new password."})
