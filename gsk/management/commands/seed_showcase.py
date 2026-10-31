"""Idempotent, explicitly fictional data for a populated local demo."""

import os
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from aliar.models import Invoice
from aliar.services import confirm, create_period_if_missing, record_payment
from gsk.integration import BillingORMRepository
from gsk.service import run
from yascn.models import (
    Discount, Plan, Product, QuotationTemplate, Subscription, SubscriptionLine,
    Tax, TemplateLine, User, Variant,
)
from yascn.validators import validate_password


PRODUCT_NAMES = (
    "Workspace Core", "CRM Flow", "Inventory Pulse", "Invoice Studio", "Support Desk",
    "Analytics Hub", "Team Scheduler", "Document Vault", "Campaign Pilot", "API Gateway",
    "Project Board", "Expense Track", "Identity Shield", "Data Sync", "Commerce Bridge",
    "Field Service", "Knowledge Base", "Contract Manager", "HR Portal", "Asset Monitor",
    "Feedback Loop", "Workflow Builder", "Forecast Engine", "Partner Portal", "Audit Trail",
)


class ShowcaseRepository(BillingORMRepository):
    def __init__(self, ids):
        self.ids = ids

    def due_candidates(self, as_of):
        from yascn.billing import due_candidates

        return due_candidates(as_of, subscription_ids=self.ids)

    def create_period_if_missing(self, candidate, period, snapshot):
        # Historical issue dates give the showcase realistic aging and overdue rows.
        # The finance service still owns the invoice, discount, and cursor transaction.
        subscription = Subscription.objects.get(pk=candidate.id)
        try:
            return create_period_if_missing(
                subscription, period, {**snapshot, "demo_fixture": True}, issued_on=period.start
            )
        except ValidationError as exc:
            raise ValueError(str(exc.detail)) from exc


class Command(BaseCommand):
    help = "Create 25 fictional products, 50 customers and 300 active subscriptions with real billing history. Safe to rerun."

    def handle(self, *args, **options):
        password = os.environ.get("BRIGHTLOOP_DEMO_PASSWORD", "")
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            raise CommandError("Set BRIGHTLOOP_DEMO_PASSWORD: " + "; ".join(exc.messages)) from exc

        today = timezone.localdate()
        with transaction.atomic():
            admin = User.objects.filter(role="admin", is_active=True).order_by("pk").first()
            if admin is None:
                admin = User.objects.create_user(
                    "showcase-admin@brightloop.example", password,
                    full_name="Showcase Admin", company_name="Brightloop", role="admin",
                )
            customers = []
            for index in range(1, 51):
                email = f"showcase-customer-{index:03d}@brightloop.example"
                customer = User.objects.filter(email=email).first()
                if customer is None:
                    customer = User.objects.create_user(
                        email, password, full_name=f"Showcase Customer {index:03d}",
                        company_name=f"Showcase Company {index:03d}", role="customer",
                    )
                elif customer.role != "customer":
                    raise CommandError(f"Showcase email belongs to another role: {email}")
                customers.append(customer)

            gst, _ = Tax.objects.get_or_create(name="Showcase GST 18%", defaults={"rate_bps": 1800})
            reduced, _ = Tax.objects.get_or_create(name="Showcase GST 5%", defaults={"rate_bps": 500})
            plans = []
            for name, frequency, fee, tax in (
                ("Showcase Monthly", "monthly", 99000, gst),
                ("Showcase Annual", "yearly", 999000, gst),
                ("Showcase Weekly", "weekly", 29000, reduced),
            ):
                plan, _ = Plan.objects.get_or_create(
                    name=name, defaults={"frequency": frequency, "base_price_paise": fee,
                    "tax": tax, "minimum_quantity": 1, "allow_pause": True,
                    "allow_renew": True, "allow_cancel": True},
                )
                plans.append(plan)

            products = []
            variants = []
            for index, name in enumerate(PRODUCT_NAMES):
                product, _ = Product.objects.get_or_create(
                    name=f"Showcase · {name}",
                    defaults={"type": "service" if index % 4 else "software",
                    "sale_price_paise": (490 + index * 80) * 100,
                    "cost_price_paise": (120 + index * 17) * 100,
                    "notes": "Fictional Brightloop showcase product with recurring adoption data.",
                    "tax": gst if index % 4 else reduced},
                )
                variant, _ = Variant.objects.get_or_create(
                    product=product, name="Enterprise", defaults={"price_delta_paise": 56000 + index * 1000}
                )
                products.append(product)
                variants.append(variant)

            for index, plan in enumerate(plans):
                template, _ = QuotationTemplate.objects.get_or_create(
                    name=f"Showcase {plan.frequency.title()} Offer",
                    defaults={"plan": plan, "valid_days": 14 + index * 7},
                )
                TemplateLine.objects.get_or_create(
                    template=template, product=products[index],
                    defaults={"quantity": 1, "unit_price_paise": products[index].sale_price_paise},
                )

            # Unlimited rules keep a rerun and a later billing run deterministic.
            product_discount, _ = Discount.objects.get_or_create(
                name="Showcase Team Seats 10%",
                defaults={"kind": "percent", "value": 1000, "scope": "product",
                "product": products[0], "min_quantity": 3, "active": True},
            )
            subscription_discount, _ = Discount.objects.get_or_create(
                name="Showcase Loyalty ₹250",
                defaults={"kind": "fixed", "value": 25000, "scope": "subscription",
                "min_purchase_paise": 100000, "active": True},
            )

            ids = []
            for product_index, product in enumerate(products):
                for slot in range(12):
                    ordinal = product_index * 12 + slot + 1
                    number = f"SUB-SHOWCASE-{ordinal:04d}"
                    subscription = Subscription.objects.filter(number=number).first()
                    if subscription is None:
                        recent_count = 9 if product_index < 5 else 3 if product_index < 10 else 6
                        age = (slot * 7 + product_index * 3) % 30
                        age += 0 if slot < recent_count else 30
                        started = today - timedelta(days=age)
                        plan = plans[2] if ordinal % 10 == 0 else plans[1] if ordinal % 7 == 0 else plans[0]
                        subscription = Subscription.objects.create(
                            number=number, customer=customers[(ordinal - 1) % len(customers)],
                            plan=plan, status="active", start_date=started,
                            expiry_date=started + timedelta(days=365), next_bill_date=started,
                            activated_at=timezone.now(), payment_terms_days=14,
                            subscription_discount=subscription_discount if ordinal % 13 == 0 else None,
                        )
                        variant = variants[product_index] if ordinal % 4 == 0 else None
                        SubscriptionLine.objects.create(
                            subscription=subscription, product=product, variant=variant,
                            quantity=3 if product_index == 0 and ordinal % 3 == 0 else 1 + ordinal % 3,
                            unit_price_paise=product.sale_price_paise + (variant.price_delta_paise if variant else 0),
                            tax=product.tax,
                        )
                    ids.append(subscription.pk)

        result = run(ShowcaseRepository(ids), today)
        if result["error_count"]:
            raise CommandError(f"Showcase billing had {result['error_count']} errors: {result['errors'][:3]}")

        payment_count = 0
        invoices = Invoice.objects.filter(subscription_id__in=ids).prefetch_related("payments")
        for invoice in invoices.iterator(chunk_size=200):
            if invoice.status == "draft":
                invoice = confirm(invoice.pk)
            if invoice.status != "confirmed" or invoice.payments.exists() or invoice.total_paise == 0:
                continue
            mode = invoice.subscription_id % 10
            if mode >= 7:
                continue
            amount = invoice.total_paise if mode < 4 else max(1, invoice.total_paise // 2)
            paid_on = min(today, invoice.issued_on + timedelta(days=2 + mode))
            record_payment(
                invoice.pk, created_by=admin, method=("bank", "card", "upi")[mode % 3],
                amount_paise=amount, paid_on=paid_on, note="Fictional showcase payment",
            )
            payment_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Showcase ready: {len(products)} products, {len(customers)} customers, "
            f"{len(ids)} subscriptions; {result['created_count']} new invoices, "
            f"{payment_count} new payments. All records are fictional."
        ))
