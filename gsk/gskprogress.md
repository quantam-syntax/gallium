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

## Next

- Hand Gauthami the live API and seeded demo so she can replace local UI state
  with authenticated requests and a saved-snapshot invoice print view.
- Let Yazeen begin password reset and the deferred lifecycle flows now that
  the integrated backend gate passes. Ali owns any finance defects found.
- Rehearse the full browser path after GDM connects the API; prepare the final
  demo and delivery once that path works after refresh.

## Blocked

- GDM's Billing Control Tower and portal still hold data in React memory.
  Browser authentication, API reads/writes, refresh persistence, and invoice
  printing remain the final integration gap.

## Contract changes

- None; implementation follows `CONTRACT.md`.

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
