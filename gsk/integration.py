"""Production bridge between billing orchestration and teammate ORM models."""

class IntegrationPending(RuntimeError):
    pass


class BillingORMRepository:
    def due_candidates(self, as_of):
        from yascn.billing import due_candidates

        return due_candidates(as_of)

    def invoice_exists(self, subscription_id, period_start):
        from aliar.models import Invoice

        # Include cancelled revisions: a cancelled period is reissued, never rebilled.
        return Invoice.objects.filter(
            subscription_id=subscription_id, period_start=period_start
        ).exists()

    def create_period_if_missing(self, candidate, period, snapshot):
        from aliar.services import create_for_candidate

        # ALIAR owns the atomic invoice, discount usage, and cursor writes.
        return create_for_candidate(candidate, period, snapshot)


def get_repository():
    return BillingORMRepository()
