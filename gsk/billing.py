"""Pure recurring-billing calculations shared by preview and invoice creation.

No Django models are imported here. YASCN and ALIAR can hand their records to this
module through the integration adapter without creating a circular dependency.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta


def _round_ratio(numerator: int, denominator: int) -> int:
    """Round a non-negative rational amount to the nearest paise, half up."""
    return (numerator + denominator // 2) // denominator


@dataclass(frozen=True)
class BillableLine:
    description: str
    quantity: int
    unit_price_paise: int  # Already includes any variant surcharge.
    tax_rate_bps: int = 0
    product_id: int | None = None


@dataclass(frozen=True)
class DiscountRule:
    id: int
    kind: str  # fixed or percent
    value: int  # paise when fixed; basis points when percent
    scope: str  # product or subscription
    product_id: int | None = None
    min_purchase_paise: int = 0
    min_quantity: int = 0
    starts_on: date | None = None
    ends_on: date | None = None
    usage_limit: int | None = None
    used_count: int = 0
    active: bool = True


@dataclass(frozen=True)
class BillingPeriod:
    start: date
    end: date  # Exclusive.


def _eligible(rule: DiscountRule, *, on: date, amount: int, quantity: int) -> bool:
    return (
        rule.active
        and (rule.starts_on is None or rule.starts_on <= on)
        and (rule.ends_on is None or on <= rule.ends_on)
        and (rule.usage_limit is None or rule.used_count < rule.usage_limit)
        and amount >= rule.min_purchase_paise
        and quantity >= rule.min_quantity
    )


def _saving(rule: DiscountRule, amount: int) -> int:
    if rule.value < 0 or (rule.kind == "percent" and rule.value > 10_000):
        raise ValueError("invalid discount value")
    if rule.kind == "fixed":
        return min(amount, rule.value)
    if rule.kind == "percent":
        return min(amount, _round_ratio(amount * rule.value, 10_000))
    raise ValueError(f"unsupported discount kind: {rule.kind}")


def _allocate(total: int, weights: list[int]) -> list[int]:
    """Allocate a whole-invoice discount proportionally with exact paise sum."""
    weight_sum = sum(weights)
    if not total or not weight_sum:
        return [0] * len(weights)
    floors = [total * w // weight_sum for w in weights]
    remaining = total - sum(floors)
    order = sorted(range(len(weights)), key=lambda i: (-(total * weights[i] % weight_sum), i))
    for i in order[:remaining]:
        floors[i] += 1
    return floors


def calculate_invoice(
    *,
    plan_fee_paise: int,
    plan_tax_rate_bps: int,
    lines: list[BillableLine],
    product_discounts: list[DiscountRule],
    subscription_discount: DiscountRule | None,
    period: BillingPeriod,
) -> dict:
    """Return an immutable-ready invoice snapshot; never mutate discount usage."""
    if plan_fee_paise < 0 or not 0 <= plan_tax_rate_bps <= 10_000:
        raise ValueError("invalid plan fee or tax rate")
    entries = [BillableLine("Plan fee", 1, plan_fee_paise, plan_tax_rate_bps)] + list(lines)
    for line in entries:
        if line.quantity < 1 or line.unit_price_paise < 0 or not 0 <= line.tax_rate_bps <= 10_000:
            raise ValueError("invalid billable line")
    amounts = [line.quantity * line.unit_price_paise for line in entries]
    subtotal = sum(amounts)

    product_allocations = [0] * len(entries)
    product_rule_ids: set[int] = set()
    for index, line in enumerate(entries):
        if line.product_id is None:
            continue
        candidates = [
            (_saving(rule, amounts[index]), rule.id)
            for rule in product_discounts
            if rule.scope == "product"
            and rule.product_id == line.product_id
            and _eligible(rule, on=period.start, amount=amounts[index], quantity=line.quantity)
        ]
        if candidates:
            saving, rule_id = max(candidates, key=lambda item: (item[0], -item[1]))
            product_allocations[index] = saving
            if saving:
                product_rule_ids.add(rule_id)

    whole_saving = 0
    if subscription_discount is not None and subscription_discount.scope == "subscription":
        if _eligible(subscription_discount, on=period.start, amount=subtotal, quantity=sum(line.quantity for line in lines)):
            whole_saving = _saving(subscription_discount, subtotal)

    if whole_saving > sum(product_allocations):
        allocations = _allocate(whole_saving, amounts)
        applied_discount_ids = [subscription_discount.id]  # type: ignore[union-attr]
    else:
        allocations = product_allocations
        applied_discount_ids = sorted(product_rule_ids)

    snapshot_lines = []
    tax_total = 0
    for line, amount, discount in zip(entries, amounts, allocations):
        taxable = amount - discount
        tax = _round_ratio(taxable * line.tax_rate_bps, 10_000)
        tax_total += tax
        snapshot_lines.append({
            "description": line.description,
            "product_id": line.product_id,
            "quantity": line.quantity,
            "unit_price_paise": line.unit_price_paise,
            "amount_paise": amount,
            "discount_paise": discount,
            "tax_rate_bps": line.tax_rate_bps,
            "tax_paise": tax,
        })
    discount_total = sum(allocations)
    return {
        "period_start": period.start.isoformat(),
        "period_end": period.end.isoformat(),
        "lines": snapshot_lines,
        "applied_discount_ids": applied_discount_ids,
        "subtotal_paise": subtotal,
        "discount_paise": discount_total,
        "tax_paise": tax_total,
        "total_paise": subtotal - discount_total + tax_total,
    }


def _boundary(anchor: date, frequency: str, index: int) -> date:
    if index < 0:
        raise ValueError("period index must be non-negative")
    if frequency == "daily":
        return anchor + timedelta(days=index)
    if frequency == "weekly":
        return anchor + timedelta(weeks=index)
    if frequency not in ("monthly", "yearly"):
        raise ValueError(f"unsupported frequency: {frequency}")
    months = anchor.month - 1 + index * (12 if frequency == "yearly" else 1)
    year, month_zero = divmod(months, 12)
    month = month_zero + 1
    return date(anchor.year + year, month, min(anchor.day, calendar.monthrange(anchor.year + year, month)[1]))


def due_periods(
    *, anchor: date, next_bill_date: date, expiry_date: date, frequency: str, as_of: date
) -> list[BillingPeriod]:
    """Return unbilled due periods, respecting exclusive expiry and anchor dates."""
    if expiry_date <= anchor or next_bill_date < anchor:
        raise ValueError("invalid subscription dates")
    if frequency == "daily":
        index = (next_bill_date - anchor).days
    elif frequency == "weekly":
        index = (next_bill_date - anchor).days // 7
    elif frequency == "monthly":
        index = (next_bill_date.year - anchor.year) * 12 + next_bill_date.month - anchor.month
    elif frequency == "yearly":
        index = next_bill_date.year - anchor.year
    else:
        raise ValueError(f"unsupported frequency: {frequency}")
    if _boundary(anchor, frequency, index) != next_bill_date:
        raise ValueError("next_bill_date is not on the subscription schedule")
    periods: list[BillingPeriod] = []
    while True:
        start = _boundary(anchor, frequency, index)
        if start > as_of or start >= expiry_date:
            break
        end = min(_boundary(anchor, frequency, index + 1), expiry_date)
        periods.append(BillingPeriod(start, end))
        index += 1
        if len(periods) > 10_000:
            raise ValueError("too many missed billing periods")
    return periods


def gross_mrr_paise(*, plan_fee_paise: int, lines: list[BillableLine], frequency: str) -> int:
    """Current contracted gross MRR, excluding discount and tax."""
    amount = plan_fee_paise + sum(line.quantity * line.unit_price_paise for line in lines)
    if frequency == "daily":
        return _round_ratio(amount * 365, 12)
    if frequency == "weekly":
        return _round_ratio(amount * 52, 12)
    if frequency == "monthly":
        return amount
    if frequency == "yearly":
        return _round_ratio(amount, 12)
    raise ValueError(f"unsupported frequency: {frequency}")
