from django.urls import path
from rest_framework.routers import SimpleRouter
from .password_reset import ResetRequestView, ResetConfirmView

from .views import (RegisterView, LoginView, MeView, ProductViewSet, PlanViewSet,
                    TaxViewSet, DiscountViewSet, TemplateViewSet, SubscriptionViewSet)

router = SimpleRouter(trailing_slash=False)
router.register("products", ProductViewSet, basename="product")
router.register("plans", PlanViewSet, basename="plan")
router.register("taxes", TaxViewSet, basename="tax")
router.register("discounts", DiscountViewSet, basename="discount")
router.register("templates", TemplateViewSet, basename="template")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")

urlpatterns = [
    path("auth/register", RegisterView.as_view(), name="register"),
    path("auth/login", LoginView.as_view(), name="login"),
    path("auth/me", MeView.as_view(), name="me"),
    path("auth/password-reset/request", ResetRequestView.as_view(), name="password-reset-request"),
    path("auth/password-reset/confirm", ResetConfirmView.as_view(), name="password-reset-confirm"),
] + router.urls
