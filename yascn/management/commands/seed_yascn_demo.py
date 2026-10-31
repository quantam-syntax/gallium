"""Create the YASCN half of the demo without altering existing billing cursors."""
import os
from datetime import timedelta
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from yascn.models import User, Tax, Product, Variant, Plan, QuotationTemplate, TemplateLine, Subscription
from yascn.serializers import SubscriptionSerializer
from yascn.services import transition
from yascn.validators import validate_password


class Command(BaseCommand):
    help = "Seed an admin, customer, GST, Odoo variant, plan, template, and active subscription."

    def add_arguments(self, parser):
        parser.add_argument("--admin-email", default="admin@brightloop.example")
        parser.add_argument("--customer-email", default="customer@brightloop.example")

    @transaction.atomic
    def handle(self, *args, **options):
        number = "SUB-DEMO-0001"
        existing = Subscription.objects.filter(number=number).first()
        if existing:
            self.stdout.write(f"Demo already exists: {existing.number}; no records changed.")
            return
        password = os.environ.get("BRIGHTLOOP_DEMO_PASSWORD", "")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError("Set BRIGHTLOOP_DEMO_PASSWORD: " + "; ".join(exc.messages))
        if options["admin_email"].strip().lower() == options["customer_email"].strip().lower():
            raise CommandError("Admin and customer emails must differ.")
        accounts = []
        for email, role, name in [(options["admin_email"], "admin", "Demo Admin"),
                                  (options["customer_email"], "customer", "Example Shop")]:
            user = User.objects.filter(email__iexact=email.strip()).first()
            if user and (user.role != role or not user.is_active):
                raise CommandError(f"Existing account must be active with role {role}: {email}")
            if user is None:
                user = User.objects.create_user(email, password, full_name=name, role=role,
                    company_name="Example Shop" if role == "customer" else "Brightloop")
            accounts.append(user)
        admin, customer = accounts
        tax = Tax.objects.create(name="Demo GST 18%", rate_bps=1800)
        product = Product.objects.create(name="Demo Integration", type="service", sale_price_paise=0,
            cost_price_paise=0, notes="Optional Odoo connector", tax=tax)
        variant = Variant.objects.create(product=product, name="Odoo", price_delta_paise=56000)
        plan = Plan.objects.create(name="Demo Monthly", base_price_paise=100000, frequency="monthly", tax=tax)
        template = QuotationTemplate.objects.create(name="Demo Monthly + Odoo", plan=plan, valid_days=14)
        TemplateLine.objects.create(template=template, product=product, variant=variant, quantity=1, unit_price_paise=56000)
        today = timezone.localdate()
        serializer = SubscriptionSerializer(data={"customer": customer.pk, "template_id": template.pk,
            "start_date": str(today), "expiry_date": str(today + timedelta(days=365)), "payment_terms_days": 14},
            context={"request": SimpleNamespace(user=admin)})
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save(number=number)
        for action in ["quote", "confirm", "activate"]:
            transition(subscription, action)
        self.stdout.write(self.style.SUCCESS(
            f"Created {number}; expected first invoice 184080 paise. "
            f"Admin: {admin.email}; customer: {customer.email}. Existing passwords are preserved."
        ))
