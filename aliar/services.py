"""Finance mutations. Call these services rather than writing ledger rows directly."""

from copy import deepcopy
from datetime import timedelta
from smtplib import SMTPException

from django.apps import apps
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Max, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from .models import Invoice, Payment


class InvoiceDeliveryUnavailable(APIException):
    status_code = 503
    default_detail = "Invoice delivery failed. Check the email backend and retry."


def _lock_invoice(pk):
    # A write before reading serializes SQLite writers too (select_for_update is
    # a no-op on SQLite). PostgreSQL also takes a row lock for this update.
    Invoice.objects.filter(pk=pk).update(status=F("status"))
    return Invoice.objects.select_related("customer").get(pk=pk)


def balances(invoice):
    paid = invoice.payments.aggregate(value=Sum("amount_paise"))["value"] or 0
    remaining = (
        0 if invoice.status == Invoice.Status.CANCELLED else invoice.total_paise - paid
    )
    return {"paid_paise": paid, "balance_paise": remaining}


def _snapshot_amounts(snapshot, period):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("lines"), list):
        raise ValidationError(
            {"snapshot": "A calculation snapshot with lines is required."}
        )
    amounts = {}
    for key in ("subtotal_paise", "discount_paise", "tax_paise", "total_paise"):
        value = snapshot.get(key)
        if type(value) is not int or not 0 <= value <= 2**63 - 1:
            raise ValidationError(
                {"snapshot": f"{key} must be nonnegative 64-bit integer paise."}
            )
        amounts[key] = value
    if (
        amounts["discount_paise"] > amounts["subtotal_paise"]
        or amounts["total_paise"]
        != amounts["subtotal_paise"] - amounts["discount_paise"] + amounts["tax_paise"]
    ):
        raise ValidationError({"snapshot": "Calculation totals do not reconcile."})
    if (
        period.end <= period.start
        or snapshot.get("period_start") != period.start.isoformat()
        or snapshot.get("period_end") != period.end.isoformat()
    ):
        raise ValidationError(
            {"snapshot": "Snapshot dates must match the exclusive billing period."}
        )
    for field, line_field in (
        ("subtotal_paise", "amount_paise"),
        ("discount_paise", "discount_paise"),
        ("tax_paise", "tax_paise"),
    ):
        values = [
            line.get(line_field) if isinstance(line, dict) else None
            for line in snapshot["lines"]
        ]
        if (
            any(type(value) is not int or value < 0 for value in values)
            or sum(values) != amounts[field]
        ):
            raise ValidationError(
                {"snapshot": f"Line {line_field} values must reconcile with {field}."}
            )
    for line in snapshot["lines"]:
        quantity, price = line.get("quantity"), line.get("unit_price_paise")
        if (
            type(quantity) is not int
            or quantity < 1
            or type(price) is not int
            or price < 0
            or line["amount_paise"] != quantity * price
            or line["discount_paise"] > line["amount_paise"]
        ):
            raise ValidationError(
                {
                    "snapshot": "Line quantities, prices, amounts and discounts must reconcile."
                }
            )
    return amounts


def create_for_candidate(candidate, period, snapshot):
    """Drop-in implementation of GSK's repository creation method."""
    subscription = apps.get_model("yascn", "Subscription").objects.get(pk=candidate.id)
    try:
        return create_period_if_missing(subscription, period, snapshot)
    except ValidationError as exc:
        # GSK.run reports ValueError per period rather than failing the HTTP run.
        raise ValueError(str(exc.detail)) from exc


@transaction.atomic
def create_period_if_missing(subscription, period, snapshot, *, issued_on=None):
    """GSK adapter calls with a real Subscription and its calculated snapshot.

    Returns {id, number}, or None for ANY existing revision, including cancelled.
    Invoice, discount counters and billing cursor commit or roll back together.
    """
    model = type(subscription)
    model.objects.filter(pk=subscription.pk).update(next_bill_date=F("next_bill_date"))
    subscription = model.objects.get(pk=subscription.pk)
    if Invoice.objects.filter(
        subscription=subscription, period_start=period.start
    ).exists():
        if subscription.next_bill_date < period.end:
            model.objects.filter(pk=subscription.pk).update(next_bill_date=period.end)
        return None
    if (
        subscription.status != "active"
        or period.start < subscription.start_date
        or period.end > subscription.expiry_date
        or period.start > timezone.localdate()
    ):
        raise ValidationError(
            {
                "subscription": "Billing requires an active subscription and a due period within its dates."
            }
        )
    amounts = _snapshot_amounts(snapshot, period)
    issued_on = issued_on or timezone.localdate()
    invoice = Invoice.objects.create(
        subscription=subscription,
        customer_id=subscription.customer_id,
        period_start=period.start,
        period_end=period.end,
        issued_on=issued_on,
        due_on=issued_on + timedelta(days=subscription.payment_terms_days),
        snapshot=deepcopy(snapshot),
        **amounts,
    )
    discount_ids = snapshot.get("applied_discount_ids", [])
    if not isinstance(discount_ids, list) or any(
        type(pk) is not int for pk in discount_ids
    ):
        raise ValidationError({"snapshot": "Invalid applied discount IDs."})
    if discount_ids:
        discount_model = apps.get_model("yascn", "Discount")
        for pk in set(discount_ids):
            updated = (
                discount_model.objects.filter(pk=pk, active=True)
                .filter(
                    Q(usage_limit__isnull=True) | Q(used_count__lt=F("usage_limit"))
                )
                .update(used_count=F("used_count") + 1)
            )
            if not updated:
                raise ValidationError(
                    {
                        "snapshot": "Applied discount is unavailable or exhausted; rerun preview."
                    }
                )
    if subscription.next_bill_date < period.end:
        model.objects.filter(pk=subscription.pk).update(next_bill_date=period.end)
    return {"id": invoice.pk, "number": invoice.number}


@transaction.atomic
def confirm(pk):
    invoice = _lock_invoice(pk)
    if invoice.status != Invoice.Status.DRAFT:
        raise ValidationError({"detail": "Only draft invoices can be confirmed."})
    invoice.status = (
        Invoice.Status.PAID if invoice.total_paise == 0 else Invoice.Status.CONFIRMED
    )
    invoice.save(update_fields=["status"])
    return invoice


@transaction.atomic
def record_payment(pk, *, created_by, method, amount_paise, paid_on, note=""):
    invoice = _lock_invoice(pk)
    if invoice.status != Invoice.Status.CONFIRMED:
        raise ValidationError({"detail": "Payments require a confirmed invoice."})
    if (
        type(amount_paise) is not int
        or amount_paise <= 0
        or amount_paise > balances(invoice)["balance_paise"]
    ):
        raise ValidationError(
            {
                "amount_paise": "Must be positive integer paise and no greater than the balance."
            }
        )
    payment = Payment.objects.create(
        invoice=invoice,
        created_by=created_by,
        method=method,
        amount_paise=amount_paise,
        paid_on=paid_on,
        note=note,
    )
    if balances(invoice)["balance_paise"] == 0:
        invoice.status = Invoice.Status.PAID
        invoice.save(update_fields=["status"])
    return payment, invoice


@transaction.atomic
def cancel(pk):
    invoice = _lock_invoice(pk)
    if (
        invoice.status not in (Invoice.Status.DRAFT, Invoice.Status.CONFIRMED)
        or balances(invoice)["paid_paise"]
    ):
        raise ValidationError(
            {
                "detail": "Only unpaid draft or confirmed invoices can be cancelled; payments require a refund workflow."
            }
        )
    invoice.status = Invoice.Status.CANCELLED
    invoice.save(update_fields=["status"])
    return invoice


@transaction.atomic
def reissue(pk):
    invoice = _lock_invoice(pk)
    # Lock the shared subscription before checking sibling revisions.
    type(invoice.subscription).objects.filter(pk=invoice.subscription_id).update(
        next_bill_date=F("next_bill_date")
    )
    siblings = Invoice.objects.filter(
        subscription_id=invoice.subscription_id, period_start=invoice.period_start
    )
    if (
        invoice.status != Invoice.Status.CANCELLED
        or siblings.exclude(status="cancelled").exists()
    ):
        raise ValidationError(
            {"detail": "Reissue requires a cancelled invoice with no active revision."}
        )
    if siblings.aggregate(latest=Max("revision"))["latest"] != invoice.revision:
        raise ValidationError({"detail": "Reissue the latest cancelled revision."})
    today = timezone.localdate()
    return Invoice.objects.create(
        subscription_id=invoice.subscription_id,
        customer_id=invoice.customer_id,
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        revision=invoice.revision + 1,
        issued_on=today,
        due_on=today + timedelta(days=invoice.subscription.payment_terms_days),
        snapshot=deepcopy(invoice.snapshot),
        subtotal_paise=invoice.subtotal_paise,
        discount_paise=invoice.discount_paise,
        tax_paise=invoice.tax_paise,
        total_paise=invoice.total_paise,
    )


@transaction.atomic
def send(pk):
    invoice = _lock_invoice(pk)
    if invoice.status not in (Invoice.Status.CONFIRMED, Invoice.Status.PAID):
        raise ValidationError({"detail": "Confirm the invoice before sending."})
    if not invoice.customer.email:
        raise ValidationError({"detail": "Customer email is required."})
    try:
        send_mail(
            f"Brightloop invoice {invoice.number}",
            f"Invoice {invoice.number}\nDue: {invoice.due_on}\nTotal (paise): {invoice.total_paise}\nBalance (paise): {balances(invoice)['balance_paise']}",
            None,
            [invoice.customer.email],
            fail_silently=False,
        )
    except (OSError, SMTPException) as exc:
        raise InvoiceDeliveryUnavailable() from exc
    invoice.sent_at = timezone.now()
    invoice.save(update_fields=["sent_at"])
    return invoice
