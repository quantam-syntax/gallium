import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import BigIntegerField, Case, F, Q, Sum, Value, When
from django.utils import timezone


def invoice_number():
    return "INV-" + uuid.uuid4().hex.upper()


class InvoiceQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if set(kwargs) - {"status", "sent_at"}:
            raise ValidationError("Issued invoice data is immutable.")
        return super().update(**kwargs)

    def delete(self):
        raise ValidationError("Preserve invoice history; cancel instead.")

    def with_balances(self):
        from django.db.models.functions import Coalesce

        return self.annotate(
            paid_paise=Coalesce(Sum("payments__amount_paise"), 0),
        ).annotate(
            balance_paise=Case(
                When(status="cancelled", then=Value(0)),
                default=F("total_paise") - F("paid_paise"),
                output_field=BigIntegerField(),
            )
        )


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        CONFIRMED = "confirmed"
        PAID = "paid"
        CANCELLED = "cancelled"

    number = models.CharField(
        max_length=40, unique=True, default=invoice_number, editable=False
    )
    subscription = models.ForeignKey(
        "yascn.Subscription", on_delete=models.PROTECT, related_name="invoices"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="invoices"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    revision = models.PositiveIntegerField(default=1)
    issued_on = models.DateField(default=timezone.localdate)
    due_on = models.DateField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    subtotal_paise = models.PositiveBigIntegerField()
    discount_paise = models.PositiveBigIntegerField(default=0)
    tax_paise = models.PositiveBigIntegerField(default=0)
    total_paise = models.PositiveBigIntegerField()
    snapshot = models.JSONField()
    sent_at = models.DateTimeField(null=True, blank=True)
    objects = InvoiceQuerySet.as_manager()

    class Meta:
        ordering = ["-issued_on", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "period_start", "revision"],
                name="aliar_period_revision_unique",
            ),
            models.UniqueConstraint(
                fields=["subscription", "period_start"],
                condition=~Q(status="cancelled"),
                name="aliar_one_active_period",
            ),
            models.CheckConstraint(
                condition=Q(period_end__gt=F("period_start")), name="aliar_period_order"
            ),
            models.CheckConstraint(
                condition=Q(revision__gte=1), name="aliar_positive_revision"
            ),
            models.CheckConstraint(
                condition=Q(discount_paise__lte=F("subtotal_paise")),
                name="aliar_discount_limit",
            ),
            models.CheckConstraint(
                condition=Q(
                    total_paise=F("subtotal_paise")
                    - F("discount_paise")
                    + F("tax_paise")
                ),
                name="aliar_total_matches",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["draft", "confirmed", "paid", "cancelled"]),
                name="aliar_valid_status",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "due_on"]),
            models.Index(fields=["customer", "issued_on"]),
            models.Index(fields=["issued_on"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            for field in self._meta.concrete_fields:
                if field.name not in {"id", "status", "sent_at"} and getattr(
                    old, field.attname
                ) != getattr(self, field.attname):
                    raise ValidationError(
                        {
                            field.name: "Issued invoice data is immutable; cancel and reissue."
                        }
                    )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Preserve invoice history; cancel instead.")


class PaymentQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Payments are immutable.")

    def delete(self):
        raise ValidationError("Payments are immutable.")


class Payment(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="payments"
    )
    method = models.CharField(max_length=40)
    amount_paise = models.PositiveBigIntegerField()
    paid_on = models.DateField(db_index=True)
    note = models.TextField(blank=True, max_length=2000)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_payments",
    )
    objects = PaymentQuerySet.as_manager()

    class Meta:
        ordering = ["-paid_on", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_paise__gt=0), name="aliar_positive_payment"
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Payments are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Payments are immutable.")
