"""Billing orchestration independent of the teammates' ORM model layout."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Protocol

from .billing import BillableLine, BillingPeriod, DiscountRule, calculate_invoice, due_periods


@dataclass(frozen=True)
class BillingCandidate:
    id: int
    number: str
    customer_name: str
    start_date: date
    expiry_date: date
    next_bill_date: date
    frequency: str
    plan_fee_paise: int
    plan_tax_rate_bps: int
    lines: list[BillableLine]
    product_discounts: list[DiscountRule]
    subscription_discount: DiscountRule | None
    payment_terms_days: int


class BillingRepository(Protocol):
    def due_candidates(self, as_of: date) -> list[BillingCandidate]: ...

    def invoice_exists(self, subscription_id: int, period_start: date) -> bool: ...

    def create_period_if_missing(
        self, candidate: BillingCandidate, period: BillingPeriod, snapshot: dict
    ) -> dict | None:
        """Atomically create invoice, consume discounts, and advance cursor.

        Return `{id, number}` on creation or None when the period already exists.
        A database constraint must enforce uniqueness even if two runs race.
        """


def _due_items(repo: BillingRepository, as_of: date):
    due = []
    for candidate in repo.due_candidates(as_of):
        try:
            periods = due_periods(
                anchor=candidate.start_date,
                next_bill_date=candidate.next_bill_date,
                expiry_date=candidate.expiry_date,
                frequency=candidate.frequency,
                as_of=as_of,
            )
        except ValueError as exc:
            yield candidate, None, str(exc)
            continue
        for period in periods:
            if repo.invoice_exists(candidate.id, period.start):
                continue
            due.append((candidate, period))
    for candidate, period in sorted(due, key=lambda item: (item[1].start, item[0].id)):
        yield candidate, period, None


def _quote(candidate: BillingCandidate, period: BillingPeriod, projected_uses: dict[int, int]) -> dict:
    def adjusted(rule: DiscountRule) -> DiscountRule:
        return replace(rule, used_count=max(rule.used_count, projected_uses.get(rule.id, 0)))

    return calculate_invoice(
        plan_fee_paise=candidate.plan_fee_paise,
        plan_tax_rate_bps=candidate.plan_tax_rate_bps,
        lines=candidate.lines,
        product_discounts=[adjusted(rule) for rule in candidate.product_discounts],
        subscription_discount=adjusted(candidate.subscription_discount) if candidate.subscription_discount else None,
        period=period,
    )


def _consume_projected(candidate: BillingCandidate, snapshot: dict, projected_uses: dict[int, int]) -> None:
    rules = {rule.id: rule for rule in candidate.product_discounts}
    if candidate.subscription_discount:
        rules[candidate.subscription_discount.id] = candidate.subscription_discount
    for rule_id in snapshot["applied_discount_ids"]:
        projected_uses[rule_id] = max(projected_uses.get(rule_id, 0), rules[rule_id].used_count) + 1


def preview(repo: BillingRepository, as_of: date) -> dict:
    items, exceptions = [], []
    projected_uses: dict[int, int] = {}
    for candidate, period, schedule_error in _due_items(repo, as_of):
        if schedule_error:
            exceptions.append({"subscription_id": candidate.id, "reason": schedule_error})
            continue
        try:
            snapshot = _quote(candidate, period, projected_uses)
            _consume_projected(candidate, snapshot, projected_uses)
            items.append({
                "subscription_id": candidate.id,
                "number": candidate.number,
                "customer_name": candidate.customer_name,
                "period_start": snapshot["period_start"],
                "period_end": snapshot["period_end"],
                "subtotal_paise": snapshot["subtotal_paise"],
                "discount_paise": snapshot["discount_paise"],
                "tax_paise": snapshot["tax_paise"],
                "total_paise": snapshot["total_paise"],
                "issues": [],
            })
        except ValueError as exc:
            exceptions.append({"subscription_id": candidate.id, "reason": str(exc)})
    return {
        "as_of": as_of.isoformat(),
        "due_count": len(items),
        "expected_total_paise": sum(item["total_paise"] for item in items),
        "items": items,
        "exceptions": exceptions,
    }


def run(repo: BillingRepository, as_of: date) -> dict:
    invoices, errors = [], []
    skipped = 0
    projected_uses: dict[int, int] = {}
    for candidate, period, schedule_error in _due_items(repo, as_of):
        if schedule_error:
            errors.append({"subscription_id": candidate.id, "reason": schedule_error})
            continue
        try:
            snapshot = _quote(candidate, period, projected_uses)
            result = repo.create_period_if_missing(candidate, period, snapshot)
            if result is None:
                skipped += 1
            else:
                _consume_projected(candidate, snapshot, projected_uses)
                invoices.append({
                    "id": result["id"], "number": result["number"],
                    "subscription_id": candidate.id,
                    "total_paise": snapshot["total_paise"],
                })
        except (ValueError, RuntimeError) as exc:
            errors.append({"subscription_id": candidate.id, "period_start": period.start.isoformat(), "reason": str(exc)})
    return {
        "created_count": len(invoices),
        "created_total_paise": sum(invoice["total_paise"] for invoice in invoices),
        "skipped_count": skipped,
        "error_count": len(errors),
        "invoices": invoices,
        "errors": errors,
    }
