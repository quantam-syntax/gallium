# ALIAR finance backend handoff

All implementation is inside `aliar/`. `CONTRACT.md` remains authoritative.

## Integration for GSK

1. YASCN's real User, Subscription, SubscriptionLine, Plan, and Discount are now present and verified. `gsk.settings` already lists `aliar`; no registration change is needed there. ALIAR uses `settings.AUTH_USER_MODEL` and a real foreign key to `yascn.Subscription`.
2. GSK has mounted `aliar.urls` in the production `gsk/urls.py`. This module owns the full `/api/...` paths, without trailing slashes.
3. GSK's production repository now calls `aliar.services.create_for_candidate(candidate, period, snapshot)`. The candidate exposes the subscription's integer `id`. The helper translates finance validation errors to the `ValueError` handled by GSK's run loop.
4. GSK's `invoice_exists` includes cancelled revisions. ALIAR atomically rechecks, saves a draft snapshot, increments applied discount counters, and advances `next_bill_date`. It returns `{id, number}` or `None`. The lower-level interface is `create_period_if_missing(subscription, period, snapshot, issued_on=None)`.
5. `aliar/migrations/0001_initial.py` depends on `yascn.0001_initial` and the swappable User. This dependency has been checked against the delivered models and applied on a fresh database. Run normal demo migrations with `gsk.settings`; never use the in-memory test settings for a persistent server.

GSK's production repository delegates `due_candidates` to `yascn.billing.due_candidates`, checks all invoice revisions, and calls ALIAR's creation service. `aliar/tests/test_phase1.py` covers the original foundation with a test adapter. `aliar/tests/test_production_phase2.py` exercises the unpatched production routes and repository through cancellation, reissue, payments, date filters, overdue reporting, and customer access. The broader production smoke test is in `gsk/tests/test_production_integration.py`.

Reporting expects `Subscription.customer_id`, `plan`, `status`, `payment_terms_days`, `next_bill_date`; `Plan.base_price_paise`, `frequency`; `SubscriptionLine.subscription_id`, `active`, `quantity`, `unit_price_paise`; and `Discount.active`, `usage_limit`, `used_count`. These match the shared contract. Reporting calculates MRR using GSK's frequency ratios, with per-subscription half-up rounding in SQL. Line prices already include variant surcharges. No pricing engine is duplicated.

## API for GDM

- `GET /api/invoices`, `GET /api/invoices/{id}`. Lists support `page`, `page_size` (maximum 100), `status`, `overdue=true`, and `outstanding=true`.
- Staff/admin: `POST /api/invoices/{id}/confirm`, `/cancel`, `/send`, `/reissue`. Reissue returns 201 with a new draft revision; all other actions return 200 with the updated invoice.
- `GET /api/invoices/{id}/payments` is paginated. Staff/admin POST accepts `{ "method": "bank", "amount_paise": 50000, "paid_on": "2026-10-31", "note": "..." }` and returns 201 with `{ "payment": {...}, "paid_paise": ..., "balance_paise": ... }`.
- Staff/admin: `GET /api/dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD`. Inclusive filters apply to invoice issue dates and payment dates respectively. Outstanding and overdue remain current balances. Active count and MRR are current values. Cancelled invoices contribute nothing.
- Customers can read only their own invoices/payment history; mutations and global financial reporting require `role` of `staff` or `admin`. Foreign invoice reads return 404. Anonymous requests return 401.
- Detail includes all contract fields plus period, revision, monetary breakdown, `sent_at`, and derived `is_partially_paid`. `is_overdue` is derived from remaining balance and `due_on < today`; neither partial nor overdue is a stored status.
- Print uses the frontend invoice detail view and browser printing, as specified in the contract. Render saved `snapshot.lines` and amounts. GDM owns that React view; no extra print endpoint is needed.

Payments require confirmation; overpayments and nonpositive amounts return 400. A zero-total invoice becomes paid on confirmation. Cancellation of a partially paid invoice is also rejected because no refund workflow exists. Cancelled detail responses expose zero remaining balance while preserving the historical total. Reissue copies the saved snapshot, preserves cancelled history, creates the next revision, and does not bill again or consume another discount. Invoice snapshots/amounts and recorded payments are immutable through normal model/queryset edits. Use services for ledger mutations. Creation rechecks the subscription's current state and rejects paused, expired, closed, future, or out-of-contract periods. Historical active cycles ending before expiry can still be caught up after the expiry date.

Sending delivers a plain-text invoice summary through Django's configured email backend and records `sent_at` only after successful delivery. Backend connection/delivery failures return a clear 503 and do not mark the invoice sent. The default project backend captures mail locally. An explicit subsequent send delivers again. Email delivery and a database commit are separate systems: a process failure after sending can require staff to inspect the captured mail before retrying.

## Verify on Windows

From the repository root (the development environment is ignored by Git):

```powershell
aliar/.venv/Scripts/python.exe manage.py test aliar.tests --settings=aliar.test_settings
aliar/.venv/Scripts/python.exe manage.py test aliar.tests yascn.tests gsk.tests
aliar/.venv/Scripts/python.exe manage.py migrate --noinput --settings=aliar.test_settings
aliar/.venv/Scripts/python.exe manage.py check
aliar/.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
```

`aliar.test_settings` installs the production models, including `yascn.User`, with a fresh migrated in-memory SQLite database, captured test mail, and a fast test-only password hasher. No substitute model apps remain. `aliar.test_urls` mounts ALIAR beside GSK/YASCN without editing root integration. The phase gate exercises actual login tokens, products, the Odoo variant, quotation/template transitions, GSK preview/run with the test adapter, confirmation, two partial payments, overdue reporting, customer isolation, settlement, and a duplicate-free second billing run.

The initial environment can be created with `uv venv aliar/.venv --python 3.12` and `uv pip install --python aliar/.venv/Scripts/python.exe -r requirements.txt`. On POSIX, use the corresponding `.venv/bin/python` executable. The environment and generated databases/build files are not committed.

The existing frontend builds in this restricted Windows environment with `npm run build -- --configLoader runner` from `gdm/`. Plain `npm run build` hits a parent-directory permission failure in esbuild's config bundling here; no frontend source/config change is required. The latest UI still uses in-memory mock billing/payment state, so its backend connection and per-invoice print output remain GDM/GSK handoffs. Customer payment controls must follow the contract: payment recording is staff/admin only.

## Integrated demo data

First use YASCN's product/plan/quotation/active subscription and GSK's preview/run to create the real invoice. Confirm it through ALIAR, record two partial payments, and inspect the remaining balance, dashboard, and customer detail. Settle the balance and check `paid`; run billing again and check zero new invoices.

For a local demo DB, the optional command below clones an existing invoice into one clearly tagged historical finance fixture with two partial payments and an overdue balance, plus 1,000 additional fixtures for performance checks. It preserves the source invoice and does not change the subscription cursor or discount usage. Fixture prices are copied from the saved source, not newly billed periods. Reruns skip previously seeded numbers. Choose a dedicated demo subscription so synthetic historical periods cannot overlap future real catch-up billing.

```powershell
aliar/.venv/Scripts/python.exe manage.py seed_aliar --source-invoice 1 --staff 1 --records 1000
```

Replace IDs with the GSK-generated source invoice and a real staff/admin user. This command requires the integrated YASCN models and a migrated local demo database. No production data is seeded automatically.
