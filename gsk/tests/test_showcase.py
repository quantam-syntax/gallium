"""Showcase fixtures and product adoption contract."""

import io
import unittest
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient


@unittest.skipUnless({"yascn", "aliar"}.issubset(settings.INSTALLED_APPS), "Production apps required")
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ShowcaseTests(TestCase):
    def test_seed_is_rerunnable_and_does_not_advance_original_demo_cursor(self):
        from aliar.models import Invoice, Payment
        from yascn.models import Product, Subscription, User

        with patch.dict("os.environ", {"BRIGHTLOOP_DEMO_PASSWORD": "DemoGate!123"}):
            call_command("seed_yascn_demo", stdout=io.StringIO())
            original = Subscription.objects.get(number="SUB-DEMO-0001")
            original_cursor = original.next_bill_date
            call_command("seed_showcase", stdout=io.StringIO())
            first_invoice_count = Invoice.objects.count()
            first_payment_count = Payment.objects.count()
            call_command("seed_showcase", stdout=io.StringIO())

        original.refresh_from_db()
        self.assertEqual(original.next_bill_date, original_cursor)
        self.assertEqual(Subscription.objects.filter(number__startswith="SUB-SHOWCASE-").count(), 300)
        self.assertEqual(Product.objects.filter(name__startswith="Showcase · ").count(), 25)
        self.assertEqual(User.objects.filter(email__startswith="showcase-customer-").count(), 50)
        self.assertEqual(Invoice.objects.count(), first_invoice_count)
        self.assertEqual(Payment.objects.count(), first_payment_count)
        self.assertGreater(first_invoice_count, 300)
        self.assertGreater(first_payment_count, 0)

        admin = User.objects.get(email="admin@brightloop.example")
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get("/api/analytics/products")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["as_of"], timezone.localdate().isoformat())
        trends = {item["name"]: item for item in response.data["products"]}
        self.assertEqual(trends["Showcase · Workspace Core"]["pace"], "fast")
        self.assertEqual(trends["Showcase · Analytics Hub"]["pace"], "slow")
        self.assertEqual(len(trends["Showcase · Workspace Core"]["weekly_counts"]), 9)
        customer = User.objects.get(email="showcase-customer-001@brightloop.example")
        client.force_authenticate(user=customer)
        self.assertEqual(client.get("/api/analytics/products").status_code, 403)
