"""Read-only, role-scoped context and local demo answers for Brightloop chat."""

import os
import re

from django.utils import timezone
from django.db.models import Count


def _rupees(paise):
    return f"₹{(paise or 0) / 100:,.2f}"


def workspace_context(user):
    from aliar.models import Invoice, Payment
    from yascn.models import Plan, Product, Subscription, User

    if user.role in ("admin", "staff"):
        from aliar.reporting import dashboard

        metrics = dashboard()
        today = timezone.localdate()
        this_month = dashboard(today.replace(day=1), today)
        from .product_analytics import product_trends

        product_rows = product_trends(today)["products"]
        fastest = sorted((item for item in product_rows if item["delta"] > 0), key=lambda item: -item["delta"])[:3]
        slowing = sorted((item for item in product_rows if item["delta"] < 0), key=lambda item: item["delta"])[:3]
        overdue = list(
            Invoice.objects.select_related("customer").with_balances()
            .filter(due_on__lt=timezone.localdate(), balance_paise__gt=0)
            .exclude(status="cancelled")
            .order_by("due_on", "pk")[:5]
        )
        return {
            "scope": "workspace", "as_of": timezone.localdate().isoformat(),
            "metrics": metrics, "this_month": this_month,
            "record_counts": {
                "customers": User.objects.filter(role="customer").count(),
                "products": Product.objects.count(), "plans": Plan.objects.count(),
                "subscriptions": Subscription.objects.count(), "invoices": Invoice.objects.count(),
                "payments": Payment.objects.count(),
                "subscription_statuses": dict(Subscription.objects.values_list("status").annotate(count=Count("pk"))),
                "invoice_statuses": dict(Invoice.objects.values_list("status").annotate(count=Count("pk"))),
            },
            "product_momentum": {
                "fastest": [{"name": item["name"], "delta": item["delta"]} for item in fastest],
                "slowing": [{"name": item["name"], "delta": item["delta"]} for item in slowing],
            },
            "oldest_overdue": [
                {"number": item.number, "customer": item.customer.company_name or item.customer.full_name,
                 "due_on": item.due_on.isoformat(), "balance_paise": item.balance_paise}
                for item in overdue
            ],
        }

    subscriptions = list(
        Subscription.objects.filter(customer=user).select_related("plan")
        .order_by("-start_date", "-pk")[:10]
    )
    invoices = list(
        Invoice.objects.filter(customer=user).with_balances()
        .order_by("-issued_on", "-pk")[:10]
    )
    return {
        "scope": "customer", "as_of": timezone.localdate().isoformat(),
        "subscriptions": [
            {"number": item.number, "plan": item.plan.name, "status": item.status,
             "next_bill_date": item.next_bill_date.isoformat(), "expiry_date": item.expiry_date.isoformat()}
            for item in subscriptions
        ],
        "invoices": [
            {"number": item.number, "status": item.status, "due_on": item.due_on.isoformat(),
             "total_paise": item.total_paise, "balance_paise": item.balance_paise}
            for item in invoices
        ],
    }


def demo_answer(message, context):
    """Deterministic demo answers make the widget usable without an API account."""
    question = message.lower()
    if context["scope"] == "workspace":
        metrics = context["metrics"]
        if "product" in question or "fastest" in question or "slowing" in question:
            momentum = context["product_momentum"]
            rising = ", ".join(f"{item['name']} (+{item['delta']})" for item in momentum["fastest"]) or "none"
            falling = ", ".join(f"{item['name']} ({item['delta']})" for item in momentum["slowing"]) or "none"
            return f"Fastest growing products: {rising}. Slowing products: {falling}. These compare new active contracts in adjacent 30-day windows."
        if any(word in question for word in ("overdue", "late", "chase")):
            if not metrics["overdue_count"]:
                return "There are no overdue invoices right now."
            examples = "; ".join(
                f"{item['number']} ({item['customer']}): {_rupees(item['balance_paise'])}, due {item['due_on']}"
                for item in context["oldest_overdue"]
            )
            return f"{metrics['overdue_count']} invoices are overdue. The oldest are: {examples}. Open Invoices to review the full list."
        if any(word in question for word in ("revenue", "collected", "payment", "money", "owed", "outstanding", "mrr")):
            if any(word in question for word in ("this month", "monthly", "october", "month to date")) and "mrr" not in question:
                month = context["this_month"]
                return (f"This month, invoices total {_rupees(month['invoiced_paise'])} and "
                        f"collected payments total {_rupees(month['collected_paise'])}. "
                        f"Current outstanding across all periods is {_rupees(month['outstanding_paise'])}.")
            return (f"As of {context['as_of']}, gross MRR is {_rupees(metrics['gross_mrr_paise'])}. "
                    f"Collected payments total {_rupees(metrics['collected_paise'])}; "
                    f"{_rupees(metrics['outstanding_paise'])} remains outstanding. "
                    "Collected is all time in this view.")
        if any(word in question for word in ("active", "subscription", "customer")):
            return f"There are {metrics['active_count']} active subscriptions. Open Subscriptions to filter or inspect individual contracts."
        if any(word in question for word in ("bill", "renew", "invoice")):
            return "Use the Billing Control Tower to preview due periods, then Run billing. Each subscription period can be invoiced only once; confirm the draft invoice before recording a payment."
        return "I can answer questions about active subscriptions, MRR, this month's revenue, overdue invoices, product momentum, and the billing workflow. Try ‘What is our MRR?’"

    subscriptions = context["subscriptions"]
    invoices = context["invoices"]
    if any(word in question for word in ("invoice", "payment", "owed", "balance", "overdue")):
        outstanding = sum(item["balance_paise"] for item in invoices if item["status"] != "cancelled")
        if not invoices:
            return "You have no invoices yet. New invoices will appear in your portal after billing runs."
        return (f"Your latest invoice is {invoices[0]['number']}, due {invoices[0]['due_on']}, "
                f"with {_rupees(invoices[0]['balance_paise'])} remaining. "
                f"Across the {len(invoices)} latest invoices, {_rupees(outstanding)} is outstanding.")
    if any(word in question for word in ("renew", "next", "plan", "subscription", "pause", "cancel")):
        if not subscriptions:
            return "You have no subscriptions yet. Contact Brightloop to get started."
        current = subscriptions[0]
        return (f"Your latest subscription {current['number']} is {current['status']} on "
                f"{current['plan']}. Its next billing date is {current['next_bill_date']}. "
                "Open your subscription card to see the actions available for your plan.")
    return "I can help with your subscriptions, next billing date, invoices, and outstanding balance. Try ‘When is my next bill?’"


def answer(message, history, user):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        from .gemini_assistant import generate_answer

        return {"answer": generate_answer(message, history, user, api_key), "mode": "ai"}
    from .gemini_assistant import REFUSAL

    scope_words = (
        "brightloop", "app", "account", "login", "log in", "password", "staff", "admin", "customer",
        "product", "variant", "plan", "tax", "discount", "quote", "quotation", "subscription",
        "bill", "invoice", "payment", "revenue", "mrr", "overdue", "outstanding", "report", "dashboard",
        "renew", "pause", "cancel", "price", "amount", "money", "paid", "owed", "next date",
    )
    relevant = message.lower() + " " + " ".join(item.get("content", "").lower() for item in history[-2:])
    if not any(re.search(r"\b" + re.escape(word) + r"\b", relevant) for word in scope_words):
        return {"answer": REFUSAL, "mode": "demo"}
    context = workspace_context(user)
    return {"answer": demo_answer(message, context), "mode": "demo"}
