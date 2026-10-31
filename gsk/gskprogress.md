# GSK progress

## Done

- Agreed shared model, route, and billing contract in `CONTRACT.md`.
- Created Django project skeleton, billing calculation and orchestration code, and preview/run endpoint shells.
- Verified month-end cycles, discount and tax totals, catch-up, duplicate-run behavior, discount usage limits, and bad-cursor reporting with six independent tests.
- Added isolated Django settings and five HTTP tests covering authentication, roles, date validation, missing integration, response totals, and repeated billing runs.
- Registered YASCN's URL module in shared routing and kept GSK's isolated API tests on billing-only test URLs.
- Fixed the YASCN due-query handoff so active subscriptions with missed pre-expiry periods remain billable after their expiry date.
- Restricted YASCN catalog reads to staff/admin so customers cannot inspect internal cost prices or discount rules.
- Earlier review confirmed YASCN's 23 tests and GDM's starter build before
  their full handoffs arrived.
- Pulled GDM's full demo UI, YASCN's billing handoff, and ALIAR's finance app.
  Reviewed the frontend at desktop and mobile widths, improved its visual
  hierarchy and data consistency, and verified the browser demo's second
  billing run creates no additional invoice.
- Connected YASCN's due-candidate mapper and ALIAR's atomic invoice creation in
  the production repository. Mounted ALIAR's API routes in the root URL config.
- Migrated and seeded a local demo database. The unpatched production API path
  creates an invoice matching the ₹1,840.80 preview, records a ₹500.00 partial
  payment, reports ₹1,340.80 outstanding, and creates nothing on a second run.
- Added a production-settings regression test covering the same path and
  customer access controls. The combined suite now passes 77 tests.
- Applied YASCN migration `0002` locally and ran the live browser flow with
  admin login, quotation creation, confirmation/activation, ₹1,840.80 preview,
  billing, saved-snapshot print view, ₹500 payment, refresh, second no-op run,
  and customer portal. Added a staff Confirm action for draft invoices discovered
  during the walkthrough; payment is now offered only after confirmation.
- Updated the shared contract for reset/lifecycle/add-on routes and ran
  `maintain_subscriptions` locally (zero contracts expired).

## Next

- Ask Gauthami to connect reset-password and customer add-on/quantity screens
  to Yazeen's completed APIs, and finish any invoice send/cancel/reissue UI.
- Rehearse the browser flow with a newly due subscription and capture the final
  demo/video. Keep the seeded database intact; never rewind a billed cursor.
- Rehearse the full browser story once more on the final demo environment and
  record the video/submission. Keep the confirmed local demo records intact.

## Blocked

- Core staff billing and customer portal paths use the API and pass a live
  browser walkthrough. Reset/add-on screens remain pending with Gauthami.

## Contract changes

- Documented YASCN's already implemented reset, lifecycle, and add-on routes;
  no backend wire shape changed in GSK.

## Verification

- Billing calculation tests: 6 passed within the current 11-test Django suite.
- `python3 -m compileall -q gsk manage.py` and `git diff --check`: passed.
- `.venv/bin/python manage.py check`: passed after both teammate apps arrived.
- `.venv/bin/python manage.py makemigrations --check --dry-run`: no changes detected.
- Isolated Django system check with teammate apps omitted: passed, 0 issues.
- `.venv/bin/python manage.py test gsk.tests --settings=gsk.test_settings`: 11 tests passed.
- `.venv/bin/python manage.py check --settings=gsk.test_settings`: passed, 0 issues.
- `.venv/bin/python manage.py test yascn --settings=yascn.test_settings`: 23 tests passed after catch-up and customer catalog access fixes.
- `cd gdm && npm ci && npm run build`: passed.
- `.venv/bin/python manage.py test aliar.tests yascn.tests gsk.tests`: 77 passed with production settings and root URLs.
- `.venv/bin/python manage.py test gsk.tests --settings=gsk.test_settings`: 11 passed; the production-only test was skipped.
- Local database: production migrations and seeded API walkthrough passed; first
  run created one invoice, second created none, and customer finance access was
  restricted.
- `cd gdm && npm run build`: passed after the visual review.
- Latest combined backend suite: 109 tests passed; production migration and
  Django checks passed. Live browser flow persisted payment after refresh and
  created zero invoices on the second run.
- With 1,003 invoices in a temporary local benchmark, dashboard API requests
  took about 4 ms after warmup, a 25-row invoice page about 4 ms, and all 41
  invoice pages about 186 ms in the Django test client.
- A temporary database with 1,003 subscriptions and 1,004 invoices loaded the
  authenticated browser overview in 733 ms, displayed the subscription table
  in 1,237 ms, and displayed the invoice table in 1,687 ms total from navigation
  start in local headless Chromium. No API errors appeared. The original demo
  database was restored after both benchmarks; production latency may differ.
- A focused live browser check confirmed a real draft invoice through the new
  UI button; the row changed to confirmed and then offered Record payment.
- Latest `npm run build`: passed after the invoice action change. Latest full
  production test suite: 109 passed; system and migration checks passed.
