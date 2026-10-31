"""Exercise real app APIs without editing GSK-owned root URL wiring."""

from django.urls import include, path

urlpatterns = [
    path("", include("gsk.urls")),
    path("", include("aliar.urls")),
]
