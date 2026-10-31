# Brightloop shared contract

This file is the single source of truth for all four teammates. GSK updates it before any shared interface changes. The target is a working local demo by hour 6; hours 6–8 are for fixes, delivery, and optional polish.

**Repository sync:** `main` was rewritten on 31 October to correct GDM's commit author name. Before pushing from an older clone, follow [README.md's sync instructions](README.md#sync-after-the-author-name-correction); do not force-push the old history.

## Architecture and data

Django REST Framework + SQLite backend, React/Vite frontend. `gsk/` owns project wiring and billing; `yascn/` owns identity, catalog, and subscriptions; `aliar/` owns invoices, payments, and reporting; `gdm/` owns UI. GSK alone edits root integration files. Use one local billing worker, short database transactions, and database uniqueness constraints. Routes start `/api` with no trailing slash. IDs are integers; dates are ISO `YYYY-MM-DD`; timestamps include a timezone. Money is integer paise (₹560 = 56000); rates are basis points (1800 = 18%).

| Owner | Model | Fields |
| --- | --- | --- |
| YASCN | User | `id`, case-insensitive unique `email`, password hash, `full_name`, `company_name`, `role` (`admin`, `staff`, `customer`), `is_active`. Define before the first migration. |
| YASCN | Product, Variant | Product: `id`, `name`, `type`, `sale_price_paise`, `cost_price_paise`, `notes`, optional `tax_id`, `active`. Variant: `id`, `product_id`, `name`, `price_delta_paise`. |
| YASCN | Plan | `id`, `name`, `base_price_paise`, optional `tax_id`, `frequency` (`daily`, `weekly`, `monthly`, `yearly`), `minimum_quantity`, `available_from`, `available_to`, `auto_close`, `allow_pause`, `allow_renew`, `allow_cancel`. |
| YASCN | Tax, Discount | Tax: `id`, `name`, `rate_bps`, `active`. Discount: `id`, `name`, `kind` (`fixed`, `percent`), `value`, `scope` (`product`, `subscription`), optional `product_id`, `min_purchase_paise`, `min_quantity`, `starts_on`, `ends_on`, optional `usage_limit`, `used_count`, `active`. |
| YASCN | QuotationTemplate, TemplateLine | Template: `id`, `name`, `plan_id`, `valid_days`. Line: `product_id`, optional `variant_id`, `quantity`, `unit_price_paise`. |
| YASCN | Subscription, SubscriptionLine | Subscription: `id`, unique `number`, `customer_id`, `plan_id`, `status`, `start_date`, exclusive `expiry_date`, optional `quote_expires_at`, `payment_terms_days`, `next_bill_date`, optional assigned `subscription_discount_id`. Line: `product_id`, optional `variant_id`, `quantity`, `unit_price_paise`, optional `tax_id`, `active`. |
| ALIAR | Invoice | `id`, unique `number`, `subscription_id`, `customer_id`, `period_start`, exclusive `period_end`, `revision`, `issued_on`, `due_on`, `status`, `subtotal_paise`, `discount_paise`, `tax_paise`, `total_paise`, immutable `snapshot`, optional `sent_at`. |
| ALIAR | Payment | `id`, `invoice_id`, `method`, `amount_paise`, `paid_on`, `note`, `created_by_id`. |

For a fixed discount, `value` is paise; for a percentage discount, `value` is basis points. A subscription line's `unit_price_paise` is the effective price **including** its chosen variant surcharge, so billing never adds that surcharge twice. Template lines copy to the subscription; later catalog edits do not rewrite them. Bill outstanding past periods before changing subscription lines or quantities so catch-up invoices use the old terms; the edit affects the next cycle. Product discounts apply to eligible product lines; whole-subscription discounts require assignment to a subscription. Plan availability controls new sign-ups; subscription expiry stops existing billing.

## Statuses and API

Subscription statuses: `draft`, `quotation`, `confirmed`, `active`, `paused`, `expired`, `closed`. Transition: `POST /api/subscriptions/{id}/transition` with `{ "action": "quote|confirm|activate|pause|resume|renew|close" }`. Responses include `permitted_actions`. Customer add-on and quantity edits affect the next invoice without proration.

Invoice statuses: `draft`, `confirmed`, `paid`, `cancelled`. `is_overdue` and partial-payment badges are derived, not stored statuses. Paid invoices cannot be cancelled without a refund workflow. Printable invoices use a frontend print view.

All lists return `{ "results": [], "count": 0, "next": null, "previous": null }`. Non-field errors return `{ "detail": "..." }`; validation errors identify fields. Every mutation checks role and ownership on the backend.

- YASCN: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, password-reset request/confirm, CRUD `/api/products`, `/api/plans`, `/api/taxes`, `/api/discounts`, `/api/templates`, `/api/subscriptions`. Login returns `{ "token": "...", "user": { "id": 1, "email": "...", "role": "admin", "full_name": "..." } }`. Subsequent calls send `Authorization: Token <token>`.
- GSK: `GET /api/billing/preview` and `POST /api/billing/run`, with optional `as_of` defaulting to today. Run is staff/admin only and never bills future periods.
- ALIAR: list/detail `/api/invoices`, actions `/api/invoices/{id}/confirm`, `/cancel`, `/send`, `/reissue`, `GET/POST /api/invoices/{id}/payments`, and `GET /api/dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD`.

Subscription responses contain `id`, `number`, `status`, `customer`, `plan`, `start_date`, `expiry_date`, `next_bill_date`, `lines`, and `permitted_actions`. Invoice detail contains `id`, `number`, `customer_name`, `status`, `due_on`, `total_paise`, `paid_paise`, `balance_paise`, `is_overdue`, and `snapshot.lines`. Dashboard returns `active_count`, `gross_mrr_paise`, `invoiced_paise`, `collected_paise`, `outstanding_paise`, and `overdue_count`; invoiced/collected use the date filter, while outstanding/overdue are current open balances. Gross MRR excludes tax and discounts and normalizes active subscriptions' plan fee plus line totals: daily × 365/12, weekly × 52/12, monthly × 1, yearly ÷ 12, rounded to paise. GSK supplies this shared calculation to ALIAR.

Preview returns `{ "as_of": "2026-10-31", "due_count": 1, "expected_total_paise": 184080, "items": [{ "subscription_id": 12, "number": "SUB-0012", "customer_name": "Example Shop", "period_start": "2026-10-31", "period_end": "2026-11-30", "subtotal_paise": 156000, "discount_paise": 0, "tax_paise": 28080, "total_paise": 184080, "issues": [] }], "exceptions": [] }`.

Run returns `{ "created_count": 1, "skipped_count": 0, "error_count": 0, "invoices": [{ "id": 25, "number": "INV-0025", "subscription_id": 12, "total_paise": 184080 }], "errors": [] }`. Payment POST body is `{ "method": "bank", "amount_paise": 50000, "paid_on": "2026-10-31", "note": "..." }`; response includes the payment and updated `paid_paise`/`balance_paise`.

## Billing and gates

GSK reads due subscriptions and advances `next_bill_date` transactionally after creating or deliberately skipping each cycle. Monthly/yearly cycles stay anchored to the subscription start day. Catch up missed active cycles; issue no invoice for paused or expired cycles. Preview and run call the same pricing function: plan fee plus active line effective prices (already including variant surcharges); choose the greater saving from eligible product discounts or the assigned whole-subscription discount; calculate tax on discounted amounts; snapshot the breakdown. Increment discount usage only when an invoice is created.

ALIAR enforces unique `(subscription, period_start, revision)` and at most one non-cancelled invoice per `(subscription, period_start)`. Automatic reruns skip any period already represented by an invoice, including cancelled ones; staff reissue creates the next revision. Payments must be positive, cannot exceed balance, and are accepted only on confirmed invoices; zero balance sets `paid`.

Hour 4 gate: fresh migrations, Django checks, auth/ownership smoke tests, and React build. Hour 6 gate: product/variant → plan/template → active subscription → preview → one invoice → partial payment → dashboard; second billing run creates zero invoices and preview totals match saved invoice totals. Fix failures before optional AI work.

## GSK Python adapter handoff

`gsk.service.BillingCandidate` is the read shape for one active due subscription. GSK's adapter must implement `due_candidates(as_of)`, `invoice_exists(subscription_id, period_start)`, and `create_period_if_missing(candidate, period, snapshot)`. YASCN supplies the subscription query and model fields; ALIAR supplies invoice creation and the unique period/revision constraints. `create_period_if_missing` must atomically recheck for an existing invoice, save the snapshot, increment applied discount usage, advance `next_bill_date`, and return `{ "id": ..., "number": ... }`, or return `None` if already invoiced. GSK connects the two apps inside `gsk/integration.py`; no teammate edits another owner's directory.
