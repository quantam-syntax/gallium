"""HTTP contract checks using a fake repository, independent of teammate apps."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from gsk.billing import BillableLine
from gsk.service import BillingCandidate
from gsk.tests.test_billing import MemoryRepo


def make_repo():
    return MemoryRepo(BillingCandidate(
        id=12,
        number="SUB-0012",
        customer_name="Example Shop",
        start_date=date(2026, 10, 31),
        expiry_date=date(2026, 12, 31),
        next_bill_date=date(2026, 10, 31),
        frequency="monthly",
        plan_fee_paise=100_000,
        plan_tax_rate_bps=1800,
        lines=[BillableLine("Odoo", 1, 56_000, 1800, product_id=4)],
        product_discounts=[],
        subscription_discount=None,
        payment_terms_days=14,
    ))


class BillingApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.today_patch = patch("gsk.views.timezone.localdate", return_value=date(2026, 10, 31))
        self.today_patch.start()
        self.addCleanup(self.today_patch.stop)

    def authenticate(self, role):
        self.client.force_authenticate(user=SimpleNamespace(role=role, is_authenticated=True))

    def test_unauthenticated_requests_are_rejected(self):
        self.assertEqual(self.client.get("/api/billing/preview").status_code, 401)
        self.assertEqual(self.client.post("/api/billing/run", {}, format="json").status_code, 401)

    def test_customer_cannot_preview_or_run_billing(self):
        self.authenticate("customer")
        self.assertEqual(self.client.get("/api/billing/preview").status_code, 403)
        self.assertEqual(self.client.post("/api/billing/run", {}, format="json").status_code, 403)

    def test_invalid_or_future_date_is_rejected(self):
        self.authenticate("staff")
        self.assertEqual(self.client.get("/api/billing/preview?as_of=not-a-date").status_code, 400)
        self.assertEqual(self.client.post("/api/billing/run", {"as_of": "2026-11-01"}, format="json").status_code, 400)

    def test_missing_teammate_adapter_returns_clear_unavailable_response(self):
        self.authenticate("staff")
        response = self.client.get("/api/billing/preview")
        self.assertEqual(response.status_code, 503)
        self.assertIn("handoffs", response.data["detail"])

    @patch("gsk.views.get_repository")
    def test_preview_and_two_runs_obey_response_contract(self, get_repository):
        repo = make_repo()
        get_repository.return_value = repo
        self.authenticate("admin")

        preview_response = self.client.get("/api/billing/preview")
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response.data["as_of"], "2026-10-31")
        self.assertEqual(preview_response.data["due_count"], 1)
        self.assertEqual(preview_response.data["expected_total_paise"], 184_080)
        self.assertEqual(preview_response.data["items"][0]["period_end"], "2026-11-30")
        self.assertEqual(preview_response.data["exceptions"], [])

        first = self.client.post("/api/billing/run", {}, format="json")
        second = self.client.post("/api/billing/run", {}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["created_count"], 1)
        self.assertEqual(first.data["invoices"][0]["total_paise"], preview_response.data["expected_total_paise"])
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["created_count"], 0)
        self.assertEqual(len(repo.invoices), 1)
