from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from yascn.models import Subscription
from yascn.services import expire_quotations, maintain_subscription


class Command(BaseCommand):
    help = "Catch up expired active contracts, skip paused cycles, and persist expiry/auto-close."

    def add_arguments(self, parser):
        parser.add_argument("--as-of", type=date.fromisoformat)

    def handle(self, *args, **options):
        as_of = options["as_of"] or timezone.localdate()
        if as_of > timezone.localdate():
            raise CommandError("Future maintenance dates are not allowed.")
        expire_quotations(Subscription.objects.all())
        ids = list(Subscription.objects.filter(status__in=["active", "paused"], expiry_date__lte=as_of).values_list("pk", flat=True))
        failures = 0
        for pk in ids:
            try:
                maintain_subscription(pk, as_of)
            except (ValidationError, ValueError) as exc:
                failures += 1
                self.stderr.write(f"Subscription {pk}: {exc}")
        if failures:
            raise CommandError(f"{failures} subscriptions could not be maintained; failed transactions rolled back.")
        self.stdout.write(self.style.SUCCESS(f"Maintained {len(ids)} expired contracts."))
