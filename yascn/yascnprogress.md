# YASCN progress

## Latest integration handoff

- Added `GET /api/customers` for authenticated admin/staff users. It returns only active customer accounts using the standard paginated user shape; customer role receives 403. A targeted test confirms a newly registered customer remains discoverable for quotations after a fresh request. GSK connected this route to the UI and ran the full suite.

## Checkpoint 1 — Phase 1 foundation

**Done:** Read every project source and workstream brief. Implemented the custom
email User, roles, catalog/tax/discount/template/subscription models and initial
migration. Added token login, registration, `/auth/me`, paginated CRUD, ownership
filtering, effective line prices, and quotation → confirmed → active transitions.
Quotation expiry is persisted lazily on subscription reads and transition attempts.

**Next:** Finish malformed draft-edit checks, repeatable demo data, API examples,
and fresh SQLite migration/system-check verification.

**Blocked:** Shared settings reference the absent `aliar` app. Shared routes do
not yet include `yascn.urls`. GSK owns those edits; no other owner's files changed.
YASCN checks run using `yascn.test_settings`, which omits ALIAR and mounts our URLs.

**Model/API changes:** No shared contract changes. All contract models now exist
in `yascn.models`. Nested product variants and template/subscription lines are
supported; core subscription actions are `quote`, `confirm`, and `activate`.

**Migration:** `yascn/migrations/0001_initial.py`; defines `User` before any app
refers to it. Database constraints include `Lower(email)` uniqueness.

**Verification:** `.venv/bin/python manage.py test yascn
--settings=yascn.test_settings -v 2`: 18 tests passed, system check: 0 issues.

## Checkpoint 2 — Phase 1 delivered

**Done:** Finished the models/core endpoints gate within YASCN's ownership.
Added malformed nested-line validation, draft date/cursor consistency,
admin/staff/customer authorization tests, quotation validity boundary tests,
template snapshot tests, and the repeatable `seed_yascn_demo` command. The demo
creates an active subscription with effective Odoo price 56000 paise, plan fee
100000, and GST 18%; the GSK pricing function returns total **184080 paise**.
The seed command never rewinds an existing billing cursor or changes passwords
on existing accounts. No Phase 2-only lifecycle/customer mutations are exposed.

**Next:** GSK applies the integration steps in `yascn/HANDOFF.md` after ALIAR is
delivered, repeats the checks with shared settings, and connects billing/invoice
creation. Only after the integrated demo gate passes: password reset/SMTP,
pause/resume/renew/close, expiry/auto-close maintenance, and next-cycle edits.

**Blocked:** The shared Django project still fails startup with
`ModuleNotFoundError: No module named 'aliar'`. `gsk/urls.py` also still needs
`path("api/", include("yascn.urls"))`. These files belong to GSK. Full project,
frontend, billing-run, payment, and dashboard gates are not claimed as passed.

**Model/API changes:** No changes to `CONTRACT.md`. Import paths, full route
table, JSON examples, permissions, line-price rules, expiry behavior, and exact
integration requirements are in `yascn/HANDOFF.md`. The read-only ORM handoff is
`yascn.services.due_subscriptions(as_of)`; GSK owns transactional billing writes.

**Migrations:** `0001_initial` is the only YASCN migration. Fresh SQLite migration
tested both by Django's test runner and against a separate temporary on-disk DB.

**Latest verification:**

- `.venv/bin/python manage.py test yascn --settings=yascn.test_settings -v 2`:
  **22 tests passed**; system check 0 issues.
- `.venv/bin/python manage.py check --settings=yascn.test_settings`: passed.
- `.venv/bin/python manage.py makemigrations yascn --check --dry-run
  --settings=yascn.test_settings`: no changes detected.
- `YASCN_DB_PATH=<fresh temporary SQLite file> .venv/bin/python manage.py migrate
  --noinput --settings=yascn.test_settings`: all migrations passed; subsequent
  system check passed. Temporary DB removed after verification.
- `.venv/bin/python -m unittest discover -s gsk/tests -v`: **6 tests passed**.
- `git diff --check`: passed. Existing tracked project files remain unchanged;
  delivered changes are under `yascn/` only (dependencies installed in ignored
  `.venv/`).
- `.venv/bin/python manage.py check`: blocked by the missing ALIAR app, as above.

## GSK integration review

- Corrected `due_subscriptions(as_of)` to include missed pre-expiry cycles even when the contract has now expired; GSK's period calculator stops at exclusive expiry.
- Restricted catalog reads to staff/admin so customer accounts cannot read product cost prices or discount rules. Added a regression test.
- Latest YASCN suite: **23 tests passed**. Shared URLs now include `yascn.urls`; ALIAR is still needed for the full Django app.

## Checkpoint 3 — Phase 2 core integration handoff

**Done:** Synced `97f4fa9`, including GDM's dashboard implementation. Delivered
`yascn.billing.due_candidates(as_of)`, returning GSK's exact `BillingCandidate`
shape from real YASCN models. It maps active effective-price lines, plan fees,
active tax rates, product rules, and the assigned whole-subscription discount.
Period-specific discount eligibility stays with GSK. Historical prices and
pre-expiry catch-up periods are preserved, including after plan signup
availability ends. Mapping uses three queries for both 1 and 13 subscriptions.

Added fourteen regression/integration tests: database-backed preview, shared
HTTP routing with token authentication/role checks, quotation-to-active-to-preview,
variant pricing without double counting, inactive/missing taxes, discount
selection and projected usage, skipped states, month-end catch-up, historical
catalog prices, and bounded query counts. Preview consumes no discount usage and
never advances `next_bill_date`. HTTP tests provide a read repository and assume
no existing invoices; they do not replace ALIAR's persistence or prove reruns.

Hardened core transitions by locking/reloading current state inside the service,
including non-HTTP calls. Updated the seed command to use its returned instance.
Expired draft template validity now blocks `quote` instead of advertising an
action that would immediately expire. Updated `HANDOFF.md` with exact mapper
imports and the current integration state.

**Next:** GSK delegates its repository read method to
`yascn.billing.due_candidates`, connects ALIAR's invoice creation/existence checks,
and verifies invoice/payment/dashboard plus second-run idempotency. GDM replaces
local demo state with authenticated backend calls. Once the integrated gate
passes, implement the remaining YASCN lifecycle and password reset flows.

**Blocked:** `gsk.integration.get_repository()` still raises `IntegrationPending`.
`aliar/` contains only a contribution note, with no invoice/payment implementation.
The frontend now has dashboard screens but still uses in-memory demo data.
The full integrated demo gate has **not** passed. Per `yascn.md`, password reset,
pause/resume/renew/close, expiry/auto-close, and next-cycle edits remain deferred.
No code outside YASCN was edited for this checkpoint.

**Model/API changes:** No shared contract or HTTP route changes. Added a Python
read adapter and strengthened existing transition validation. `transition`
returns a fresh locked model instance; callers should retain its return value.
**Migrations:** No schema changes; `0001_initial` remains the only migration.

**Latest verification:**

- `.venv/bin/python manage.py test yascn --settings=yascn.test_settings`:
  **37 tests passed**; system check 0 issues.
- `.venv/bin/python manage.py test yascn gsk.tests --noinput`:
  **48 tests passed with shared settings**; system check 0 issues.
- Fresh temporary on-disk SQLite database using `gsk.settings`: all migrations,
  `check`, and empty ORM candidate mapping passed; database removed afterward.
- `makemigrations yascn --check --dry-run` with shared and isolated settings:
  no changes detected.
- `cd gdm && npm run build`: passed on the newly synced dashboard source.
- `git diff --check`: passed.

The earlier missing-app startup error is resolved by the ALIAR namespace
directory: shared checks and migrations now pass, but that does not establish
that any invoice/payment functionality exists.

## Checkpoint 4 — ALIAR compatibility verified; awaiting GSK

**Done:** Synced ALIAR's `dc60886` delivery. Verified its invoice/payment models,
creation service, reporting, and test bridge against YASCN's real models and
`yascn.billing.due_candidates`. The combined suite covers login, active
subscription, pricing/preview, real invoice creation, two partial payments,
dashboard/ownership checks, settlement, catch-up, and a second no-op billing run.
No YASCN compatibility code changes were needed. Updated the integration handoff
to reflect the delivered finance backend and exact remaining wiring steps.

**Next:** Resume after GSK connects `gsk/integration.py` and registers
`aliar.urls` in shared URLs. Then repeat the production/backend and browser demo
gate before implementing the deferred YASCN lifecycle/password-reset work.

**Blocked:** Production repository selection still raises `IntegrationPending`,
and root URLs still omit ALIAR. Combined tests supply the repository selection
and test URL wiring; they do not prove the production or browser gate. Further
YASCN feature work is paused at the user's request until GSK's part arrives.

**Model/API changes:** None. ALIAR's `create_for_candidate` owns invoice creation,
discount consumption, and cursor advancement. GSK must not duplicate those
writes; its invoice-existence query must include cancelled revisions.
**Migrations:** No new YASCN migration; `0001_initial` remains current.

**Latest verification:**

- `.venv/bin/python manage.py test aliar.tests yascn.tests gsk.tests
  --settings=aliar.test_settings --verbosity 1`: **76 tests passed**, system check
  0 issues, including fresh test-database migrations with both real apps.
- `.venv/bin/python manage.py check`: passed with shared settings, 0 issues.
- `.venv/bin/python manage.py makemigrations --check --dry-run`: no changes.
- Documentation checkpoint: `git diff --check` passed; implementation remains
  unchanged after the verified `dc60886` sync.

## Checkpoint 5 — Deferred lifecycle and password reset delivered

**Done:** Synced GSK's `554e697` production repository/routes and received the
user's authorization to proceed after the backend gate. Implemented password
reset request/confirm, plan-controlled pause/resume/renew/close, customer-safe
add-on choices, transactional next-cycle line replacement, and expiry/auto-close
maintenance. Changes remain inside `yascn/`.

Password reset uses Django's expiring password-bound tokens, identical public
responses for absent/inactive/undeliverable accounts, IP throttles, configured
SMTP or captured email, atomic password writes, and revocation of existing DRF
tokens. Weak passwords, malformed/expired/reused links, and disabled users are
rejected. Tests do not send real SMTP messages.

Lifecycle operations lock the subscription and use the real GSK/ALIAR production
bridge to settle old periods before pause, close, renew, or line replacement.
Failed catch-up rolls back invoices, discount usage, cursor, and requested edits.
Paused periods are skipped on resume; resumed exact boundaries remain billable.
Lapsed renewal starts a new anchor without billing the gap; a previously billed
partial final period continues at its old expiry, preserving a valid schedule.
Existing/negotiated prices survive customer quantity changes, new add-ons use
current sale price plus surcharge once, and customer prices/taxes are rejected.

**Next:** Gauthami connects reset and lifecycle UI to the documented payloads,
clears saved auth after password reset, uses backend `permitted_actions`, and
refreshes subscriptions/invoices/preview/dashboard after mutations. GSK adds
these route/payload details to the shared contract and runs
`manage.py maintain_subscriptions` in the single-worker billing/demo sequence
before expiry-sensitive dashboard reporting. Perform the final browser demo
through authenticated APIs after UI integration.

**Blocked:** No YASCN backend implementation blocker remains. The browser demo
and reset screen still require GDM's API/UI work. SMTP delivery requires the
operator's configured host/credentials; local capture works without them.

**Model/API changes:** Added internal `Subscription.activated_at` to distinguish
expired quotations from expired previously active contracts. All existing
response fields/routes remain. Added `/api/auth/password-reset/request`,
`/api/auth/password-reset/confirm`, and ownership-filtered
`GET /api/subscriptions/{id}/addons`. Existing transition accepts all contract
lifecycle actions plus optional renewal `expiry_date`. Customers may PATCH only
active line choices/quantities. Exact GSK/GDM handoff is `yascn/LIFECYCLE.md`;
root README/shared contract edits remain with GSK.

**Migrations:** `0002_subscription_activated_at`, with a marker backfill for
existing active/paused/closed contracts. Quotes remain unmarked. Applied to the
local database; fresh and existing-0001 upgrade paths passed separately.

**Verification:**

- `.venv/bin/python manage.py test aliar.tests yascn.tests gsk.tests --verbosity 1`:
  **108 tests passed with production settings and shared root URLs**, 0 check issues.
- Focused reset/lifecycle suite using real ALIAR models: **31 tests passed**.
- Fresh temporary SQLite database upgraded from `yascn.0001_initial` with seeded
  old active/paused/quotation rows: migrations passed, active markers backfilled,
  quotations unmarked, Django checks passed, no migration drift.
- `.venv/bin/python manage.py migrate --noinput`: all local migrations applied.
- `.venv/bin/python manage.py check`: passed, 0 issues.
- `.venv/bin/python manage.py makemigrations --check --dry-run`: no changes.
- `git diff --check`: passed.
