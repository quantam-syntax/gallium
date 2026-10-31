from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import reporting, services
from .models import Invoice
from .serializers import DashboardFilterSerializer, InvoiceSerializer, PaymentSerializer


def staff(user):
    return getattr(user, "role", None) in ("admin", "staff")


def require_staff(user):
    if not staff(user):
        raise PermissionDenied("Staff access required.")


class FinancePagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class InvoiceAccess:
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = (
            Invoice.objects.select_related("customer")
            .with_balances()
            .order_by("-issued_on", "-id")
        )
        return qs if staff(self.request.user) else qs.filter(customer=self.request.user)


class InvoiceList(InvoiceAccess, generics.ListAPIView):
    serializer_class = InvoiceSerializer
    pagination_class = FinancePagination

    def get_queryset(self):
        qs = super().get_queryset()
        if value := self.request.query_params.get("status"):
            qs = qs.filter(status=value)
        if self.request.query_params.get("overdue") == "true":
            from django.utils import timezone

            qs = qs.exclude(status="cancelled").filter(
                due_on__lt=timezone.localdate(), balance_paise__gt=0
            )
        if self.request.query_params.get("outstanding") == "true":
            qs = qs.exclude(status="cancelled").filter(balance_paise__gt=0)
        return qs


class InvoiceDetail(InvoiceAccess, generics.RetrieveAPIView):
    serializer_class = InvoiceSerializer


class InvoiceAction(InvoiceAccess, APIView):
    def post(self, request, pk, action):
        require_staff(request.user)
        invoice = get_object_or_404(self.get_queryset(), pk=pk)
        result = getattr(services, action)(invoice.pk)
        result = (
            Invoice.objects.select_related("customer").with_balances().get(pk=result.pk)
        )
        return Response(
            InvoiceSerializer(result).data,
            status=status.HTTP_201_CREATED
            if action == "reissue"
            else status.HTTP_200_OK,
        )


class InvoicePayments(InvoiceAccess, generics.GenericAPIView):
    serializer_class = PaymentSerializer
    pagination_class = FinancePagination

    def get(self, request, pk):
        invoice = get_object_or_404(self.get_queryset(), pk=pk)
        return self.get_paginated_response(
            self.get_serializer(
                self.paginate_queryset(invoice.payments.all()), many=True
            ).data
        )

    def post(self, request, pk):
        require_staff(request.user)
        invoice = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment, invoice = services.record_payment(
            invoice.pk, created_by=request.user, **serializer.validated_data
        )
        return Response(
            {"payment": PaymentSerializer(payment).data, **services.balances(invoice)},
            status=status.HTTP_201_CREATED,
        )


class Dashboard(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        require_staff(request.user)
        serializer = DashboardFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(
                reporting.dashboard(
                    serializer.validated_data.get("from"),
                    serializer.validated_data.get("to"),
                )
            )
        except LookupError:
            return Response(
                {"detail": "YASCN subscription models are not installed."}, status=503
            )
