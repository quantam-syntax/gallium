"""Billing-only routes for isolated GSK tests without teammate apps."""
from django.urls import path

from .views import BillingPreviewView, BillingRunView

urlpatterns = [
    path("api/billing/preview", BillingPreviewView.as_view()),
    path("api/billing/run", BillingRunView.as_view()),
]
