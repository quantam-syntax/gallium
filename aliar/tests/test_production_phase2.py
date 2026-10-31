"""Finance actions through the unpatched production routing and billing bridge."""

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from aliar.models import Invoice


@override_settings(ROOT_URLCONF="gsk.urls")
class ProductionFinanceFlowTests(TestCase):
    def test_cancelled_run_requires_reissue_and_reports_current_balance(self):
        password = "FinanceGate!123"
        with patch.dict("os.environ", {"BRIGHTLOOP_DEMO_PASSWORD": password}):
            call_command("seed_yascn_demo", stdout=StringIO())

        client = APIClient()
        login = client.post(
            "/api/auth/login",
            {"email": "admin@brightloop.example", "password": password},
            format="json",
        )
        self.assertEqual(login.status_code, 200, login.data)
        client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")

        preview = client.get("/api/billing/preview")
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["expected_total_paise"], 184080)
        run = client.post("/api/billing/run", {}, format="json")
        self.assertEqual(run.status_code, 200, run.data)
        self.assertEqual(run.data["created_count"], 1)
        first_id = run.data["invoices"][0]["id"]
        original_snapshot = Invoice.objects.get(pk=first_id).snapshot

        cancelled = client.post(f"/api/invoices/{first_id}/cancel", {}, format="json")
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        self.assertEqual(cancelled.data["balance_paise"], 0)
        empty = client.get("/api/dashboard")
        self.assertEqual(empty.status_code, 200, empty.data)
        self.assertEqual(empty.data["invoiced_paise"], 0)
        self.assertEqual(empty.data["outstanding_paise"], 0)
        second_run = client.post("/api/billing/run", {}, format="json")
        self.assertEqual(second_run.status_code, 200, second_run.data)
        self.assertEqual(second_run.data["created_count"], 0)
        self.assertEqual(Invoice.objects.count(), 1)

        reissue = client.post(f"/api/invoices/{first_id}/reissue", {}, format="json")
        self.assertEqual(reissue.status_code, 201, reissue.data)
        self.assertEqual(reissue.data["revision"], 2)
        self.assertEqual(reissue.data["total_paise"], 184080)
        self.assertEqual(reissue.data["snapshot"], original_snapshot)
        current_id = reissue.data["id"]
        self.assertEqual(
            client.post(f"/api/invoices/{current_id}/confirm").status_code, 200
        )
        for amount, remaining in ((50000, 134080), (30000, 104080)):
            payment = client.post(
                f"/api/invoices/{current_id}/payments",
                {
                    "method": "bank",
                    "amount_paise": amount,
                    "paid_on": str(timezone.localdate()),
                },
                format="json",
            )
            self.assertEqual(payment.status_code, 201, payment.data)
            self.assertEqual(payment.data["balance_paise"], remaining)
        dashboard = client.get("/api/dashboard")
        self.assertEqual(dashboard.status_code, 200, dashboard.data)
        self.assertEqual(dashboard.data["invoiced_paise"], 184080)
        self.assertEqual(dashboard.data["collected_paise"], 80000)
        self.assertEqual(dashboard.data["outstanding_paise"], 104080)
        self.assertEqual(dashboard.data["overdue_count"], 0)

        tomorrow = timezone.localdate() + timedelta(days=1)
        filtered = client.get(f"/api/dashboard?from={tomorrow}&to={tomorrow}")
        self.assertEqual(filtered.status_code, 200, filtered.data)
        self.assertEqual(filtered.data["invoiced_paise"], 0)
        self.assertEqual(filtered.data["collected_paise"], 0)
        self.assertEqual(filtered.data["outstanding_paise"], 104080)
        with patch(
            "django.utils.timezone.localdate",
            return_value=tomorrow + timedelta(days=14),
        ):
            detail = client.get(f"/api/invoices/{current_id}")
            self.assertTrue(detail.data["is_overdue"])
            self.assertEqual(client.get("/api/invoices?overdue=true").data["count"], 1)
            self.assertEqual(client.get("/api/dashboard").data["overdue_count"], 1)

        customer = client.post(
            "/api/auth/login",
            {"email": "customer@brightloop.example", "password": password},
            format="json",
        )
        self.assertEqual(customer.status_code, 200, customer.data)
        client.credentials(HTTP_AUTHORIZATION=f"Token {customer.data['token']}")
        self.assertEqual(client.get("/api/invoices").data["count"], 2)
        self.assertEqual(
            client.get(f"/api/invoices/{current_id}").data["balance_paise"], 104080
        )
        self.assertEqual(client.get("/api/dashboard").status_code, 403)
        self.assertEqual(
            client.post(
                f"/api/invoices/{current_id}/payments", {}, format="json"
            ).status_code,
            403,
        )
