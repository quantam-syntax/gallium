from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError as ModelValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from gsk.billing import BillingPeriod, gross_mrr_paise
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from yascn.models import Discount, Plan, Product, Subscription, SubscriptionLine

from aliar import reporting, services
from aliar.models import Invoice, Payment


class FinanceTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        users = get_user_model()
        self.staff = users.objects.create_user(
            "staff@example.com",
            "FinanceTest!123",
            full_name="Finance Staff",
            role="staff",
        )
        self.customer = users.objects.create_user(
            "a@example.com", "FinanceTest!123", full_name="Customer A"
        )
        self.other = users.objects.create_user(
            "b@example.com", "FinanceTest!123", full_name="Customer B"
        )
        self.plan = Plan.objects.create(
            name="Monthly", base_price_paise=10000, frequency="monthly"
        )
        self.product = Product.objects.create(
            name="Connector", type="service", sale_price_paise=561
        )
        self.subscription = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
            number="SUB-1",
            status="active",
            start_date=self.today - timedelta(days=365),
            expiry_date=self.today + timedelta(days=365),
            payment_terms_days=7,
            next_bill_date=self.today - timedelta(days=30),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    def snapshot(self, period=None, amount=10000, discounts=None):
        period = period or BillingPeriod(self.today - timedelta(days=30), self.today)
        return {
            "period_start": period.start.isoformat(),
            "period_end": period.end.isoformat(),
            "lines": [
                {
                    "description": "Plan fee",
                    "quantity": 1,
                    "unit_price_paise": amount,
                    "amount_paise": amount,
                    "discount_paise": 0,
                    "tax_paise": 0,
                }
            ],
            "subtotal_paise": amount,
            "discount_paise": 0,
            "tax_paise": 0,
            "total_paise": amount,
            "applied_discount_ids": discounts or [],
        }

    def invoice(self, period=None, amount=10000, discounts=None):
        period = period or BillingPeriod(self.today - timedelta(days=30), self.today)
        result = services.create_period_if_missing(
            self.subscription,
            period,
            self.snapshot(period, amount, discounts),
            issued_on=self.today - timedelta(days=20),
        )
        return Invoice.objects.get(pk=result["id"])

    def pay(self, invoice, amount):
        return self.client.post(
            f"/api/invoices/{invoice.pk}/payments",
            {
                "method": "bank",
                "amount_paise": amount,
                "paid_on": self.today.isoformat(),
                "note": "test",
            },
            format="json",
        )

    def test_partial_payments_and_settlement(self):
        invoice = self.invoice()
        self.assertEqual(self.pay(invoice, 1).status_code, 400)
        self.assertEqual(
            self.client.post(f"/api/invoices/{invoice.pk}/confirm").status_code, 200
        )
        for amount, expected in ((2000, 8000), (3000, 5000), (5000, 0)):
            response = self.pay(invoice, amount)
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data["balance_paise"], expected)
            invoice.refresh_from_db()
            self.assertEqual(invoice.status, "paid" if expected == 0 else "confirmed")
        self.assertEqual(self.pay(invoice, 1).status_code, 400)

    def test_invalid_payments_do_not_change_balance(self):
        invoice = self.invoice()
        services.confirm(invoice.pk)
        for amount in (0, -1, 10001, 1.5, "invalid"):
            self.assertEqual(self.pay(invoice, amount).status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)

    def test_customer_ownership_all_routes_and_mutations(self):
        invoice = self.invoice()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/invoices").data["count"], 0)
        for suffix in ("", "/payments"):
            self.assertEqual(
                self.client.get(f"/api/invoices/{invoice.pk}{suffix}").status_code, 404
            )
        self.client.force_authenticate(self.customer)
        self.assertEqual(
            self.client.get(f"/api/invoices/{invoice.pk}").status_code, 200
        )
        for action in ("confirm", "cancel", "send", "reissue", "payments"):
            self.assertEqual(
                self.client.post(
                    f"/api/invoices/{invoice.pk}/{action}", {}, format="json"
                ).status_code,
                403,
            )
        self.assertEqual(self.client.get("/api/dashboard").status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/invoices").status_code, 401)

    def test_overdue_balance_and_paid_badges(self):
        invoice = self.invoice()
        services.confirm(invoice.pk)
        self.pay(invoice, 2500)
        detail = self.client.get(f"/api/invoices/{invoice.pk}").data
        self.assertTrue(detail["is_overdue"])
        self.assertTrue(detail["is_partially_paid"])
        self.assertEqual(detail["balance_paise"], 7500)
        self.assertEqual(self.client.get("/api/invoices?overdue=true").data["count"], 1)
        self.pay(invoice, 7500)
        self.assertFalse(
            self.client.get(f"/api/invoices/{invoice.pk}").data["is_overdue"]
        )

    def test_cancel_reissue_and_automatic_reruns(self):
        invoice = self.invoice()
        services.cancel(invoice.pk)
        cancelled = self.client.get(f"/api/invoices/{invoice.pk}").data
        self.assertEqual(cancelled["balance_paise"], 0)
        self.assertFalse(cancelled["is_overdue"])
        self.assertEqual(
            self.client.get("/api/invoices?outstanding=true").data["count"], 0
        )
        invoice.refresh_from_db()
        self.assertEqual(services.balances(invoice)["balance_paise"], 0)
        cancelled_dashboard = self.client.get("/api/dashboard").data
        self.assertEqual(cancelled_dashboard["outstanding_paise"], 0)
        self.assertEqual(cancelled_dashboard["invoiced_paise"], 0)
        self.assertEqual(cancelled_dashboard["overdue_count"], 0)
        period = BillingPeriod(invoice.period_start, invoice.period_end)
        self.assertIsNone(
            services.create_period_if_missing(
                self.subscription, period, invoice.snapshot
            )
        )
        response = self.client.post(f"/api/invoices/{invoice.pk}/reissue")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["revision"], 2)
        self.assertEqual(response.data["snapshot"], invoice.snapshot)
        self.assertEqual(
            self.client.post(f"/api/invoices/{invoice.pk}/reissue").status_code, 400
        )
        self.assertEqual(Invoice.objects.count(), 2)
        self.assertEqual(reporting.dashboard()["invoiced_paise"], 10000)

    def test_cancel_paid_or_partial_rejected(self):
        invoice = self.invoice()
        services.confirm(invoice.pk)
        self.pay(invoice, 100)
        self.assertEqual(
            self.client.post(f"/api/invoices/{invoice.pk}/cancel").status_code, 400
        )
        self.pay(invoice, 9900)
        self.assertEqual(
            self.client.post(f"/api/invoices/{invoice.pk}/cancel").status_code, 400
        )

    def test_database_unique_period_and_revision(self):
        invoice = self.invoice()
        fields = {
            field.attname: getattr(invoice, field.attname)
            for field in Invoice._meta.concrete_fields
            if field.name not in ("id", "number")
        }
        for revision in (1, 2):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Invoice.objects.create(**{**fields, "revision": revision})

    def test_snapshot_and_payment_immutability(self):
        invoice = self.invoice()
        invoice.snapshot["lines"] = []
        with self.assertRaises(ModelValidationError):
            invoice.save()
        with self.assertRaises(ModelValidationError):
            Invoice.objects.filter(pk=invoice.pk).update(total_paise=1)
        with self.assertRaises(ModelValidationError):
            invoice.delete()
        services.confirm(invoice.pk)
        self.pay(invoice, 1)
        with self.assertRaises(ModelValidationError):
            Payment.objects.all().delete()

    def test_creation_atomically_consumes_discount_and_advances_cursor(self):
        discount = Discount.objects.create(
            name="Once", kind="fixed", value=0, scope="subscription", usage_limit=1
        )
        invoice = self.invoice(discounts=[discount.pk])
        self.subscription.refresh_from_db()
        discount.refresh_from_db()
        self.assertEqual(self.subscription.next_bill_date, invoice.period_end)
        self.assertEqual(discount.used_count, 1)
        next_period = BillingPeriod(self.today, self.today + timedelta(days=30))
        with self.assertRaises(ValidationError) as error:
            self.invoice(next_period, discounts=[discount.pk])
        self.assertIn("discount", str(error.exception).lower())
        self.assertEqual(Invoice.objects.count(), 1)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.next_bill_date, self.today)

    def test_invalid_snapshot_rolls_back(self):
        period = BillingPeriod(self.today, self.today + timedelta(days=30))
        snapshot = self.snapshot(period)
        snapshot["lines"][0]["amount_paise"] = 1
        with self.assertRaises(ValidationError):
            services.create_period_if_missing(self.subscription, period, snapshot)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_inconsistent_line_prices_are_rejected(self):
        period = BillingPeriod(self.today, self.today + timedelta(days=1))
        snapshot = self.snapshot(period)
        snapshot["lines"][0]["unit_price_paise"] = 1
        with self.assertRaises(ValidationError):
            services.create_period_if_missing(self.subscription, period, snapshot)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_creation_rechecks_live_subscription_state(self):
        period = BillingPeriod(self.today, self.today + timedelta(days=1))
        for state in ("paused", "expired", "closed", "draft"):
            Subscription.objects.filter(pk=self.subscription.pk).update(status=state)
            with self.assertRaises(ValidationError):
                services.create_period_if_missing(
                    self.subscription, period, self.snapshot(period)
                )
        self.assertEqual(Invoice.objects.count(), 0)

    def test_future_and_outside_subscription_period_rejected(self):
        for period in (
            BillingPeriod(
                self.today + timedelta(days=1), self.today + timedelta(days=2)
            ),
            BillingPeriod(
                self.subscription.start_date - timedelta(days=1),
                self.subscription.start_date,
            ),
            BillingPeriod(
                self.today, self.subscription.expiry_date + timedelta(days=1)
            ),
        ):
            with self.assertRaises(ValidationError):
                services.create_period_if_missing(
                    self.subscription, period, self.snapshot(period)
                )
        self.assertEqual(Invoice.objects.count(), 0)

    @patch("aliar.services.send_mail", side_effect=OSError("test backend unavailable"))
    def test_delivery_failure_does_not_mark_invoice_sent(self, _send):
        invoice = self.invoice()
        services.confirm(invoice.pk)
        response = self.client.post(f"/api/invoices/{invoice.pk}/send")
        self.assertEqual(response.status_code, 503)
        invoice.refresh_from_db()
        self.assertIsNone(invoice.sent_at)
        self.assertEqual(invoice.status, "confirmed")

    def test_send_and_action_validation(self):
        invoice = self.invoice()
        self.assertEqual(
            self.client.post(f"/api/invoices/{invoice.pk}/send").status_code, 400
        )
        services.confirm(invoice.pk)
        self.assertEqual(
            self.client.post(f"/api/invoices/{invoice.pk}/send").status_code, 200
        )
        invoice.refresh_from_db()
        self.assertIsNotNone(invoice.sent_at)
        self.assertEqual(mail.outbox[0].to, [self.customer.email])
        self.assertEqual(
            self.client.post(f"/api/invoices/{invoice.pk}/confirm").status_code, 400
        )

    def test_zero_invoice_settled_on_confirmation(self):
        invoice = self.invoice(amount=0)
        self.assertEqual(services.confirm(invoice.pk).status, "paid")

    def test_dashboard_date_filters_and_no_join_multiplication(self):
        invoice = self.invoice()
        services.confirm(invoice.pk)
        self.pay(invoice, 2000)
        self.pay(invoice, 3000)
        expected = {
            "active_count": 1,
            "gross_mrr_paise": 10000,
            "invoiced_paise": 10000,
            "collected_paise": 5000,
            "outstanding_paise": 5000,
            "overdue_count": 1,
        }
        self.assertEqual(self.client.get("/api/dashboard").data, expected)
        filtered = self.client.get(
            f"/api/dashboard?from={self.today}&to={self.today}"
        ).data
        self.assertEqual(filtered, {**expected, "invoiced_paise": 0})
        for query in ("from=invalid", f"from={self.today}&to=2000-01-01"):
            self.assertEqual(
                self.client.get(f"/api/dashboard?{query}").status_code, 400
            )
        self.assertIn("from", self.client.get("/api/dashboard?from=invalid").data)

    def test_mrr_matches_shared_calculator_and_active_lines(self):
        SubscriptionLine.objects.create(
            subscription=self.subscription,
            product=self.product,
            quantity=2,
            unit_price_paise=561,
        )
        SubscriptionLine.objects.create(
            subscription=self.subscription,
            product=self.product,
            quantity=1,
            unit_price_paise=99999,
            active=False,
        )
        from gsk.billing import BillableLine

        for frequency in ("daily", "weekly", "monthly", "yearly"):
            self.plan.frequency = frequency
            self.plan.save()
            expected = gross_mrr_paise(
                plan_fee_paise=10000,
                lines=[BillableLine("addon", 2, 561)],
                frequency=frequency,
            )
            self.assertEqual(reporting.active_metrics()["gross_mrr_paise"], expected)
        self.subscription.status = "paused"
        self.subscription.save()
        self.assertEqual(
            reporting.active_metrics(), {"active_count": 0, "gross_mrr_paise": 0}
        )

    def test_empty_dashboard(self):
        self.assertEqual(reporting.dashboard()["outstanding_paise"], 0)
        self.assertEqual(reporting.dashboard()["collected_paise"], 0)

    def test_mrr_rounds_each_subscription_before_summing(self):
        self.plan.base_price_paise = 6
        self.plan.frequency = "yearly"
        self.plan.save()
        Subscription.objects.create(
            customer=self.other,
            plan=self.plan,
            status="active",
            start_date=self.subscription.start_date,
            expiry_date=self.subscription.expiry_date,
            next_bill_date=self.today,
        )
        self.assertEqual(
            reporting.active_metrics(), {"active_count": 2, "gross_mrr_paise": 2}
        )

    def test_invoice_generic_writes_are_not_exposed(self):
        invoice = self.invoice()
        for method in (self.client.patch, self.client.put, self.client.delete):
            self.assertEqual(
                method(f"/api/invoices/{invoice.pk}", {}, format="json").status_code,
                405,
            )
        self.assertEqual(
            self.client.post("/api/invoices", {}, format="json").status_code, 405
        )

    def test_gsk_preview_run_saved_totals_and_second_run(self):
        from gsk.service import BillingCandidate, preview, run

        candidate = BillingCandidate(
            id=self.subscription.pk,
            number=self.subscription.number,
            customer_name="Customer A",
            start_date=self.today,
            expiry_date=self.today + timedelta(days=60),
            next_bill_date=self.today,
            frequency="monthly",
            plan_fee_paise=10000,
            plan_tax_rate_bps=1800,
            lines=[],
            product_discounts=[],
            subscription_discount=None,
            payment_terms_days=7,
        )

        class Repository:
            def due_candidates(repo, as_of):
                return [candidate]

            def invoice_exists(repo, subscription_id, period_start):
                return Invoice.objects.filter(
                    subscription_id=subscription_id, period_start=period_start
                ).exists()

            def create_period_if_missing(repo, candidate, period, snapshot):
                return services.create_for_candidate(candidate, period, snapshot)

        repo = Repository()
        before = preview(repo, self.today)
        result = run(repo, self.today)
        self.assertEqual(result["created_count"], 1, result)
        self.assertEqual(
            Invoice.objects.get().total_paise, before["expected_total_paise"]
        )
        self.assertEqual(run(repo, self.today)["created_count"], 0)
        self.assertEqual(preview(repo, self.today)["due_count"], 0)

    def test_candidate_adapter_reports_finance_validation_as_value_error(self):
        period = BillingPeriod(self.today, self.today + timedelta(days=1))
        with self.assertRaises(ValueError):
            services.create_for_candidate(
                SimpleNamespace(id=self.subscription.pk), period, {}
            )

    def test_repeatable_demo_seed_keeps_source_and_cursor(self):
        source = self.invoice()
        self.subscription.refresh_from_db()
        cursor = self.subscription.next_bill_date
        for _ in range(2):
            call_command(
                "seed_aliar",
                source_invoice=source.pk,
                staff=self.staff.pk,
                records=10,
                stdout=StringIO(),
            )
        self.assertEqual(Invoice.objects.count(), 12)
        fixture = Invoice.objects.get(number=f"INV-SEED-{source.pk}-0")
        self.assertEqual(fixture.payments.count(), 2)
        self.assertEqual(
            services.balances(fixture)["balance_paise"], source.total_paise // 2
        )
        self.assertLess(fixture.due_on, self.today)
        source.refresh_from_db()
        self.assertEqual(source.status, "draft")
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.next_bill_date, cursor)

    def test_pagination_and_query_budget(self):
        source = self.invoice()
        rows = []
        for offset in range(1000):
            start = self.today - timedelta(days=offset + 100)
            rows.append(
                Invoice(
                    subscription=self.subscription,
                    customer=self.customer,
                    period_start=start,
                    period_end=start + timedelta(days=1),
                    due_on=self.today,
                    subtotal_paise=10000,
                    total_paise=10000,
                    snapshot=source.snapshot,
                )
            )
        Invoice.objects.bulk_create(rows)
        with self.assertNumQueries(2):
            response = self.client.get("/api/invoices")
        self.assertEqual(response.data["count"], 1001)
        self.assertEqual(len(response.data["results"]), 25)
        with self.assertNumQueries(4):
            self.assertEqual(
                self.client.get("/api/dashboard").data["invoiced_paise"], 10010000
            )
