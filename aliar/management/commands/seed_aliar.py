"""Generate repeatable demo finance fixtures from a GSK-generated invoice."""

from copy import deepcopy
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from aliar.models import Invoice
from aliar.services import record_payment


class Command(BaseCommand):
    help = (
        "Seed finance demo fixtures from an existing GSK invoice (local demo DB only)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--source-invoice", type=int, required=True)
        parser.add_argument("--staff", type=int, required=True)
        parser.add_argument("--records", type=int, default=1000)

    @transaction.atomic
    def handle(self, *args, **options):
        if not 0 <= options["records"] <= 10000:
            raise CommandError("records must be between 0 and 10000")
        try:
            source = Invoice.objects.get(pk=options["source_invoice"])
            actor = get_user_model().objects.get(pk=options["staff"])
        except (Invoice.DoesNotExist, get_user_model().DoesNotExist) as exc:
            raise CommandError(
                "A source invoice and staff user must already exist."
            ) from exc
        if (
            getattr(actor, "role", None) not in ("admin", "staff")
            or not actor.is_active
        ):
            raise CommandError("--staff must identify an admin or staff user")
        if source.total_paise < 4:
            raise CommandError(
                "Use a source invoice with at least four paise for two partial payments."
            )
        today = timezone.localdate()
        created = 0
        for index in range(options["records"] + 1):
            # Synthetic historical periods cannot alter GSK's billing cursor or
            # discount counters. These records are explicitly marked as fixtures.
            number = f"INV-SEED-{source.pk}-{index}"
            if Invoice.objects.filter(number=number).exists():
                continue
            start = today - timedelta(days=60 + index)
            if Invoice.objects.filter(
                subscription_id=source.subscription_id, period_start=start
            ).exists():
                continue
            end = start + timedelta(days=1)
            snapshot = deepcopy(source.snapshot)
            snapshot.update(
                period_start=start.isoformat(),
                period_end=end.isoformat(),
                demo_fixture=True,
            )
            invoice = Invoice.objects.create(
                number=number,
                subscription_id=source.subscription_id,
                customer_id=source.customer_id,
                period_start=start,
                period_end=end,
                issued_on=start,
                due_on=end,
                status="confirmed",
                snapshot=snapshot,
                subtotal_paise=source.subtotal_paise,
                discount_paise=source.discount_paise,
                tax_paise=source.tax_paise,
                total_paise=source.total_paise,
            )
            if index == 0:
                for _ in range(2):
                    record_payment(
                        invoice.pk,
                        created_by=actor,
                        method="bank",
                        amount_paise=source.total_paise // 4,
                        paid_on=today,
                        note="Seeded demo partial payment",
                    )
            created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created} demo invoices; fixture 0 has two partial payments and an overdue balance. Source invoice is unchanged."
            )
        )
