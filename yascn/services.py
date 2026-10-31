from datetime import datetime, time, timedelta

from django.db import transaction
from django.db.models import F, Prefetch
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Subscription, SubscriptionLine


def expire_quotations(queryset):
    """Lazily persist quotation expiry on reads and transition attempts."""
    queryset.filter(status__in=["quotation", "confirmed"], quote_expires_at__lte=timezone.now()).update(status="expired")


def due_subscriptions(as_of):
    """Include past due cycles even when the contract has since expired."""
    return (Subscription.objects.filter(status="active", next_bill_date__lte=as_of,
                                        next_bill_date__lt=F("expiry_date"))
            .select_related("customer", "plan__tax", "subscription_discount")
            .prefetch_related(Prefetch("lines", queryset=SubscriptionLine.objects.select_related(
                "product", "variant", "tax").order_by("pk")))
            .order_by("next_bill_date", "pk"))


@transaction.atomic
def transition(subscription, action):
    """Apply a core action and return the freshly locked subscription instance."""
    # Lock and reload here too: callers other than HTTP views must not activate
    # using stale state, permissions, or dates retained on a Python instance.
    subscription = (Subscription.objects.select_for_update()
                    .select_related("customer", "plan").get(pk=subscription.pk))
    if action not in subscription.permitted_actions:
        raise ValidationError({"action": "Action is not permitted in the current state."})
    if not subscription.customer.is_active or subscription.customer.role != "customer":
        raise ValidationError({"customer": "An active customer account is required."})
    today = timezone.localdate()
    if ((subscription.plan.available_from and today < subscription.plan.available_from)
            or (subscription.plan.available_to and today > subscription.plan.available_to)):
        raise ValidationError({"plan": "Plan is not available for new sign-ups today."})
    lines = list(subscription.lines.filter(active=True).select_related("product", "variant"))
    if sum(line.quantity for line in lines) < subscription.plan.minimum_quantity:
        raise ValidationError({"lines": "Plan minimum quantity is not met."})
    if any(not line.product.active or (line.variant and line.variant.product_id != line.product_id) for line in lines):
        raise ValidationError({"lines": "Products must be active and variants must match their products."})
    if action == "quote" and subscription.quote_expires_at is None:
        expires = timezone.localdate() + timedelta(days=14)
        subscription.quote_expires_at = timezone.make_aware(datetime.combine(expires, time.min))
    subscription.status = {"quote": "quotation", "confirm": "confirmed", "activate": "active"}[action]
    subscription.save(update_fields=["status", "quote_expires_at"])
    return subscription
