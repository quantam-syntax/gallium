"""Staff-only Billing Control Tower endpoints."""
from datetime import date

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .integration import IntegrationPending, get_repository
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
