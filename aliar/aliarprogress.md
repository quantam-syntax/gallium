# ALIAR progress

## Done

- Reviewed the repository, `aliar.md`, the shared contract, and the updated README Git-sync instructions. Fetched teammate changes, preserved the old branch as `main-before-aliar-sync-20261031`, and based this delivery on corrected remote history. No force push or teammate commit rewriting.
- Implemented Invoice and Payment models, immutable snapshots, integer-paise constraints, unique period/revision constraints, and one non-cancelled invoice per period. All implementation changes remain inside `aliar/`.
- Implemented authenticated, ownership-filtered, paginated invoice/payment APIs; staff/admin confirm, cancel, send, reissue, and payments; derived balances, overdue/partial flags, and zero-total settlement. Cancelled invoices expose zero remaining balance and are excluded from reports.
- Implemented atomic invoice creation, discount consumption, and cursor advancement. Exposed `aliar.services.create_for_candidate` for GSK. Subscription state, period boundaries, future billing, and snapshot consistency are rechecked. Automatic reruns skip cancelled revisions too.
- Implemented SQL dashboard totals, inclusive date filters, and current gross MRR with GSK's shared frequency calculation and per-subscription rounding. Reporting uses saved money amounts and does not load the ledger into Python.
- Added an idempotent demo/performance seed command based on an existing GSK invoice, creating tagged historical fixtures including one overdue invoice with two partial payments. It preserves the source, real billing cursor, and discount usage.
- Replaced temporary YASCN fixtures with the real custom User and production subscription/catalog models. No substitute model apps remain.
- Added the backend phase-gate walkthrough: actual login tokens, Odoo product variant, plan/template, quotation transitions, GSK preview/run, confirmation, two partial payments, overdue dashboard, customer ownership, settlement, and a second no-op billing run. Only the pending repository selection is patched; the bridge delegates to the real `yascn.billing.due_candidates`, GSK pricing/orchestration, and ALIAR persistence. A catch-up test also verifies two historical periods ending at exclusive expiry with one-use discount consumption exactly once.
- Documented routes, registration, migration dependency, demo commands, email behavior, and GDM's print handoff in `aliar/README.md`. Added scoped Ruff formatting/lint configuration.

## Next

- GDM connects its in-memory UI to the production APIs, restricts payment recording to staff/admin, and builds the individual invoice print view from `snapshot.lines`.
- Repeat the full browser walkthrough after GDM integration, checking that balances agree after refresh and that a second billing run creates no invoice.

## Blocked / remaining shared work

- GSK's production repository and root URL wiring are complete. The unpatched backend API works and ALIAR's post-integration regression now covers the finance actions.
- GDM's UI still uses mock/local state. Browser persistence, API-backed dashboard/payment agreement, and individual invoice printing remain GDM/GSK tasks.

## Invoice/API contract changes

- None. Routes, statuses, and money units follow the shared contract. Invoice detail also exposes full period/revision/breakdown fields and `is_partially_paid`.
- Clarifications: partially paid invoices cannot be cancelled without refunds; zero-total invoices become paid on confirmation; cancelled remaining balances are zero; reissue copies pricing without another discount use. Email transport failures return 503 and leave `sent_at` unchanged.
- Imports: `aliar.models.Invoice`, `aliar.models.Payment`, `aliar.services.create_for_candidate`, `aliar.urls`. Full handoff: `aliar/README.md`.

## Migrations

- Production: `aliar/migrations/0001_initial.py`, depends on actual `yascn.0001_initial` and the swappable User. Applied successfully on a fresh SQLite database with real YASCN migrations.
- No migrations/models in another owner's directory were modified.

## Verification

- Phase 1 foundation: fresh migrations, Django checks, manually created invoice receiving partial payments, customer ownership, and unique active-period checks passed.
- Original combined gate after syncing YASCN's billing handoff (`d042a31`): 76 tests passed on a fresh migrated database.
- After GSK production integration (`554e697`) and YASCN lifecycle/password-reset delivery (`7003047`), `aliar/.venv/Scripts/python.exe manage.py test aliar.tests yascn.tests gsk.tests --verbosity 1`: **109 tests passed** against production settings and routes on a fresh database, including the new post-integration ALIAR regression.
- New post-integration finance regression: `aliar/.venv/Scripts/python.exe manage.py test aliar.tests.test_production_phase2 --verbosity 1`: passed, covering actual billing → cancel → no duplicate → reissue → two partial payments → filtered and overdue reporting → customer visibility.
- `manage.py migrate --noinput --settings=aliar.test_settings`: all migrations applied to a fresh in-memory database, including YASCN and ALIAR initial migrations.
- `manage.py check` with production settings: passed, zero issues.
- `manage.py makemigrations --check --dry-run` with production settings: passed, no changes detected.
- `aliar/.venv/Scripts/ruff.exe check aliar` and `ruff.exe format --check aliar`: passed; 21 Python files formatted. Scope is ALIAR only.
- Performance: 1,001 invoices; a 25-row invoice page uses two SQL queries and the dashboard uses four, excluding token authentication. Multiple payment rows do not multiply invoice totals.
- `npm ci --cache C:\Users\AdilN\Documents\.npm-cache --no-audit --no-fund` in `gdm/`: passed. Default cache access is restricted here.
- `npm run build -- --configLoader runner` in `gdm/`: passed. Plain build hits an environment-specific esbuild parent-directory permission error; runner mode avoids it without changing frontend config.
