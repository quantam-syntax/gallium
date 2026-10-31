from datetime import date
from unittest import TestCase

from gsk.billing import BillableLine, BillingPeriod, DiscountRule, calculate_invoice, due_periods
from gsk.service import BillingCandidate, preview, run


class BillingCalculationTests(TestCase):
    def test_variant_price_discount_then_tax_and_no_double_surcharge(self):
        snapshot = calculate_invoice(
            plan_fee_paise=100_000,
            plan_tax_rate_bps=1800,
            lines=[BillableLine("Odoo add-on", 1, 56_000, 1800, product_id=4)],
            product_discounts=[DiscountRule(7, "fixed", 6_000, "product", product_id=4)],
            subscription_discount=None,
            period=BillingPeriod(date(2026, 10, 31), date(2026, 11, 30)),
        )
        self.assertEqual(snapshot["subtotal_paise"], 156_000)
        self.assertEqual(snapshot["discount_paise"], 6_000)
        self.assertEqual(snapshot["tax_paise"], 27_000)
        self.assertEqual(snapshot["total_paise"], 177_000)
        self.assertEqual(snapshot["applied_discount_ids"], [7])

    def test_whole_discount_wins_and_tax_allocation_preserves_total(self):
        snapshot = calculate_invoice(
            plan_fee_paise=101,
            plan_tax_rate_bps=1000,
            lines=[BillableLine("Seat", 1, 99, 2000, product_id=2)],
            product_discounts=[DiscountRule(1, "fixed", 20, "product", product_id=2)],
            subscription_discount=DiscountRule(3, "fixed", 51, "subscription"),
            period=BillingPeriod(date(2026, 10, 1), date(2026, 11, 1)),
        )
        self.assertEqual(snapshot["discount_paise"], 51)
        self.assertEqual(sum(line["discount_paise"] for line in snapshot["lines"]), 51)
        self.assertEqual(snapshot["applied_discount_ids"], [3])
        self.assertEqual(snapshot["total_paise"], 149 + snapshot["tax_paise"])

    def test_month_end_anchor_and_missed_cycles(self):
        periods = due_periods(
            anchor=date(2026, 1, 31),
            next_bill_date=date(2026, 1, 31),
            expiry_date=date(2026, 4, 15),
            frequency="monthly",
            as_of=date(2026, 4, 1),
        )
        self.assertEqual([p.start for p in periods], [
            date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)
        ])
        self.assertEqual(periods[-1].end, date(2026, 4, 15))


class MemoryRepo:
    def __init__(self, candidate):
        self.candidate = candidate
        self.invoices = {}

    def due_candidates(self, as_of):
        return [self.candidate]

    def invoice_exists(self, subscription_id, period_start):
        return (subscription_id, period_start) in self.invoices

    def create_period_if_missing(self, candidate, period, snapshot):
        key = candidate.id, period.start
        if key in self.invoices:
            return None
        result = {"id": len(self.invoices) + 1, "number": f"INV-{len(self.invoices) + 1:04d}"}
        self.invoices[key] = (result, snapshot)
        return result


class BillingFlowTests(TestCase):
    def test_preview_matches_run_and_second_run_creates_nothing(self):
        repo = MemoryRepo(BillingCandidate(
            id=12, number="SUB-0012", customer_name="Example Shop",
            start_date=date(2026, 10, 31), expiry_date=date(2026, 12, 31),
            next_bill_date=date(2026, 10, 31), frequency="monthly",
            plan_fee_paise=100_000, plan_tax_rate_bps=1800,
            lines=[BillableLine("Odoo", 1, 56_000, 1800, 4)],
            product_discounts=[], subscription_discount=None, payment_terms_days=14,
        ))
        before = preview(repo, date(2026, 10, 31))
        first = run(repo, date(2026, 10, 31))
        second = run(repo, date(2026, 10, 31))
        self.assertEqual(before["due_count"], 1)
        self.assertEqual(first["created_count"], 1)
        self.assertEqual(first["invoices"][0]["total_paise"], before["expected_total_paise"])
        self.assertEqual(first["created_total_paise"], before["expected_total_paise"])
        self.assertEqual(second["created_count"], 0)
        self.assertEqual(second["created_total_paise"], 0)
        self.assertEqual(len(repo.invoices), 1)

    def test_limited_discount_is_used_once_across_catch_up_periods(self):
        repo = MemoryRepo(BillingCandidate(
            id=13, number="SUB-0013", customer_name="Example Shop",
            start_date=date(2026, 8, 1), expiry_date=date(2026, 12, 1),
            next_bill_date=date(2026, 8, 1), frequency="monthly",
            plan_fee_paise=100_000, plan_tax_rate_bps=0,
            lines=[], product_discounts=[],
            subscription_discount=DiscountRule(9, "fixed", 10_000, "subscription", usage_limit=1),
            payment_terms_days=14,
        ))
        before = preview(repo, date(2026, 9, 1))
        first = run(repo, date(2026, 9, 1))
        self.assertEqual([item["total_paise"] for item in before["items"]], [90_000, 100_000])
        self.assertEqual([item["total_paise"] for item in first["invoices"]], [90_000, 100_000])

    def test_bad_billing_cursor_is_reported_as_exception(self):
        repo = MemoryRepo(BillingCandidate(
            id=14, number="SUB-0014", customer_name="Example Shop",
            start_date=date(2026, 1, 31), expiry_date=date(2026, 6, 1),
            next_bill_date=date(2026, 3, 28), frequency="monthly",
            plan_fee_paise=100_000, plan_tax_rate_bps=0,
            lines=[], product_discounts=[], subscription_discount=None,
            payment_terms_days=14,
        ))
        self.assertEqual(preview(repo, date(2026, 4, 1))["exceptions"][0]["subscription_id"], 14)
        self.assertEqual(run(repo, date(2026, 4, 1))["error_count"], 1)
