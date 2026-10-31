"""Read-only bridge from YASCN's ORM to GSK's billing calculation contract.

GSK can delegate its repository's due_candidates(as_of) to this function. This
module never creates invoices, consumes discounts, or advances billing cursors.
"""
from dataclasses import fields
from datetime import date

from gsk.billing import BillableLine, DiscountRule
from gsk.service import BillingCandidate

from .models import Discount
from .services import due_subscriptions


def _discount_rule(discount):
    if discount is None:
        return None
    return DiscountRule(**{field.name: getattr(discount, field.name) for field in fields(DiscountRule)})


def _tax_rate(tax):
    return tax.rate_bps if tax is not None and tax.active else 0


def due_candidates(as_of: date, *, subscription_ids=None) -> list[BillingCandidate]:
    """Return billing inputs with bounded queries, preserving historical prices.

    Discount date, amount, quantity, and usage checks remain GSK's responsibility
    for each billing period, including historical periods before current expiry.
    """
    queryset = due_subscriptions(as_of)
    if subscription_ids is not None:
        queryset = queryset.filter(pk__in=subscription_ids)
    subscriptions = list(queryset)
    product_ids = {line.product_id for sub in subscriptions for line in sub.lines.all() if line.active}
    rules_by_product = {}
    if product_ids:
        for discount in Discount.objects.filter(scope="product", active=True, product_id__in=product_ids).order_by("pk"):
            rules_by_product.setdefault(discount.product_id, []).append(_discount_rule(discount))

    candidates = []
    for sub in subscriptions:
        lines = [line for line in sub.lines.all() if line.active]
        used_products = sorted({line.product_id for line in lines})
        candidates.append(BillingCandidate(
            id=sub.pk,
            number=sub.number,
            customer_name=sub.customer.company_name or sub.customer.full_name,
            start_date=sub.start_date,
            expiry_date=sub.expiry_date,
            next_bill_date=sub.next_bill_date,
            frequency=sub.plan.frequency,
            plan_fee_paise=sub.plan.base_price_paise,
            plan_tax_rate_bps=_tax_rate(sub.plan.tax),
            lines=[BillableLine(
                description=f"{line.product.name} — {line.variant.name}" if line.variant else line.product.name,
                quantity=line.quantity,
                unit_price_paise=line.unit_price_paise,
                tax_rate_bps=_tax_rate(line.tax),
                product_id=line.product_id,
            ) for line in lines],
            product_discounts=[rule for product_id in used_products for rule in rules_by_product.get(product_id, [])],
            subscription_discount=_discount_rule(sub.subscription_discount),
            payment_terms_days=sub.payment_terms_days,
        ))
    return candidates
