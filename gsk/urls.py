"""Root URL wiring. GSK registers teammate URL modules during integration."""
from django.contrib import admin
from django.urls import include, path

from .views import BillingPreviewView, BillingRunView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("yascn.urls")),
    path("", include("aliar.urls")),
    path("api/billing/preview", BillingPreviewView.as_view()),
    path("api/billing/run", BillingRunView.as_view()),
]
