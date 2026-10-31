from datetime import datetime, time, timedelta
import calendar

from django.db import transaction
from django.db.models import F, Prefetch, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from .models import Subscription, SubscriptionLine


def expire_quotations(queryset):
    queryset.filter(status__in=["quotation", "confirmed"], quote_expires_at__lte=timezone.now()).update(status="expired")


def refresh_expiry(queryset, as_of=None):
    """Persist expiry when historical billing is settled; never lose arrears."""
    today = as_of or timezone.localdate()
    ready = queryset.filter(expiry_date__lte=today).filter(
        Q(status="active", next_bill_date__gte=F("expiry_date")) | Q(status="paused"))
    for auto_close, status in [(True, "closed"), (False, "expired")]:
        ready.filter(plan__auto_close=auto_close).update(
            status=status, next_bill_date=F("expiry_date"),
            activated_at=Coalesce("activated_at", timezone.now()))


def due_subscriptions(as_of):
    return (Subscription.objects.filter(status="active", next_bill_date__lte=as_of,
                                        next_bill_date__lt=F("expiry_date"))
            .select_related("customer", "plan__tax", "subscription_discount")
            .prefetch_related(Prefetch("lines", queryset=SubscriptionLine.objects.select_related(
                "product", "variant", "tax").order_by("pk")))
            .order_by("next_bill_date", "pk"))


def lock_subscription(pk):
    # SQLite serializes writers on this update; select_for_update covers other DBs.
    Subscription.objects.filter(pk=pk).update(next_bill_date=F("next_bill_date"))
    return Subscription.objects.select_for_update().select_related("customer", "plan").get(pk=pk)


def settle_due(subscription, as_of=None):
    """Bill only this subscription under its OLD terms, inside the caller's transaction."""
    from gsk.billing import due_periods
    from gsk.integration import BillingORMRepository
    from gsk.service import run
    from .billing import due_candidates

    today = as_of or timezone.localdate()
    if subscription.status != "active" or subscription.next_bill_date >= subscription.expiry_date:
        return subscription

    class Repository(BillingORMRepository):
        def due_candidates(self, as_of):
            return due_candidates(as_of, subscription_ids=[subscription.pk])

    repo = Repository()
    result = run(repo, today)
    if result["errors"]:
        raise ValidationError({"detail": "Billing catch-up failed; no lifecycle or line changes were saved.",
                               "billing_errors": result["errors"]})
    subscription.refresh_from_db()
    if subscription.next_bill_date >= subscription.expiry_date:
        return subscription
    # GSK's normal rerun skips existing periods before calling ALIAR; repair a
    # stale cursor only when every skipped period is represented, even cancelled.
    periods = due_periods(anchor=subscription.start_date, next_bill_date=subscription.next_bill_date,
                         expiry_date=subscription.expiry_date, frequency=subscription.plan.frequency, as_of=today)
    for period in periods:
        if not repo.invoice_exists(subscription.pk, period.start):
            raise ValidationError({"detail": "Unsettled billing periods prevent this change."})
        subscription.next_bill_date = period.end
    if periods:
        subscription.save(update_fields=["next_bill_date"])
    return subscription


def skip_paused(subscription, as_of=None):
    from gsk.billing import due_periods
    today = as_of or timezone.localdate()
    if subscription.next_bill_date >= subscription.expiry_date:
        return
    # A cycle that began while paused remains skipped when resuming mid-cycle.
    cutoff = today - timedelta(days=1)
    for period in due_periods(anchor=subscription.start_date, next_bill_date=subscription.next_bill_date,
                             expiry_date=subscription.expiry_date, frequency=subscription.plan.frequency, as_of=cutoff):
        subscription.next_bill_date = period.end


def _next_date(anchor, frequency):
    if frequency == "daily":
        return anchor + timedelta(days=1)
    if frequency == "weekly":
        return anchor + timedelta(days=7)
    months = anchor.month - 1 + (12 if frequency == "yearly" else 1)
    year_offset, month = divmod(months, 12)
    year, month = anchor.year + year_offset, month + 1
    return anchor.replace(year=year, month=month, day=min(anchor.day, calendar.monthrange(year, month)[1]))


@transaction.atomic
def transition(subscription, action, *, expiry_date=None, actor=None):
    """Return fresh state after atomically settling or skipping old periods."""
    subscription = lock_subscription(subscription.pk)
    if actor is not None and actor.role == "customer":
        if (subscription.customer_id != actor.pk or action not in ("pause", "resume", "renew", "close")
                or subscription.status in ("draft", "quotation", "confirmed")
                or (subscription.status == "expired" and subscription.activated_at is None)):
            raise PermissionDenied("Customers may only manage their own activated subscriptions.")
    if action not in subscription.permitted_actions:
        raise ValidationError({"action": "Action is not permitted in the current state or by this plan."})
    if action == "close":
        subscription = settle_due(subscription)
        subscription.status = "closed"
        subscription.save(update_fields=["status"])
        return subscription
    if not subscription.customer.is_active or subscription.customer.role != "customer":
        raise ValidationError({"customer": "An active customer account is required."})
    today = timezone.localdate()
    if action in ("quote", "confirm", "activate"):
        if ((subscription.plan.available_from and today < subscription.plan.available_from)
                or (subscription.plan.available_to and today > subscription.plan.available_to)):
            raise ValidationError({"plan": "Plan is not available for new sign-ups today."})
        lines = list(subscription.lines.filter(active=True).select_related("product", "variant"))
        if sum(line.quantity for line in lines) < subscription.plan.minimum_quantity:
            raise ValidationError({"lines": "Plan minimum quantity is not met."})
        if any(not line.product.active or (line.variant and line.variant.product_id != line.product_id) for line in lines):
            raise ValidationError({"lines": "Products must be active and variants must match their products."})
        if action == "quote" and subscription.quote_expires_at is None:
            expires = today + timedelta(days=14)
            subscription.quote_expires_at = timezone.make_aware(datetime.combine(expires, time.min))
        if action == "activate":
            subscription.activated_at = timezone.now()
        subscription.status = {"quote": "quotation", "confirm": "confirmed", "activate": "active"}[action]
    elif action == "pause":
        subscription = settle_due(subscription)
        subscription.status = "paused"
    elif action == "resume":
        skip_paused(subscription)
        subscription.status = "active"
    elif action == "renew":
        boundary = max(today, subscription.expiry_date)
        end = expiry_date or _next_date(boundary, subscription.plan.frequency)
        if end <= boundary:
            raise ValidationError({"expiry_date": "Renewal expiry must be after both today and the existing expiry."})
        subscription = settle_due(subscription)
        if subscription.status == "paused":
            skip_paused(subscription)
        if subscription.expiry_date <= today:
            # A lapsed contract starts a new anchored term; never invoice the gap.
            subscription.start_date = boundary
            subscription.next_bill_date = boundary
        elif subscription.next_bill_date == subscription.expiry_date:
            # The final billed period may have been truncated at a mid-cycle
            # expiry. Its continuation must start there, not at an invalid
            # cursor on the old anchor or by rebilling the already paid span.
            from gsk.billing import due_periods
            try:
                due_periods(anchor=subscription.start_date, next_bill_date=subscription.next_bill_date,
                            expiry_date=end, frequency=subscription.plan.frequency, as_of=boundary)
            except ValueError:
                subscription.start_date = boundary
        subscription.expiry_date = end
        subscription.status = "active" if subscription.status != "paused" else "paused"
        subscription.quote_expires_at = None
    subscription.save()
    return subscription


@transaction.atomic
def maintain_subscription(pk, as_of=None):
    today = as_of or timezone.localdate()
    subscription = lock_subscription(pk)
    if subscription.expiry_date <= today and subscription.status == "active":
        settle_due(subscription, today)
    refresh_expiry(Subscription.objects.filter(pk=pk), today)
