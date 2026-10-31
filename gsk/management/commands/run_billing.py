"""Run the same idempotent billing service used by the Control Tower."""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from gsk.integration import get_repository
from gsk.service import run


class Command(BaseCommand):
    help = "Create all due invoices through the standard idempotent billing service."

    def add_arguments(self, parser):
        parser.add_argument("--as-of", type=date.fromisoformat)

    def handle(self, *args, **options):
        as_of = options["as_of"] or timezone.localdate()
        if as_of > timezone.localdate():
            raise CommandError("Future billing dates are not allowed.")
        result = run(get_repository(), as_of)
        self.stdout.write(
            f"Billing {as_of}: {result['created_count']} created, "
            f"{result['skipped_count']} skipped, {result['error_count']} errors."
        )
        for error in result["errors"]:
            self.stderr.write(str(error))
        if result["error_count"]:
            raise CommandError("Billing finished with errors; inspect the records above.")
