from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Tax, Product, Plan, Discount, QuotationTemplate, Subscription
from .permissions import CatalogPermission, SubscriptionPermission
from .serializers import (UserSerializer, RegisterSerializer, TaxSerializer, ProductSerializer,
                          VariantSerializer, PlanSerializer, DiscountSerializer,
                          TemplateSerializer, SubscriptionSerializer)
from .services import expire_quotations, transition


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user = serializer.save()
        except IntegrityError:
            raise ValidationError({"email": "An account with this email already exists."})
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, email=serializer.validated_data["email"].strip().lower(),
                            password=serializer.validated_data["password"])
        if user is None:
            return Response({"detail": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class Pagination(PageNumberPagination):
    page_size = 25


class CatalogViewSet(viewsets.ModelViewSet):
    permission_classes = [CatalogPermission]
    pagination_class = Pagination

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "This record is in use and cannot be deleted."})


class TaxViewSet(CatalogViewSet):
    queryset = Tax.objects.order_by("pk")
    serializer_class = TaxSerializer


class ProductViewSet(CatalogViewSet):
    queryset = Product.objects.select_related("tax").prefetch_related("variants").order_by("pk")
    serializer_class = ProductSerializer

    @action(detail=True, methods=["post"])
    def variants(self, request, pk=None):
        product = self.get_object()
        serializer = VariantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["patch", "delete"], url_path=r"variants/(?P<variant_id>[^/.]+)")
    def variant_detail(self, request, pk=None, variant_id=None):
        variant = get_object_or_404(self.get_object().variants, pk=variant_id)
        if request.method == "DELETE":
            self.perform_destroy(variant)
            return Response(status=204)
        serializer = VariantSerializer(variant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PlanViewSet(CatalogViewSet):
    queryset = Plan.objects.select_related("tax").order_by("pk")
    serializer_class = PlanSerializer


class DiscountViewSet(CatalogViewSet):
    queryset = Discount.objects.select_related("product").order_by("pk")
    serializer_class = DiscountSerializer


class TemplateViewSet(CatalogViewSet):
    queryset = QuotationTemplate.objects.select_related("plan").prefetch_related("lines__product", "lines__variant").order_by("pk")
    serializer_class = TemplateSerializer


class SubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [SubscriptionPermission]
    pagination_class = Pagination
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        qs = Subscription.objects.all()
        if self.request.user.role == "customer":
            qs = qs.filter(customer=self.request.user)
        expire_quotations(qs)
        return qs.select_related("customer", "plan", "subscription_discount").prefetch_related(
            "lines__product", "lines__variant", "lines__tax").order_by("pk")

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            instance = get_object_or_404(self.get_queryset().select_for_update(), pk=kwargs["pk"])
            if instance.status != "draft":
                raise ValidationError({"detail": "Only draft subscriptions can be edited in Phase 1."})
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get("partial", False))
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            instance = get_object_or_404(self.get_queryset().select_for_update(), pk=kwargs["pk"])
            if instance.status != "draft":
                raise ValidationError({"detail": "Only draft subscriptions can be deleted."})
            try:
                instance.delete()
            except ProtectedError:
                raise ValidationError({"detail": "This subscription is in use and cannot be deleted."})
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        # Expiry is persisted before the transaction so a rejected action cannot undo it.
        queryset = self.get_queryset()
        with transaction.atomic():
            subscription = get_object_or_404(queryset.select_for_update(), pk=pk)
            subscription = transition(subscription, request.data.get("action"))
            return Response(self.get_serializer(subscription).data)
