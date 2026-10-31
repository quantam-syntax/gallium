# YASCN progress

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
