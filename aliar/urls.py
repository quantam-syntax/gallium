from django.urls import path

from . import views

urlpatterns = [
    path("api/invoices", views.InvoiceList.as_view(), name="aliar-invoices"),
    path("api/invoices/<int:pk>", views.InvoiceDetail.as_view(), name="aliar-invoice"),
    path(
        "api/invoices/<int:pk>/payments",
        views.InvoicePayments.as_view(),
        name="aliar-payments",
    ),
    path("api/dashboard", views.Dashboard.as_view(), name="aliar-dashboard"),
    *[
        path(
            f"api/invoices/<int:pk>/{action}",
            views.InvoiceAction.as_view(),
            {"action": action},
            name=f"aliar-{action}",
        )
        for action in ("confirm", "cancel", "send", "reissue")
    ],
]
