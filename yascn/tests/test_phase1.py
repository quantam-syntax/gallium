from datetime import datetime, time, timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from gsk.billing import BillableLine, BillingPeriod, calculate_invoice
from yascn.models import User, Product, Variant, Plan, Subscription, SubscriptionLine, Discount, Tax
from yascn.services import due_subscriptions


PASSWORD = "DemoPass!123"


class PhaseOneAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin@example.com", PASSWORD, full_name="Admin")
        cls.staff = User.objects.create_user("staff@example.com", PASSWORD, full_name="Staff", role="staff")
        cls.customer = User.objects.create_user("customer@example.com", PASSWORD, full_name="Customer", company_name="Example Shop")
        cls.other = User.objects.create_user("other@example.com", PASSWORD, full_name="Other")
        cls.tax = Tax.objects.create(name="GST", rate_bps=1800)
        cls.product = Product.objects.create(name="Integration", type="service", sale_price_paise=0, tax=cls.tax)
        cls.variant = Variant.objects.create(product=cls.product, name="Odoo", price_delta_paise=56000)
        cls.plan = Plan.objects.create(name="Monthly", frequency="monthly", base_price_paise=100000, tax=cls.tax)

    def login_as(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)

    def post_ok(self, route, data):
        response = self.client.post("/api/" + route, data, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def draft(self, customer=None):
        today = timezone.localdate()
        return self.post_ok("subscriptions", {
            "customer": (customer or self.customer).pk, "plan": self.plan.pk,
            "start_date": str(today), "expiry_date": str(today + timedelta(days=365)),
            "lines": [{"product_id": self.product.pk, "variant_id": self.variant.pk, "quantity": 1}],
        })

    def advance(self, subscription_id, action, expected=200):
        response = self.client.post(f"/api/subscriptions/{subscription_id}/transition", {"action": action}, format="json")
        self.assertEqual(response.status_code, expected, response.data)
        return response.data

    def test_admin_setup_template_to_active_and_billing_total(self):
        self.login_as(self.admin)
        tax = self.post_ok("taxes", {"name": "GST 18%", "rate_bps": 1800})
        product = self.post_ok("products", {"name": "Connectors", "type": "service", "sale_price_paise": 0,
            "tax_id": tax["id"], "variants": [{"name": "Odoo", "price_delta_paise": 56000}]})
        plan = self.post_ok("plans", {"name": "Core", "base_price_paise": 100000, "frequency": "monthly", "tax_id": tax["id"]})
        discount = self.post_ok("discounts", {"name": "Welcome", "kind": "fixed", "value": 1000, "scope": "subscription"})
        self.assertEqual(discount["used_count"], 0)
        template = self.post_ok("templates", {"name": "Core + Odoo", "plan_id": plan["id"], "valid_days": 7,
            "lines": [{"product_id": product["id"], "variant_id": product["variants"][0]["id"], "quantity": 1}]})
        self.assertEqual(template["lines"][0]["unit_price_paise"], 56000)
        today = timezone.localdate()
        subscription = self.post_ok("subscriptions", {"customer": self.customer.pk, "template_id": template["id"],
            "start_date": str(today), "expiry_date": str(today + timedelta(days=365))})
        self.assertEqual(subscription["status"], "draft")
        self.assertEqual(subscription["permitted_actions"], ["quote", "close"])
        self.assertTrue(subscription["number"].startswith("SUB-"))
        for action, state in [("quote", "quotation"), ("confirm", "confirmed"), ("activate", "active")]:
            self.assertEqual(self.advance(subscription["id"], action)["status"], state)
        sub = due_subscriptions(today).get(pk=subscription["id"])
        line = sub.lines.get()
        self.assertEqual(line.unit_price_paise, 56000)
        snapshot = calculate_invoice(plan_fee_paise=sub.plan.base_price_paise, plan_tax_rate_bps=sub.plan.tax.rate_bps,
            lines=[BillableLine("Odoo", line.quantity, line.unit_price_paise, line.tax.rate_bps, line.product_id)],
            product_discounts=[], subscription_discount=None, period=BillingPeriod(today, today + timedelta(days=30)))
        self.assertEqual(snapshot["subtotal_paise"], 156000)
        self.assertEqual(snapshot["tax_paise"], 28080)
        self.assertEqual(snapshot["total_paise"], 184080)
        Product.objects.filter(pk=product["id"]).update(sale_price_paise=999999)
        self.assertEqual(sub.lines.get().unit_price_paise, 56000)
        self.assertEqual(self.client.get("/api/products").data["count"], 2)

    def test_public_registration_login_and_me(self):
        response = self.post_ok("auth/register", {"email": "New@EXAMPLE.com", "password": PASSWORD, "full_name": "New"})
        self.assertEqual(response["role"], "customer")
        self.assertNotIn("password", response)
        user = User.objects.get(email="new@example.com")
        self.assertNotEqual(user.password, PASSWORD)
        response = self.client.post("/api/auth/login", {"email": "NEW@example.COM", "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(set(response.data), {"token", "user"})
        self.client.credentials(HTTP_AUTHORIZATION="Token " + response.data["token"])
        self.assertEqual(self.client.get("/api/auth/me").data["id"], user.pk)

    def test_customer_directory_persists_new_account_and_is_staff_only(self):
        self.login_as(self.admin)
        response = self.client.post("/api/auth/register", {
            "email": "newbuyer@example.com", "password": PASSWORD,
            "full_name": "New Buyer", "role": "customer",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        created_id = response.data["id"]

        self.login_as(self.staff)
        directory = self.client.get("/api/customers")
        self.assertEqual(directory.status_code, 200, directory.data)
        self.assertIn(created_id, [customer["id"] for customer in directory.data["results"]])
        self.assertTrue(all(customer["role"] == "customer" for customer in directory.data["results"]))
        self.assertNotIn("password", directory.data["results"][-1])

        self.login_as(self.customer)
        self.assertEqual(self.client.get("/api/customers").status_code, 403)

    def test_invalid_and_inactive_login(self):
        for password in ["wrong", PASSWORD]:
            if password == PASSWORD:
                User.objects.filter(pk=self.customer.pk).update(is_active=False)
            response = self.client.post("/api/auth/login", {"email": self.customer.email, "password": password})
            self.assertEqual(response.status_code, 401)
            self.assertIn("detail", response.data)

    def test_duplicate_email_and_password_rules(self):
        response = self.client.post("/api/auth/register", {"email": "CUSTOMER@Example.com", "password": PASSWORD, "full_name": "Duplicate"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        for password in ["Short!Aa", "alllowercase!", "ALLUPPERCASE!", "NoSpecial123", "Abcdefgh "]:
            with self.subTest(password=password):
                response = self.client.post("/api/auth/register", {"email": "new@example.com", "password": password, "full_name": "New"})
                self.assertEqual(response.status_code, 400)
                self.assertIn("password", response.data)
        self.assertEqual(self.client.post("/api/auth/register", {"email": "invalid", "password": PASSWORD, "full_name": "New"}).status_code, 400)

    def test_only_admin_can_create_staff_or_admin(self):
        for actor in [None, self.customer, self.staff]:
            if actor:
                self.login_as(actor)
            for role in ["staff", "admin"]:
                response = self.client.post("/api/auth/register", {"email": "escalation@example.com", "password": PASSWORD,
                    "full_name": "Escalation", "role": role})
                self.assertEqual(response.status_code, 400, response.data)
        self.login_as(self.admin)
        self.assertEqual(self.post_ok("auth/register", {"email": "newstaff@example.com", "password": PASSWORD,
            "full_name": "Staff", "role": "staff"})["role"], "staff")

    def test_catalog_mutations_are_admin_only(self):
        for actor in [self.staff, self.customer]:
            self.login_as(actor)
            for route in ["products", "plans", "taxes", "discounts", "templates"]:
                with self.subTest(role=actor.role, route=route):
                    self.assertEqual(self.client.post("/api/" + route, {}, format="json").status_code, 403)
                    self.assertEqual(self.client.patch("/api/" + route + "/1", {}, format="json").status_code, 403)
                    self.assertEqual(self.client.delete("/api/" + route + "/1").status_code, 403)
            self.assertEqual(self.client.post(f"/api/products/{self.product.pk}/variants", {}, format="json").status_code, 403)

    def test_customer_cannot_read_internal_catalog_and_cost_prices(self):
        self.login_as(self.customer)
        for route in ["products", "plans", "taxes", "discounts", "templates"]:
            with self.subTest(route=route):
                self.assertEqual(self.client.get("/api/" + route).status_code, 403)
        self.login_as(self.staff)
        self.assertEqual(self.client.get("/api/products").status_code, 200)

    def test_customer_ownership_on_all_access_paths(self):
        self.login_as(self.staff)
        mine = self.draft()
        other = self.draft(self.other)
        self.login_as(self.customer)
        response = self.client.get("/api/subscriptions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        self.assertEqual([s["id"] for s in response.data["results"]], [mine["id"]])
        self.assertEqual(self.client.get(f'/api/subscriptions/{other["id"]}').status_code, 404)
        own = self.client.get(f'/api/subscriptions/{mine["id"]}')
        self.assertEqual(own.data["permitted_actions"], [])
        for subscription in [mine, other]:
            url = f'/api/subscriptions/{subscription["id"]}'
            self.assertEqual(self.client.patch(url, {"customer": self.customer.pk}, format="json").status_code,
                             403 if subscription == mine else 404)
            self.assertEqual(self.client.delete(url).status_code, 403)
            self.assertEqual(self.client.post(url + "/transition", {"action": "quote"}, format="json").status_code,
                             403 if subscription == mine else 404)
        self.assertEqual(self.client.post("/api/subscriptions", {}, format="json").status_code, 403)

    def test_unauthenticated_access_rejected(self):
        for route in ["auth/me", "products", "plans", "taxes", "discounts", "templates", "subscriptions"]:
            self.assertEqual(self.client.get("/api/" + route).status_code, 401)

    def test_quote_expires_at_exact_validity_boundary(self):
        self.login_as(self.staff)
        sub = self.draft()
        self.advance(sub["id"], "quote")
        boundary = timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=2), time.min))
        Subscription.objects.filter(pk=sub["id"]).update(quote_expires_at=boundary)
        with patch("yascn.services.timezone.now", return_value=boundary):
            self.advance(sub["id"], "confirm", expected=400)
            response = self.client.get(f'/api/subscriptions/{sub["id"]}')
            self.assertEqual(response.data["status"], "expired")
            self.assertEqual(response.data["permitted_actions"], [])
        self.assertEqual(Subscription.objects.get(pk=sub["id"]).status, "expired")

    def test_invalid_transitions_and_active_edit_protection(self):
        self.login_as(self.staff)
        sub = self.draft()
        self.advance(sub["id"], "activate", expected=400)
        self.advance(sub["id"], "unknown", expected=400)
        for action in ["quote", "confirm", "activate"]:
            self.advance(sub["id"], action)
        url = f'/api/subscriptions/{sub["id"]}'
        self.advance(sub["id"], "activate", expected=400)
        self.assertEqual(self.client.patch(url, {"lines": []}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 400)

    def test_subscription_validation_and_server_owned_fields(self):
        self.login_as(self.staff)
        today = timezone.localdate()
        base = {"customer": self.customer.pk, "plan": self.plan.pk, "start_date": str(today),
            "expiry_date": str(today + timedelta(days=60)), "lines": [{"product_id": self.product.pk, "quantity": 1}]}
        bad_values = [{"customer": self.staff.pk}, {"expiry_date": str(today)}, {"lines": []},
            {"lines": [{"product_id": self.product.pk, "quantity": 0}]}, {"status": "active"},
            {"next_bill_date": str(today)}, {"number": "SUB-FAKE"}, {"plan": 999999}]
        for invalid in bad_values:
            response = self.client.post("/api/subscriptions", {**base, **invalid}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        foreign = Product.objects.create(name="Foreign", type="service", sale_price_paise=0)
        response = self.client.post("/api/subscriptions", {**base, "lines": [{"product_id": foreign.pk,
            "variant_id": self.variant.pk, "quantity": 1}]}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_minimum_quantity_and_plan_availability(self):
        self.login_as(self.staff)
        Plan.objects.filter(pk=self.plan.pk).update(minimum_quantity=2)
        today = timezone.localdate()
        body = {"customer": self.customer.pk, "plan": self.plan.pk, "start_date": str(today),
            "expiry_date": str(today + timedelta(days=60)), "lines": [{"product_id": self.product.pk, "quantity": 1}]}
        self.assertEqual(self.client.post("/api/subscriptions", body, format="json").status_code, 400)
        body["lines"][0]["quantity"] = 2
        Plan.objects.filter(pk=self.plan.pk).update(available_from=today + timedelta(days=1))
        self.assertEqual(self.client.post("/api/subscriptions", body, format="json").status_code, 400)

    def test_draft_edit_moves_billing_cursor(self):
        self.login_as(self.staff)
        sub = self.draft()
        new_start = timezone.localdate() + timedelta(days=1)
        response = self.client.patch(f'/api/subscriptions/{sub["id"]}', {"start_date": str(new_start)}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["next_bill_date"], str(new_start))

    def test_partial_nested_line_replacement_returns_field_errors(self):
        self.login_as(self.staff)
        sub = self.draft()
        for line in [{"quantity": 1}, {"product_id": self.product.pk}]:
            response = self.client.patch(f'/api/subscriptions/{sub["id"]}', {"lines": [line]}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        response = self.client.patch(f'/api/subscriptions/{sub["id"]}',
            {"lines": [{"product_id": self.product.pk, "variant_id": self.variant.pk, "quantity": 2}]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["lines"][0]["unit_price_paise"], 56000)
        self.assertEqual(response.data["lines"][0]["quantity"], 2)

    def test_template_snapshot_is_not_changed_by_later_template_edits(self):
        self.login_as(self.admin)
        template = self.post_ok("templates", {"name": "Snapshot", "plan_id": self.plan.pk, "valid_days": 3,
            "lines": [{"product_id": self.product.pk, "variant_id": self.variant.pk, "quantity": 1}]})
        today = timezone.localdate()
        sub = self.post_ok("subscriptions", {"customer": self.customer.pk, "template_id": template["id"],
            "start_date": str(today), "expiry_date": str(today + timedelta(days=365))})
        expires = datetime.fromisoformat(sub["quote_expires_at"])
        self.assertEqual(timezone.localtime(expires).date(), today + timedelta(days=3))
        response = self.client.patch(f'/api/templates/{template["id"]}',
            {"lines": [{"product_id": self.product.pk, "quantity": 4, "unit_price_paise": 300}]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        saved = Subscription.objects.get(pk=sub["id"])
        self.assertEqual(saved.lines.get().unit_price_paise, 56000)
        self.assertEqual(saved.lines.get().quantity, 1)

    def test_discount_and_tax_validation(self):
        self.login_as(self.admin)
        for body in [
            {"name": "Bad", "kind": "percent", "value": 10001, "scope": "subscription"},
            {"name": "Bad", "kind": "fixed", "value": 1, "scope": "product"},
            {"name": "Bad", "kind": "fixed", "value": 1, "scope": "subscription", "product_id": self.product.pk},
            {"name": "Bad", "kind": "fixed", "value": -1, "scope": "subscription"},
        ]:
            self.assertEqual(self.client.post("/api/discounts", body, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/taxes", {"name": "Bad", "rate_bps": 10001}).status_code, 400)
        self.assertEqual(self.client.delete(f"/api/products/{self.product.pk}").status_code, 204)

    def test_protected_delete_returns_validation_error(self):
        self.login_as(self.admin)
        self.draft()
        self.assertEqual(self.client.delete(f"/api/products/{self.product.pk}").status_code, 400)
        self.assertEqual(self.client.delete(f"/api/plans/{self.plan.pk}").status_code, 400)

    def test_variant_endpoint_and_effective_price_override(self):
        self.login_as(self.admin)
        variant = self.post_ok(f"products/{self.product.pk}/variants", {"name": "Other", "price_delta_paise": 100})
        url = f'/api/products/{self.product.pk}/variants/{variant["id"]}'
        self.assertEqual(self.client.patch(url, {"price_delta_paise": 200}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)
        today = timezone.localdate()
        sub = self.post_ok("subscriptions", {"customer": self.customer.pk, "plan": self.plan.pk,
            "start_date": str(today), "expiry_date": str(today + timedelta(days=60)),
            "lines": [{"product_id": self.product.pk, "variant_id": self.variant.pk, "quantity": 1, "unit_price_paise": 57000}]})
        self.assertEqual(sub["lines"][0]["unit_price_paise"], 57000)


class DatabaseTests(TestCase):
    def test_seed_command_is_repeatable_and_preserves_cursor(self):
        with patch.dict("os.environ", {"BRIGHTLOOP_DEMO_PASSWORD": PASSWORD}):
            call_command("seed_yascn_demo", stdout=StringIO())
            sub = Subscription.objects.get(number="SUB-DEMO-0001")
            self.assertEqual(sub.status, "active")
            self.assertEqual(sub.lines.get().unit_price_paise, 56000)
            sub.next_bill_date += timedelta(days=30)
            sub.save()
            call_command("seed_yascn_demo", stdout=StringIO())
            self.assertEqual(Subscription.objects.count(), 1)
            self.assertEqual(Subscription.objects.get(pk=sub.pk).next_bill_date, sub.next_bill_date)
            self.assertTrue(User.objects.get(role="admin").check_password(PASSWORD))

    def test_seed_requires_explicit_valid_password(self):
        with patch.dict("os.environ", {"BRIGHTLOOP_DEMO_PASSWORD": ""}):
            with self.assertRaises(CommandError):
                call_command("seed_yascn_demo", stdout=StringIO())
        self.assertEqual(User.objects.count(), 0)

    def test_case_insensitive_email_database_constraint(self):
        User.objects.create_user("owner@example.com", PASSWORD, full_name="Owner")
        with self.assertRaises(IntegrityError), transaction.atomic():
            # bulk_create deliberately bypasses manager and save normalization.
            User.objects.bulk_create([User(email="OWNER@EXAMPLE.COM", full_name="Duplicate")])

    def test_due_query_catches_up_past_cycles_but_skips_after_expiry(self):
        user = User.objects.create_user("owner@example.com", PASSWORD, full_name="Owner")
        plan = Plan.objects.create(name="Monthly", base_price_paise=100, frequency="monthly")
        today = timezone.localdate()
        for status, next_date, expiry in [
            ("active", today, today + timedelta(days=60)),
            ("paused", today, today + timedelta(days=60)),
            ("expired", today, today + timedelta(days=60)),
            ("active", today + timedelta(days=1), today + timedelta(days=60)),
            ("active", today - timedelta(days=1), today),
            ("active", today, today),
        ]:
            Subscription.objects.create(customer=user, plan=plan, status=status, start_date=today - timedelta(days=1),
                expiry_date=expiry, next_bill_date=next_date)
        self.assertEqual(due_subscriptions(today).count(), 2)
