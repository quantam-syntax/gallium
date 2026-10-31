"""SQL aggregates: invoice and payment joins never multiply invoice totals."""

from django.apps import apps
from django.db.models import (
    BigIntegerField,
    Case,
    Count,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone
from gsk.billing import gross_mrr_paise

from .models import Invoice, Payment


def active_metrics():
    subscription = apps.get_model("yascn", "Subscription")
    line = apps.get_model("yascn", "SubscriptionLine")
    totals = (
        line.objects.filter(subscription_id=OuterRef("pk"), active=True)
        .order_by()
        .values("subscription_id")
        .annotate(
            amount=Sum(
                F("quantity") * F("unit_price_paise"), output_field=BigIntegerField()
            )
        )
        .values("amount")
    )
    # All frequency ratios are exact multiples of 1/12. Obtain the numerators
    # from GSK's shared calculator, then round per subscription inside SQL.
    factor = Case(
        *[
            When(
                plan__frequency=frequency,
                then=Value(
                    gross_mrr_paise(plan_fee_paise=12, lines=[], frequency=frequency)
                ),
            )
            for frequency in ("daily", "weekly", "monthly", "yearly")
        ],
        default=Value(0),
        output_field=IntegerField(),
    )
    active = (
        subscription.objects.filter(status="active")
        .annotate(
            line_amount=Coalesce(
                Subquery(totals, output_field=BigIntegerField()),
                Value(0),
                output_field=BigIntegerField(),
            ),
        )
        .annotate(
            mrr=Cast(
                ((F("plan__base_price_paise") + F("line_amount")) * factor + 6) / 12,
                BigIntegerField(),
            )
        )
    )
    result = active.aggregate(active_count=Count("pk"), gross_mrr_paise=Sum("mrr"))
    result["gross_mrr_paise"] = result["gross_mrr_paise"] or 0
    return result


def dashboard(start=None, end=None):
    invoices = Invoice.objects.exclude(status="cancelled")
    payments = Payment.objects.exclude(invoice__status="cancelled")
    if start:
        invoices = invoices.filter(issued_on__gte=start)
        payments = payments.filter(paid_on__gte=start)
    if end:
        invoices = invoices.filter(issued_on__lte=end)
        payments = payments.filter(paid_on__lte=end)
    # Correlated indexed payment aggregate keeps one row per invoice.
    paid = (
        Payment.objects.filter(invoice_id=OuterRef("pk"))
        .order_by()
        .values("invoice_id")
        .annotate(amount=Sum("amount_paise"))
        .values("amount")
    )
    open_invoices = (
        Invoice.objects.exclude(status="cancelled")
        .annotate(
            remaining=F("total_paise")
            - Coalesce(
                Subquery(paid, output_field=BigIntegerField()),
                Value(0),
                output_field=BigIntegerField(),
            ),
        )
        .filter(remaining__gt=0)
    )
    open_totals = open_invoices.aggregate(
        outstanding_paise=Sum("remaining"),
        overdue_count=Count("pk", filter=Q(due_on__lt=timezone.localdate())),
    )
    return {
        **active_metrics(),
        "invoiced_paise": invoices.aggregate(value=Sum("total_paise"))["value"] or 0,
        "collected_paise": payments.aggregate(value=Sum("amount_paise"))["value"] or 0,
        "outstanding_paise": open_totals["outstanding_paise"] or 0,
        "overdue_count": open_totals["overdue_count"],
    }
