"""Unpatched production URL and repository smoke test for the demo path."""

import io
import unittest
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient


@unittest.skipUnless(
    {"yascn", "aliar"}.issubset(settings.INSTALLED_APPS),
    "Production teammate apps are not installed in isolated GSK settings",
)
@override_settings(ROOT_URLCONF="gsk.urls")
class ProductionBillingIntegrationTests(TestCase):
    def test_seeded_customer_to_invoice_payment_dashboard_and_second_run(self):
        from yascn.models import User

        password = "DemoGate!123"
        with patch.dict("os.environ", {"BRIGHTLOOP_DEMO_PASSWORD": password}):
            call_command("seed_yascn_demo", stdout=io.StringIO())

        client = APIClient()
        login = client.post(
            "/api/auth/login",
            {"email": "admin@brightloop.example", "password": password},
            format="json",
        )
        self.assertEqual(login.status_code, 200, login.data)
        client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")

        subscriptions = client.get("/api/subscriptions")
        self.assertEqual(subscriptions.status_code, 200, subscriptions.data)
        self.assertEqual(subscriptions.data["count"], 1)
        self.assertEqual(subscriptions.data["results"][0]["status"], "active")
        self.assertEqual(subscriptions.data["results"][0]["lines"][0]["unit_price_paise"], 56000)

        preview = client.get("/api/billing/preview")
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["due_count"], 1)
        self.assertEqual(preview.data["expected_total_paise"], 184080)
        self.assertEqual(preview.data["exceptions"], [])

        first = client.post("/api/billing/run", {}, format="json")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["created_count"], 1)
        self.assertEqual(first.data["created_total_paise"], preview.data["expected_total_paise"])
        self.assertEqual(first.data["error_count"], 0)
        invoice_id = first.data["invoices"][0]["id"]
        detail = client.get(f"/api/invoices/{invoice_id}")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data["total_paise"], preview.data["expected_total_paise"])
        self.assertEqual(detail.data["snapshot"]["lines"][1]["unit_price_paise"], 56000)

        confirm = client.post(f"/api/invoices/{invoice_id}/confirm", {}, format="json")
        self.assertEqual(confirm.status_code, 200, confirm.data)
        payment = client.post(
            f"/api/invoices/{invoice_id}/payments",
            {"method": "bank", "amount_paise": 50000, "paid_on": str(timezone.localdate())},
            format="json",
        )
        self.assertEqual(payment.status_code, 201, payment.data)
        self.assertEqual(payment.data["balance_paise"], 134080)
        dashboard = client.get("/api/dashboard")
        self.assertEqual(dashboard.status_code, 200, dashboard.data)
        self.assertEqual(dashboard.data["active_count"], 1)
        self.assertEqual(dashboard.data["gross_mrr_paise"], 156000)
        self.assertEqual(dashboard.data["collected_paise"], 50000)
        self.assertEqual(dashboard.data["outstanding_paise"], 134080)

        self.assertEqual(client.get("/api/billing/preview").data["due_count"], 0)
        second = client.post("/api/billing/run", {}, format="json")
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data["created_count"], 0)
        self.assertEqual(second.data["created_total_paise"], 0)

        customer = User.objects.get(email="customer@brightloop.example")
        client.force_authenticate(user=customer)
        self.assertEqual(client.get("/api/invoices").data["count"], 1)
        self.assertEqual(client.get("/api/billing/preview").status_code, 403)
        self.assertEqual(client.post(f"/api/invoices/{invoice_id}/payments", {}, format="json").status_code, 403)
