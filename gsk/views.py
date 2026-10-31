"""Staff-only Billing Control Tower endpoints."""
from datetime import date

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .integration import IntegrationPending, get_repository
from .assistant import answer as assistant_answer
from .product_analytics import product_trends
from .service import preview, run


def _as_of(request):
    raw = request.query_params.get("as_of") if request.method == "GET" else request.data.get("as_of")
    value = date.fromisoformat(raw) if raw else timezone.localdate()
    if value > timezone.localdate():
        raise ValueError("future billing dates are not allowed")
    return value


class _BillingView(APIView):
    permission_classes = [IsAuthenticated]

    def _handle(self, request, operation):
        if getattr(request.user, "role", None) not in ("admin", "staff"):
            return Response({"detail": "staff access required"}, status=403)
        try:
            as_of = _as_of(request)
        except (ValueError, TypeError):
            return Response({"detail": "as_of must be a valid past or present ISO date"}, status=400)
        try:
            repo = get_repository()
        except IntegrationPending as exc:
            return Response({"detail": str(exc)}, status=503)
        return Response(operation(repo, as_of))


class BillingPreviewView(_BillingView):
    def get(self, request):
        return self._handle(request, preview)


class BillingRunView(_BillingView):
    def post(self, request):
        return self._handle(request, run)


class ProductTrendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, "role", None) not in ("admin", "staff"):
            return Response({"detail": "staff access required"}, status=403)
        return Response(product_trends())


class AssistantChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "assistant"

    def post(self, request):
        if getattr(request.user, "role", None) not in ("admin", "staff", "customer"):
            return Response({"detail": "account role required"}, status=403)
        if not isinstance(request.data, dict):
            return Response({"detail": "Expected a chat request object."}, status=400)
        message = request.data.get("message")
        history = request.data.get("history", [])
        if not isinstance(message, str) or not message.strip() or len(message) > 1000:
            return Response({"message": "Enter a question of 1–1000 characters."}, status=400)
        if (not isinstance(history, list) or len(history) > 8 or any(
            not isinstance(item, dict) or item.get("role") not in ("user", "assistant")
            or not isinstance(item.get("content"), str) or len(item["content"]) > 1000
            for item in history
        )):
            return Response({"history": "Use at most eight short chat messages."}, status=400)
        try:
            return Response(assistant_answer(message.strip(), history, request.user))
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=503)
