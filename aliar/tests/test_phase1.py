"""Phase 1 gate with real custom users, tokens, subscriptions and migrations.

GSK's pending repository is replaced only within the integration test. Pricing,
billing orchestration, invoice persistence and all HTTP views are real code.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from yascn.billing import due_candidates
from yascn.models import Discount, Subscription, User

from aliar.models import Invoice
from aliar.services import create_for_candidate

PASSWORD = "FinanceGate!123"


class ContractRepository:
    """Test-only ORM adapter showing GSK the exact finance handoff."""

    due_candidates = staticmethod(due_candidates)

    def invoice_exists(self, subscription_id, period_start):
        return Invoice.objects.filter(
            subscription_id=subscription_id, period_start=period_start
        ).exists()

    def create_period_if_missing(self, candidate, period, snapshot):
        return create_for_candidate(candidate, period, snapshot)


class PhaseOneGateTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.admin = User.objects.create_user(
            "admin@gate.example", PASSWORD, full_name="Admin", role="admin"
        )
        self.staff = User.objects.create_user(
            "staff@gate.example", PASSWORD, full_name="Staff", role="staff"
        )
        self.customer = User.objects.create_user(
            "customer@gate.example", PASSWORD, full_name="Example Shop"
        )
        self.other = User.objects.create_user(
            "other@gate.example", PASSWORD, full_name="Other Shop"
        )
        self.client = APIClient()

    def login(self, user):
        self.client.credentials()
        response = self.client.post(
            "/api/auth/login",
            {"email": user.email, "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")

    def post(self, route, data=None, expected=201):
        response = self.client.post(route, data or {}, format="json")
        self.assertEqual(response.status_code, expected, response.data)
        return response.data

    def active_subscription(self):
        self.login(self.admin)
        tax = self.post("/api/taxes", {"name": "GST", "rate_bps": 1800})
        product = self.post(
            "/api/products",
            {
                "name": "Integration",
                "type": "service",
                "sale_price_paise": 0,
                "tax_id": tax["id"],
                "variants": [{"name": "Odoo", "price_delta_paise": 56000}],
            },
        )
        plan = self.post(
            "/api/plans",
            {
                "name": "Monthly",
                "base_price_paise": 100000,
                "frequency": "monthly",
                "tax_id": tax["id"],
            },
        )
        template = self.post(
            "/api/templates",
            {
                "name": "Monthly + Odoo",
                "plan_id": plan["id"],
                "valid_days": 14,
                "lines": [
                    {
                        "product_id": product["id"],
                        "variant_id": product["variants"][0]["id"],
                        "quantity": 1,
                    }
                ],
            },
        )
        self.login(self.staff)
        subscription = self.post(
            "/api/subscriptions",
            {
                "customer": self.customer.pk,
                "template_id": template["id"],
                "start_date": str(self.today),
                "expiry_date": str(self.today + timedelta(days=365)),
                "payment_terms_days": 7,
            },
        )
        for action in ("quote", "confirm", "activate"):
            subscription = self.post(
                f"/api/subscriptions/{subscription['id']}/transition",
                {"action": action},
                expected=200,
            )
        self.assertEqual(subscription["status"], "active")
        self.assertEqual(subscription["lines"][0]["unit_price_paise"], 56000)
        return subscription

    @patch("gsk.views.get_repository", return_value=ContractRepository())
    def test_real_login_to_billing_partial_payments_dashboard_and_customer_portal(
        self, _repository
    ):
        subscription = self.active_subscription()
        preview = self.client.get("/api/billing/preview")
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["expected_total_paise"], 184080)
        first = self.post("/api/billing/run", expected=200)
        self.assertEqual(first["created_count"], 1)
        self.assertEqual(first["error_count"], 0)
        pk = first["invoices"][0]["id"]
        invoice = self.client.get(f"/api/invoices/{pk}").data
        self.assertEqual(invoice["total_paise"], preview.data["expected_total_paise"])
        self.assertEqual(invoice["snapshot"]["lines"][1]["unit_price_paise"], 56000)
        self.post(f"/api/invoices/{pk}/confirm", expected=200)
        for amount, balance in ((50000, 134080), (30000, 104080)):
            result = self.post(
                f"/api/invoices/{pk}/payments",
                {"method": "bank", "amount_paise": amount, "paid_on": str(self.today)},
            )
            self.assertEqual(result["balance_paise"], balance)
        expected = {
            "active_count": 1,
            "gross_mrr_paise": 156000,
            "invoiced_paise": 184080,
            "collected_paise": 80000,
            "outstanding_paise": 104080,
            "overdue_count": 0,
        }
        self.assertEqual(self.client.get("/api/dashboard").data, expected)
        with patch(
            "django.utils.timezone.localdate",
            return_value=self.today + timedelta(days=8),
        ):
            self.assertTrue(self.client.get(f"/api/invoices/{pk}").data["is_overdue"])
            self.assertEqual(
                self.client.get("/api/dashboard").data, {**expected, "overdue_count": 1}
            )
        self.assertEqual(
            self.post("/api/billing/run", expected=200)["created_count"], 0
        )
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertGreater(
            Subscription.objects.get(pk=subscription["id"]).next_bill_date, self.today
        )

        self.login(self.customer)
        self.assertEqual(self.client.get("/api/invoices").data["count"], 1)
        own = self.client.get(f"/api/invoices/{pk}").data
        self.assertEqual(own["balance_paise"], 104080)
        self.assertEqual(own["customer_name"], "Example Shop")
        self.assertEqual(
            self.client.get(f"/api/invoices/{pk}/payments").data["count"], 2
        )
        self.assertEqual(
            self.client.post(
                f"/api/invoices/{pk}/payments", {}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/dashboard").status_code, 403)

        self.login(self.other)
        self.assertEqual(self.client.get("/api/invoices").data["count"], 0)
        self.assertEqual(self.client.get(f"/api/invoices/{pk}").status_code, 404)
        self.assertEqual(
            self.client.get(f"/api/invoices/{pk}/payments").status_code, 404
        )

        self.login(self.staff)
        self.post(
            f"/api/invoices/{pk}/payments",
            {"method": "bank", "amount_paise": 104080, "paid_on": str(self.today)},
        )
        settled = self.client.get(f"/api/invoices/{pk}").data
        self.assertEqual(settled["status"], "paid")
        self.assertEqual(settled["balance_paise"], 0)
        self.assertEqual(
            self.client.get("/api/dashboard").data["collected_paise"], 184080
        )

    def test_inactive_account_token_rejected(self):
        self.login(self.staff)
        User.objects.filter(pk=self.staff.pk).update(is_active=False)
        self.assertEqual(self.client.get("/api/invoices").status_code, 401)
        self.assertEqual(self.client.get("/api/dashboard").status_code, 401)

    @patch("gsk.views.get_repository", return_value=ContractRepository())
    def test_catchup_to_exclusive_expiry_consumes_limited_discount_once(
        self, _repository
    ):
        data = self.active_subscription()
        sub = Subscription.objects.get(pk=data["id"])
        sub.plan.frequency = "daily"
        sub.plan.save(update_fields=["frequency"])
        discount = Discount.objects.create(
            name="One use",
            kind="fixed",
            value=10000,
            scope="subscription",
            usage_limit=1,
        )
        sub.start_date = self.today - timedelta(days=2)
        sub.next_bill_date = sub.start_date
        sub.expiry_date = self.today
        sub.subscription_discount = discount
        sub.save()
        before = self.client.get("/api/billing/preview")
        self.assertEqual(before.status_code, 200, before.data)
        self.assertEqual(before.data["due_count"], 2)
        self.assertEqual(before.data["expected_total_paise"], 356360)
        result = self.post("/api/billing/run", expected=200)
        self.assertEqual(result["created_count"], 2, result)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(
            sum(invoice["total_paise"] for invoice in result["invoices"]),
            before.data["expected_total_paise"],
        )
        discount.refresh_from_db()
        sub.refresh_from_db()
        self.assertEqual(discount.used_count, 1)
        self.assertEqual(sub.next_bill_date, sub.expiry_date)
        self.assertEqual(
            self.post("/api/billing/run", expected=200)["created_count"], 0
        )
