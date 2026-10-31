from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from gsk.service import preview
from yascn.billing import due_candidates
from yascn.models import Discount, Plan, Product, Subscription, SubscriptionLine, Tax, User, Variant
from yascn.services import transition


AS_OF = date(2026, 10, 31)


class ReadOnlyRepository:
    """Real ORM inputs for preview; deliberately no invoice-write substitute."""
    due_candidates = staticmethod(due_candidates)

    def invoice_exists(self, subscription_id, period_start):
        return False


class BillingHandoffTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user("customer@example.com", "CustomerPass!", full_name="Customer", company_name="Example Shop")
        cls.staff = User.objects.create_user("staff@example.com", "StaffPass!", full_name="Staff", role="staff")
        cls.tax = Tax.objects.create(name="GST", rate_bps=1800)
        cls.product = Product.objects.create(name="Connector", type="service", sale_price_paise=0, tax=cls.tax)
        cls.variant = Variant.objects.create(product=cls.product, name="Odoo", price_delta_paise=56000)
        cls.plan = Plan.objects.create(name="Monthly", frequency="monthly", base_price_paise=100000, tax=cls.tax)

    def setUp(self):
        for target, value in [("yascn.models.timezone.localdate", AS_OF),
                              ("yascn.models.timezone.now", datetime(2026, 10, 31, 6, tzinfo=dt_timezone.utc))]:
            patcher = patch(target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def subscription(self, **overrides):
        values = dict(customer=self.customer, plan=self.plan, status="active", start_date=AS_OF,
                      next_bill_date=AS_OF, expiry_date=date(2027, 10, 31), payment_terms_days=14)
        values.update(overrides)
        sub = Subscription.objects.create(**values)
        SubscriptionLine.objects.create(subscription=sub, product=self.product, variant=self.variant,
            quantity=1, unit_price_paise=56000, tax=self.tax)
        return sub

    def test_exact_candidate_contract_and_preview_without_mutations(self):
        sub = self.subscription()
        candidate, = due_candidates(AS_OF)
        self.assertEqual(candidate.id, sub.pk)
        self.assertEqual(candidate.customer_name, "Example Shop")
        self.assertEqual(candidate.number, sub.number)
        self.assertEqual(candidate.plan_fee_paise, 100000)
        self.assertEqual(candidate.plan_tax_rate_bps, 1800)
        self.assertEqual(candidate.frequency, "monthly")
        self.assertEqual(candidate.payment_terms_days, 14)
        self.assertEqual(candidate.lines[0].description, "Connector — Odoo")
        self.assertEqual(candidate.lines[0].unit_price_paise, 56000)
        self.assertEqual(candidate.lines[0].quantity, 1)
        self.assertEqual(candidate.lines[0].product_id, self.product.pk)
        self.assertEqual(candidate.product_discounts, [])
        self.assertIsNone(candidate.subscription_discount)
        result = preview(ReadOnlyRepository(), AS_OF)
        self.assertEqual(result["due_count"], 1)
        self.assertEqual(result["expected_total_paise"], 184080)
        self.assertEqual(result["items"][0]["period_end"], "2026-11-30")
        sub.refresh_from_db()
        self.assertEqual(sub.next_bill_date, AS_OF)

    def test_only_active_lines_are_billed_and_catalog_prices_are_not_reapplied(self):
        sub = self.subscription()
        SubscriptionLine.objects.create(subscription=sub, product=self.product, quantity=3,
            unit_price_paise=999999, tax=self.tax, active=False)
        Product.objects.filter(pk=self.product.pk).update(sale_price_paise=999999, active=False)
        Variant.objects.filter(pk=self.variant.pk).update(price_delta_paise=1)
        candidate, = due_candidates(AS_OF)
        self.assertEqual(len(candidate.lines), 1)
        self.assertEqual(candidate.lines[0].unit_price_paise, 56000)
        # Deactivating catalog offerings stops new sales, not existing contracts.
        self.assertEqual(preview(ReadOnlyRepository(), AS_OF)["expected_total_paise"], 184080)

    def test_inactive_and_missing_taxes_are_zero_and_customer_name_falls_back(self):
        sub = self.subscription()
        User.objects.filter(pk=self.customer.pk).update(company_name="")
        Tax.objects.filter(pk=self.tax.pk).update(active=False)
        candidate, = due_candidates(AS_OF)
        self.assertEqual(candidate.customer_name, "Customer")
        self.assertEqual(candidate.plan_tax_rate_bps, 0)
        self.assertEqual(candidate.lines[0].tax_rate_bps, 0)
        Plan.objects.filter(pk=self.plan.pk).update(tax=None)
        sub.lines.update(tax=None)
        self.assertEqual(preview(ReadOnlyRepository(), AS_OF)["expected_total_paise"], 156000)

    def test_best_discount_is_evaluated_by_gsk_and_usage_is_not_consumed(self):
        sub = self.subscription()
        product_discount = Discount.objects.create(name="Product saving", kind="fixed", value=6000,
            scope="product", product=self.product, min_quantity=1, min_purchase_paise=50000,
            starts_on=AS_OF, ends_on=AS_OF, usage_limit=2, used_count=1)
        whole = Discount.objects.create(name="Whole saving", kind="percent", value=1000,
            scope="subscription", usage_limit=3)
        sub.subscription_discount = whole
        sub.save()
        candidate, = due_candidates(AS_OF)
        rule, = candidate.product_discounts
        self.assertEqual(rule.product_id, self.product.pk)
        self.assertEqual(rule.used_count, 1)
        self.assertEqual(rule.starts_on, AS_OF)
        self.assertEqual(rule.min_quantity, 1)
        self.assertEqual(candidate.subscription_discount.id, whole.pk)
        result = preview(ReadOnlyRepository(), AS_OF)
        self.assertEqual(result["items"][0]["discount_paise"], 15600)
        self.assertEqual(result["items"][0]["tax_paise"], 25272)
        self.assertEqual(result["expected_total_paise"], 165672)
        whole.refresh_from_db()
        product_discount.refresh_from_db()
        self.assertEqual(whole.used_count, 0)
        self.assertEqual(product_discount.used_count, 1)

    def test_irrelevant_inactive_unassigned_and_expired_discounts_do_not_apply(self):
        self.subscription()
        foreign = Product.objects.create(name="Foreign", type="service", sale_price_paise=1)
        Discount.objects.create(name="Foreign", kind="fixed", value=100000, scope="product", product=foreign)
        Discount.objects.create(name="Inactive", kind="fixed", value=100000, scope="product", product=self.product, active=False)
        Discount.objects.create(name="Unassigned", kind="fixed", value=100000, scope="subscription")
        ended = Discount.objects.create(name="Ended", kind="fixed", value=100000, scope="product",
            product=self.product, ends_on=AS_OF - timedelta(days=1))
        candidate, = due_candidates(AS_OF)
        # Keep dated rules for period-specific evaluation during catch-up.
        self.assertEqual([rule.id for rule in candidate.product_discounts], [ended.pk])
        self.assertEqual(preview(ReadOnlyRepository(), AS_OF)["expected_total_paise"], 184080)

    def test_limited_discount_is_projected_across_real_missed_periods(self):
        sub = self.subscription(start_date=date(2026, 8, 31), next_bill_date=date(2026, 8, 31))
        whole = Discount.objects.create(name="One use", kind="fixed", value=10000, scope="subscription", usage_limit=1)
        sub.subscription_discount = whole
        sub.save()
        result = preview(ReadOnlyRepository(), AS_OF)
        self.assertEqual([item["period_start"] for item in result["items"]], ["2026-08-31", "2026-09-30", "2026-10-31"])
        self.assertEqual([item["discount_paise"] for item in result["items"]], [10000, 0, 0])
        whole.refresh_from_db()
        self.assertEqual(whole.used_count, 0)

    def test_catch_up_ends_at_exclusive_expiry_and_ignores_signup_availability(self):
        self.subscription(start_date=date(2026, 8, 31), next_bill_date=date(2026, 8, 31), expiry_date=date(2026, 10, 15))
        Plan.objects.filter(pk=self.plan.pk).update(available_to=date(2026, 9, 1))
        result = preview(ReadOnlyRepository(), AS_OF)
        self.assertEqual(result["due_count"], 2)
        self.assertEqual(result["items"][-1]["period_end"], "2026-10-15")
        self.assertFalse(result["exceptions"])

    def test_paused_closed_expired_and_future_cycles_are_excluded(self):
        active = self.subscription()
        for state in ["draft", "quotation", "confirmed", "paused", "closed", "expired"]:
            self.subscription(status=state)
        self.subscription(next_bill_date=date(2026, 11, 30))
        self.subscription(start_date=AS_OF - timedelta(days=31), expiry_date=AS_OF)
        self.assertEqual([candidate.id for candidate in due_candidates(AS_OF)], [active.pk])

    def test_mapping_query_count_does_not_grow_with_subscriptions(self):
        self.subscription()
        with self.assertNumQueries(3):
            self.assertEqual(len(due_candidates(AS_OF)), 1)
        for _ in range(12):
            self.subscription()
        with self.assertNumQueries(3):
            self.assertEqual(len(due_candidates(AS_OF)), 13)

    def test_no_due_subscriptions_only_queries_subscriptions(self):
        with self.assertNumQueries(1):
            self.assertEqual(due_candidates(AS_OF), [])

    def test_transition_reloads_state_instead_of_trusting_stale_instance(self):
        sub = self.subscription(status="confirmed")
        Subscription.objects.filter(pk=sub.pk).update(status="closed")
        with self.assertRaises(ValidationError):
            transition(sub, "activate")
        sub.refresh_from_db()
        self.assertEqual(sub.status, "closed")

    def test_draft_with_expired_template_validity_cannot_be_quoted(self):
        sub = self.subscription(status="draft", quote_expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(sub.permitted_actions, ["close"])
        with self.assertRaises(ValidationError):
            transition(sub, "quote")

    @override_settings(ROOT_URLCONF="gsk.urls")
    def test_real_orm_preview_through_shared_route_and_token_authentication(self):
        self.subscription()
        client = APIClient()
        staff_token = Token.objects.create(user=self.staff)
        customer_token = Token.objects.create(user=self.customer)
        with patch("gsk.views.get_repository", return_value=ReadOnlyRepository()):
            self.assertEqual(client.get("/api/billing/preview").status_code, 401)
            client.credentials(HTTP_AUTHORIZATION="Token " + customer_token.key)
            self.assertEqual(client.get("/api/billing/preview").status_code, 403)
            client.credentials(HTTP_AUTHORIZATION="Token " + staff_token.key)
            response = client.get("/api/billing/preview")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["expected_total_paise"], 184080)
            self.assertEqual(response.data["due_count"], 1)
            self.assertEqual(client.get("/api/auth/me").data["id"], self.staff.pk)

    @override_settings(ROOT_URLCONF="gsk.urls")
    def test_seed_to_active_subscription_is_visible_to_billing_via_shared_routes(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.staff).key)
        response = client.post("/api/subscriptions", {
            "customer": self.customer.pk, "plan": self.plan.pk,
            "start_date": str(AS_OF), "expiry_date": "2027-10-31",
            "lines": [{"product_id": self.product.pk, "variant_id": self.variant.pk, "quantity": 1}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        url = f'/api/subscriptions/{response.data["id"]}/transition'
        for action in ["quote", "confirm", "activate"]:
            result = client.post(url, {"action": action}, format="json")
            self.assertEqual(result.status_code, 200, result.data)
        with patch("gsk.views.get_repository", return_value=ReadOnlyRepository()):
            response = client.get("/api/billing/preview")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["expected_total_paise"], 184080)
