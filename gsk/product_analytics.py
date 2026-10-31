"""Product adoption trends from current active subscription lines."""
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone


def product_trends(as_of=None):
    from yascn.models import Product, SubscriptionLine

    today = as_of or timezone.localdate()
    recent_start = today - timedelta(days=29)
    previous_start = today - timedelta(days=59)
    week_zero = today - timedelta(days=today.weekday())
    weeks = [week_zero - timedelta(weeks=offset) for offset in range(8, -1, -1)]
    week_index = {week: index for index, week in enumerate(weeks)}
    counts = defaultdict(lambda: {"recent": 0, "previous": 0, "weeks": [0] * 9})

    # Distinct pairs prevent two active lines for the same product and contract
    # from inflating adoption. Dates come from the contract, not invoice copies.
    rows = (SubscriptionLine.objects.filter(
        active=True,
        subscription__status="active",
        subscription__start_date__gte=previous_start,
        subscription__start_date__lte=today,
    ).values_list("product_id", "subscription_id", "subscription__start_date").distinct())
    for product_id, _subscription_id, started_on in rows:
        bucket = counts[product_id]
        bucket["recent" if started_on >= recent_start else "previous"] += 1
        week = started_on - timedelta(days=started_on.weekday())
        if week in week_index:
            bucket["weeks"][week_index[week]] += 1

    products = []
    for product in Product.objects.order_by("name", "pk").only("id", "name", "active"):
        values = counts[product.pk]
        recent, previous = values["recent"], values["previous"]
        pace = "no_data" if recent == previous == 0 else (
            "fast" if recent > previous else "slow" if recent < previous else "steady"
        )
        products.append({
            "product_id": product.pk,
            "name": product.name,
            "active": product.active,
            "recent_count": recent,
            "previous_count": previous,
            "delta": recent - previous,
            "pace": pace,
            "weekly_counts": values["weeks"],
        })
    return {
        "as_of": today.isoformat(),
        "window_days": 30,
        "week_starts": [week.isoformat() for week in weeks],
        "products": products,
        "definition": "Current active subscriptions containing each product, grouped by contract start date.",
    }
