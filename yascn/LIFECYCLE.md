# Lifecycle and password-reset handoff

GSK's `554e697` production bridge passes the integrated backend gate. This
YASCN delivery implements the deferred backend work; Gauthami owns UI calls and
reset/subscription screens. All code changes are inside `yascn/`.

## Migration and shared configuration

Run `.venv/bin/python manage.py migrate --noinput` before starting the server.
`yascn.0002_subscription_activated_at` adds a nullable internal activation marker,
sets it on activation, and backfills existing active/paused/closed contracts at
migration time. It distinguishes an expired quotation from a previously active
contract so an expired quotation cannot be renewed directly into an active sale.
No contract response fields or existing routes were removed.

GSK should add these concrete route/payload details to the shared contract when
convenient; this delivery does not edit GSK-owned root files. The existing
`include("yascn.urls")` automatically mounts the new endpoints.

## Password reset for Gauthami

Both endpoints are public and accept JSON, without a trailing slash:

- `POST /api/auth/password-reset/request`: `{"email":"customer@example.com"}`.
  Always returns the same 200 message for existing, absent, inactive, or
  undeliverable accounts. No token or user ID is returned in JSON. Malformed
  addresses return a field validation error. Requests are throttled to 5/hour
  per IP using Django's configured cache (single-process local cache by default).
- The email links to `/reset-password?uid=...&token=...` on the frontend. Build
  that route and collect a new password from the user. Reading the link must
  not confirm/reset the password automatically.
- `POST /api/auth/password-reset/confirm`:
  `{"uid":"<from link>","token":"<from link>","password":"NewPassword!123"}`.
  Success returns 200 and asks the user to log in again. Invalid, expired,
  deactivated-user, or reused links return 400. Weak passwords identify the
  password field. Confirmation attempts are throttled to 10/hour per IP.

Tokens use Django's password-reset generator and `PASSWORD_RESET_TIMEOUT`
(default Django timeout: 3 days). GSK can set that standard setting for a shorter
window. A successful reset changes the hash atomically and revokes all existing
DRF tokens for the account. Clear the browser's stored token and send the user
through login; the confirm endpoint does not create a new auth token. Changed
passwords invalidate earlier reset links, including links created before the
password change. Unused links are possession credentials, not public UI data.

The default project backend captures mail under `.email-outbox/`; tests use
memory and temporary captured-mail files. For SMTP, set before starting Django:

```bash
export BRIGHTLOOP_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
export BRIGHTLOOP_SMTP_HOST=smtp.example.com
export BRIGHTLOOP_SMTP_PORT=587
export BRIGHTLOOP_SMTP_USER=mailer
export BRIGHTLOOP_SMTP_PASSWORD='<SMTP credential>'
export BRIGHTLOOP_SMTP_TLS=true
export BRIGHTLOOP_SMTP_SSL=false
export BRIGHTLOOP_FROM_EMAIL=billing@example.com
export BRIGHTLOOP_PASSWORD_RESET_URL=https://app.example.com/reset-password
```

The SMTP connection also accepts standard Django email settings as fallbacks.
Transport failures emit a sanitized server warning and retain the generic
request response to avoid exposing account existence. Check the captured mail
or server log when diagnosing delivery. The frontend URL comes only from trusted
server configuration, never the request Host header. No real SMTP message is
sent during verification.

## Subscription actions

Use `POST /api/subscriptions/{id}/transition` with `{"action":"pause"}` (or
`resume`, `renew`, `close`). Render only the backend's `permitted_actions`, and
handle 400/403/404 on submission because state or permissions may have changed.

- Staff/admin retain quotation `quote` → `confirm` → `activate`; they can close
  draft/quotation/confirmed records. Customers cannot activate or close drafts.
- `pause` requires an active, unexpired subscription and `plan.allow_pause`.
  Outstanding periods through today are invoiced under the old terms before
  pausing. This never records payment automatically.
- `resume` requires an unexpired paused subscription. Cycles beginning before
  the resume date while paused are skipped; no paused-cycle invoices or
  proration are created. Resuming exactly on a cycle boundary permits that cycle
  to bill; resuming mid-cycle waits until the next original anchor boundary.
  Resume remains possible if the plan's pause flag was disabled after pausing.
- `close` is cancellation. Activated subscriptions require `plan.allow_cancel`.
  Active arrears are billed first; existing invoices and payments are retained.
  Closed subscriptions are terminal and cannot be resumed or renewed.
- `renew` requires `plan.allow_renew` and a previously activated contract.
  Auto-close contracts cannot be renewed after expiry. Optional input:
  `{"action":"renew","expiry_date":"2027-12-31"}`. The new expiry must be
  later than both the current expiry and today. Without a date, expiry extends
  by one plan frequency from the later of current expiry and today.
- Early renewal preserves the original anchor unless a final partial period
  has already been billed to a mid-cycle expiry; its new term starts at that
  old expiry so no span overlaps and the new cursor has a valid anchor.
  Lapsed renewal bills remaining
  pre-expiry active periods, then begins a new term today, without billing the
  lapse. Paused renewals remain paused until resumed. Signup availability dates
  do not block lifecycle management of existing contracts.

Customers can manage only their own previously activated subscriptions. Plan
flags apply to staff/admin actions too. Invalid transitions change no state.
The returned subscription retains the shared contract shape, including lines,
next billing date, and actions appropriate to the current actor.

## Customer quantities and add-ons

`GET /api/subscriptions/{id}/addons` returns the standard paginated list of
active products, with `id`, `name`, `type`, `sale_price_paise`, and `variants`.
It enforces subscription ownership and omits cost prices/internal notes. General
catalog routes remain restricted to staff/admin.

`PATCH /api/subscriptions/{id}` for a customer accepts only a complete line
replacement on an active, unexpired subscription:

```json
{"lines":[{"product_id":1,"variant_id":1,"quantity":2},{"product_id":2,"quantity":1}]}
```

Omit a line to remove that add-on. Product and quantity are required on every
line; omit or set null for no variant. Quantities must be positive, variants must
belong to the product, products must be active, and total active quantity must
meet the plan minimum. Combine duplicate product/variant lines into one quantity.
Customers cannot set prices, taxes, active flags, customer, plan, or discounts.
Existing line combinations retain their negotiated effective price and tax;
new combinations use current product sale price plus the variant surcharge once.

Staff/admin may replace active lines using the existing line serializer,
including negotiated full prices and tax references. Other active-subscription
fields stay immutable; draft editing remains unchanged. Paused, expired, and
closed line changes are rejected.

The transaction first bills this subscription's outstanding periods through
**today using old lines** and then installs the replacement lines for the next
cycle. There is no proration or retroactive rewrite of invoice snapshots. If
billing fails partway through, newly generated invoices, discount usage, cursor
advancement, and all line/lifecycle changes roll back together. Existing or
cancelled invoice periods are never automatically billed again. The frontend
should refresh subscriptions, invoices, preview, and dashboard after mutation.

## Expiry and auto-close for GSK

Run `.venv/bin/python manage.py maintain_subscriptions` in the single-worker
billing/demo maintenance sequence. It catches up active pre-expiry periods,
then persists `expired` or `closed` according to `plan.auto_close`. Paused periods
are skipped, never billed. Each subscription is its own transaction; failures
are reported and that subscription's changes roll back. Reruns are idempotent.
An optional past/present `--as-of YYYY-MM-DD` controls contract processing;
future dates are rejected. Quotation expiry is evaluated at the current time.

Reads also reconcile already-settled or paused contract expiry without creating
invoices. An expired-by-date active record with unbilled historical cycles stays
available for catch-up until billing/maintenance settles it; no cycle at or
after exclusive expiry is billable. This preserves GSK's catch-up contract.
After ordinary billing runs, maintenance (or a subscription read when already
settled) finalizes the status. Dashboard-only requests do not run maintenance;
GSK should run the command in the billing/demo sequence before reporting expiry.

## Verification

Use the real apps and production root routes:

```bash
.venv/bin/python manage.py test aliar.tests yascn.tests gsk.tests
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```

The isolated `yascn.test_settings` suite skips lifecycle tests requiring finance;
use the shared suite for full billing/lifecycle confidence. The tests cover
real invoice persistence and snapshots, not just mocked billing responses.
