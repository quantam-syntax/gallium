# GSK progress

## Done

- Agreed shared model, route, and billing contract in `CONTRACT.md`.
- Created Django project skeleton, billing calculation and orchestration code, and preview/run endpoint shells.
- Verified month-end cycles, discount and tax totals, catch-up, duplicate-run behavior, discount usage limits, and bad-cursor reporting with six independent tests.
- Added isolated Django settings and five HTTP tests covering authentication, roles, date validation, missing integration, response totals, and repeated billing runs.
- Registered YASCN's URL module in shared routing and kept GSK's isolated API tests on billing-only test URLs.
- Fixed the YASCN due-query handoff so active subscriptions with missed pre-expiry periods remain billable after their expiry date.
- Restricted YASCN catalog reads to staff/admin so customers cannot inspect internal cost prices or discount rules.
- Reviewed the pulled UI and YASCN code: YASCN's 23 tests pass; GDM's starter builds after `npm ci`, but the demo screens are not yet implemented.

## Next

- Connect YASCN subscription models and ALIAR invoice creation service in `gsk/integration.py` to make the preview/run endpoints live.
- Register ALIAR's URL module and GDM's frontend after their handoffs arrive; YASCN routes are already registered.

## Blocked

- Production Django migrations and integrated API checks still require ALIAR's invoice app, which is not present yet. The GSK billing API is tested with a fake repository only.
- GDM's current UI is a welcome screen; the Billing Control Tower and customer portal remain GDM work.

## Contract changes

- None; implementation follows `CONTRACT.md`.

## Verification

- Billing calculation tests: 6 passed within the current 11-test Django suite.
- `python3 -m compileall -q gsk manage.py` and `git diff --check`: passed.
- `.venv/bin/python manage.py check`: blocked by missing `yascn` app (the integrated project deliberately names `yascn.User` before migrations).
- Isolated Django system check with teammate apps omitted: passed, 0 issues.
- `.venv/bin/python manage.py test gsk.tests --settings=gsk.test_settings`: 11 tests passed.
- `.venv/bin/python manage.py check --settings=gsk.test_settings`: passed, 0 issues.
- `.venv/bin/python manage.py test yascn --settings=yascn.test_settings`: 23 tests passed after catch-up and customer catalog access fixes.
- `cd gdm && npm ci && npm run build`: passed.
