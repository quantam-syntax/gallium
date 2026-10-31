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
- The combined ALIAR, YASCN, and GSK isolated test suite passes: 76 tests.

## Next

- Connect `yascn.billing.due_candidates` and ALIAR's invoice creation service
  in `gsk/integration.py` to make production preview/run endpoints live.
- Register `aliar.urls` in `gsk/urls.py`, then connect GDM's in-memory UI to
  authenticated APIs and the saved invoice snapshot/print view.

## Blocked

- ALIAR and YASCN handoffs are now present. The production repository adapter
  still raises `IntegrationPending`, and root URLs do not expose ALIAR routes.
- GDM's Billing Control Tower and portal are polished demos but still hold data
  in React memory. Authentication, API reads/writes, and persistence are next.

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
- `.venv/bin/python manage.py test aliar.tests yascn.tests gsk.tests --settings=aliar.test_settings`: 76 passed.
- `cd gdm && npm run build`: passed after the visual review.
