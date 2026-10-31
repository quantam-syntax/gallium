from datetime import date, datetime, timedelta, timezone as dt_timezone
from io import StringIO
from unittest import skipUnless
from unittest.mock import patch

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from yascn.models import User, Product, Variant, Plan, Subscription, SubscriptionLine
from yascn.services import maintain_subscription

if apps.is_installed("aliar"):
    from aliar.models import Invoice


TODAY = date(2026, 10, 31)


@skipUnless(apps.is_installed("aliar"), "Lifecycle catch-up requires the real ALIAR app")
@override_settings(ROOT_URLCONF="gsk.urls")
class LifecycleTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user("owner@example.com", "OwnerPass!", full_name="Owner")
        cls.other = User.objects.create_user("other@example.com", "OtherPass!", full_name="Other")
        cls.staff = User.objects.create_user("staff@example.com", "StaffPass!", full_name="Staff", role="staff")
        cls.plan = Plan.objects.create(name="Monthly", base_price_paise=100000, frequency="monthly")
        cls.product = Product.objects.create(name="Connector", type="service", sale_price_paise=0, cost_price_paise=123)
        cls.variant = Variant.objects.create(product=cls.product, name="Odoo", price_delta_paise=56000)

    def setUp(self):
        for target, value in [("yascn.models.timezone.localdate", TODAY),
                              ("yascn.models.timezone.now", datetime(2026, 10, 31, 6, tzinfo=dt_timezone.utc))]:
            patcher = patch(target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.login(self.customer)
        self.sub = Subscription.objects.create(customer=self.customer, plan=self.plan, status="active",
            start_date=date(2026, 8, 31), next_bill_date=date(2026, 8, 31), expiry_date=date(2027, 8, 31),
            activated_at=datetime(2026, 8, 31, tzinfo=dt_timezone.utc))
        SubscriptionLine.objects.create(subscription=self.sub, product=self.product, variant=self.variant,
            quantity=1, unit_price_paise=56000)

    def login(self, user):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.get_or_create(user=user)[0].key)

    def action(self, action, expected=200, **data):
        response = self.client.post(f"/api/subscriptions/{self.sub.pk}/transition", {"action": action, **data}, format="json")
        self.assertEqual(response.status_code, expected, response.data)
        self.sub.refresh_from_db()
        return response

    def edit(self, lines, expected=200):
        response = self.client.patch(f"/api/subscriptions/{self.sub.pk}", {"lines": lines}, format="json")
        self.assertEqual(response.status_code, expected, response.data)
        self.sub.refresh_from_db()
        return response

    def test_pause_settles_arrears_and_resume_skips_paused_cycles(self):
        self.action("pause")
        self.assertEqual(self.sub.status, "paused")
        self.assertEqual(Invoice.objects.count(), 3)
        self.assertEqual(self.sub.next_bill_date, date(2026, 11, 30))
        with patch("yascn.services.timezone.localdate", return_value=date(2027, 1, 15)):
            self.action("resume")
        self.assertEqual(self.sub.next_bill_date, date(2027, 1, 31))
        self.assertEqual(Invoice.objects.count(), 3)

    def test_resume_on_exact_boundary_bills_only_resumed_cycle(self):
        self.action("pause")
        with patch("yascn.services.timezone.localdate", return_value=date(2026, 11, 30)):
            self.action("resume")
            self.assertEqual(self.sub.next_bill_date, date(2026, 11, 30))
            self.login(self.staff)
            result = self.client.post("/api/billing/run", {}, format="json")
        self.assertEqual(result.data["created_count"], 1)
        self.assertEqual(Invoice.objects.count(), 4)

    def test_quantity_change_bills_old_terms_then_next_cycle_uses_new_quantity(self):
        self.edit([{"product_id": self.product.pk, "variant_id": self.variant.pk, "quantity": 2}])
        self.assertEqual(list(Invoice.objects.values_list("total_paise", flat=True)), [156000] * 3)
        self.assertEqual(self.sub.lines.get().quantity, 2)
        self.assertEqual(self.sub.next_bill_date, date(2026, 11, 30))
        self.login(self.staff)
        with patch("yascn.services.timezone.localdate", return_value=date(2026, 11, 30)):
            preview = self.client.get("/api/billing/preview")
            self.assertEqual(preview.data["expected_total_paise"], 212000)
            self.assertEqual(self.client.post("/api/billing/run", {}, format="json").data["created_count"], 1)
        self.assertEqual(Invoice.objects.count(), 4)
        self.assertEqual(Invoice.objects.filter(total_paise=212000).count(), 1)

    def test_existing_negotiated_price_survives_catalog_change_and_new_addon_uses_catalog(self):
        self.sub.lines.update(unit_price_paise=50000)
        Product.objects.filter(pk=self.product.pk).update(sale_price_paise=100000)
        addon = Product.objects.create(name="Support", type="service", sale_price_paise=20000)
        self.edit([{"product_id": self.product.pk, "variant_id": self.variant.pk, "quantity": 2},
                   {"product_id": addon.pk, "quantity": 1}])
        self.assertEqual(self.sub.lines.get(product=self.product).unit_price_paise, 50000)
        self.assertEqual(self.sub.lines.get(product=addon).unit_price_paise, 20000)
        self.assertEqual(list(Invoice.objects.values_list("total_paise", flat=True)), [150000] * 3)

    def test_price_tax_and_active_spoofing_and_duplicate_lines_are_rejected(self):
        base = {"product_id": self.product.pk, "quantity": 1}
        for field, value in [("unit_price_paise", 1), ("tax_id", None), ("active", False)]:
            self.edit([{**base, field: value}], expected=400)
        self.edit([base, base], expected=400)
        self.edit([], expected=400)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_catchup_failure_rolls_back_invoices_cursor_and_lines(self):
        from aliar.services import create_for_candidate
        calls = []
        def fail_second(candidate, period, snapshot):
            calls.append(period)
            if len(calls) == 2:
                raise ValueError("simulated finance failure")
            return create_for_candidate(candidate, period, snapshot)
        with patch("aliar.services.create_for_candidate", side_effect=fail_second):
            self.edit([{"product_id": self.product.pk, "quantity": 2}], expected=400)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(self.sub.next_bill_date, date(2026, 8, 31))
        self.assertEqual(self.sub.lines.get().quantity, 1)

    def test_close_settles_due_periods_and_never_reopens(self):
        self.action("close")
        self.assertEqual(self.sub.status, "closed")
        self.assertEqual(Invoice.objects.count(), 3)
        for action in ["resume", "renew", "pause", "close"]:
            self.action(action, expected=400)

    def test_plan_flags_and_ownership_are_enforced(self):
        Plan.objects.filter(pk=self.plan.pk).update(allow_pause=False, allow_renew=False, allow_cancel=False)
        for action in ["pause", "renew", "close"]:
            self.action(action, expected=400)
        self.login(self.other)
        self.action("pause", expected=404)
        self.edit([{"product_id": self.product.pk, "quantity": 2}], expected=404)
        self.assertEqual(self.client.get(f"/api/subscriptions/{self.sub.pk}/addons").status_code, 404)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_customer_cannot_manage_drafts_or_expired_quotes(self):
        self.sub.status = "draft"
        self.sub.activated_at = None
        self.sub.save()
        self.action("close", expected=403)
        self.action("activate", expected=403)
        self.sub.status = "expired"
        self.sub.save()
        self.action("renew", expected=403)

    def test_customer_addon_options_exclude_internal_costs(self):
        response = self.client.get(f"/api/subscriptions/{self.sub.pk}/addons")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertNotIn("cost_price_paise", response.data["results"][0])
        self.assertNotIn("notes", response.data["results"][0])
        self.assertEqual(response.data["results"][0]["variants"][0]["price_delta_paise"], 56000)
        self.assertEqual(self.client.get("/api/products").status_code, 403)

    def test_expiry_maintenance_catches_up_then_expires_and_is_idempotent(self):
        self.sub.expiry_date = date(2026, 10, 15)
        self.sub.save()
        call_command("maintain_subscriptions", stdout=StringIO())
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "expired")
        self.assertEqual(self.sub.next_bill_date, date(2026, 10, 15))
        self.assertEqual(Invoice.objects.count(), 2)
        self.assertEqual(Invoice.objects.order_by("period_start").last().period_end, date(2026, 10, 15))
        call_command("maintain_subscriptions", stdout=StringIO())
        self.assertEqual(Invoice.objects.count(), 2)

    def test_paused_expiry_auto_closes_without_billing_skipped_cycles(self):
        self.action("pause")
        Plan.objects.filter(pk=self.plan.pk).update(auto_close=True)
        with patch("yascn.services.timezone.localdate", return_value=date(2027, 9, 1)):
            maintain_subscription(self.sub.pk)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "closed")
        self.assertEqual(Invoice.objects.count(), 3)

    def test_lapsed_renewal_reanchors_without_billing_the_gap(self):
        self.sub.expiry_date = date(2026, 10, 15)
        self.sub.save()
        call_command("maintain_subscriptions", stdout=StringIO())
        self.action("renew", expiry_date="2026-12-31")
        self.assertEqual(self.sub.status, "active")
        self.assertEqual(self.sub.start_date, TODAY)
        self.assertEqual(self.sub.next_bill_date, TODAY)
        self.assertEqual(Invoice.objects.count(), 2)
        self.login(self.staff)
        self.assertEqual(self.client.post("/api/billing/run", {}, format="json").data["created_count"], 1)
        self.assertEqual(Invoice.objects.filter(period_start=date(2026, 10, 15)).count(), 0)

    def test_early_renewal_preserves_anchor_and_rejects_shortening(self):
        original_start = self.sub.start_date
        self.action("renew", expected=400, expiry_date="2027-08-31")
        self.action("renew", expiry_date="2028-08-31")
        self.assertEqual(self.sub.start_date, original_start)
        self.assertEqual(self.sub.expiry_date, date(2028, 8, 31))
        self.assertEqual(self.sub.next_bill_date, date(2026, 11, 30))

    def test_staff_line_edits_ignore_signup_availability_on_existing_contract(self):
        self.login(self.staff)
        Plan.objects.filter(pk=self.plan.pk).update(available_to=date(2026, 9, 1))
        self.edit([{"product_id": self.product.pk, "quantity": 2, "unit_price_paise": 12345}])
        self.assertEqual(self.sub.lines.get().unit_price_paise, 12345)
        self.assertEqual(Invoice.objects.count(), 3)

    def test_minimum_quantity_rejection_does_not_trigger_billing(self):
        Plan.objects.filter(pk=self.plan.pk).update(minimum_quantity=2)
        self.edit([{"product_id": self.product.pk, "quantity": 1}], expected=400)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_maintenance_rejects_future_dates(self):
        with self.assertRaises(CommandError):
            call_command("maintain_subscriptions", as_of=TODAY + timedelta(days=1), stdout=StringIO())
        self.assertEqual(Invoice.objects.count(), 0)

    def test_stale_cursor_over_cancelled_invoice_is_settled_before_edit(self):
        self.login(self.staff)
        result = self.client.post("/api/billing/run", {}, format="json")
        self.assertEqual(result.data["created_count"], 3)
        invoice = Invoice.objects.order_by("period_start").first()
        self.assertEqual(self.client.post(f"/api/invoices/{invoice.pk}/cancel", {}, format="json").status_code, 200)
        Subscription.objects.filter(pk=self.sub.pk).update(next_bill_date=date(2026, 8, 31))
        self.login(self.customer)
        self.edit([{"product_id": self.product.pk, "quantity": 2}])
        self.assertEqual(self.sub.next_bill_date, date(2026, 11, 30))
        self.assertEqual(Invoice.objects.count(), 3)

    def test_active_expiry_auto_close_settles_partial_final_period(self):
        Plan.objects.filter(pk=self.plan.pk).update(auto_close=True)
        self.sub.expiry_date = date(2026, 10, 15)
        self.sub.save()
        maintain_subscription(self.sub.pk)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "closed")
        self.assertEqual(Invoice.objects.count(), 2)

    def test_paused_renewal_stays_paused_and_default_renewal_uses_frequency(self):
        self.action("pause")
        self.action("renew")
        self.assertEqual(self.sub.status, "paused")
        self.assertEqual(self.sub.expiry_date, date(2027, 9, 30))
        self.assertEqual(Invoice.objects.count(), 3)

    def test_early_renewal_after_partial_final_invoice_continues_at_old_expiry(self):
        self.sub.expiry_date = date(2026, 11, 15)
        self.sub.save()
        self.action("renew", expiry_date="2027-01-15")
        self.assertEqual(self.sub.start_date, date(2026, 11, 15))
        self.assertEqual(self.sub.next_bill_date, date(2026, 11, 15))
        self.assertEqual(Invoice.objects.order_by("period_start").last().period_end, date(2026, 11, 15))
        self.login(self.staff)
        with patch("yascn.services.timezone.localdate", return_value=date(2026, 11, 15)):
            result = self.client.post("/api/billing/run", {}, format="json")
        self.assertEqual(result.data["error_count"], 0)
        self.assertEqual(result.data["created_count"], 1)
        self.assertEqual(Invoice.objects.filter(period_start=date(2026, 11, 15)).get().period_end, date(2026, 12, 15))
