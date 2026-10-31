# GSK progress

## Latest integration handoff

- Added an idempotent fictional showcase seed (25 products, 50 customers, 300 subscriptions) scoped away from the original demo cursor. Genuine billing invoices and payments populate finance views. Added staff-only product adoption analytics and catalog sparklines with growing/slowing summaries. The live local seed produced 528 invoices and 402 payments; a second run produced zero duplicates. Fixed nullable variant ID normalization exposed by the larger dataset. The full backend suite (111 tests), frontend build, and populated Chromium check pass; local overview loaded in 1.27 seconds with no JavaScript errors.
- Investigated the zero-amount billing report: the local fourth subscription was `confirmed`, while the three active subscriptions were already billed through 30 November. Made Confirm/Activate visible in Quotations and added `created_total_paise` to billing run output. Browser verification on a copied DB: activate → ₹1,840.80 preview → one ₹1,840.80 invoice → ₹0 remaining to bill; the original DB was untouched.
- Completed the staff payment form's date and note inputs and wrote `DEMO.md` with the exact recording path. A browser check against an isolated demo database saved ₹500 by UPI with a prior payment date and reference note; the API returned the same values. The final recording and submission remain with the team lead.
- Added `python manage.py run_billing [--as-of YYYY-MM-DD]`, calling the same idempotent billing service as the Control Tower. Schedule billing before `maintain_subscriptions` so final periods can be invoiced.
- Built and browser-verified the catalog admin forms with GDM's frontend. Updated each owner's root brief with current remaining work.
- Next: final seeded browser rehearsal, any teammate integration fixes, and demo recording/submission.
- Pulled Gauthami's UI contribution: password recovery, customer add-on editing, and invoice actions are present. Full backend suite, Django check/migration check, and Vite build pass. Fixed cancelled-invoice display and customer line styling found in review. Corrected shared author attribution to Gauthami; she must correct local Git config before her next commit.
- Added a staff-only paginated customer directory and connected it to the quotation selector, fixing the loss of newly registered customers after refresh.
- The isolated browser rehearsal found that the customer portal lacked plan/product names and omitted the plan fee from its displayed price. Added owner-scoped display names and recurring totals to subscription responses and connected the portal to them. Verified reset email/link, customer quantity edit, invoice cancel/reissue/confirm/send, and clean token state using a copied demo database; 110 backend tests and the frontend build pass.

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

- Rehearse the full browser story once on the final recording environment using a newly activated quotation. Capture the demo and submit the repository and video. Keep the seeded database intact; never rewind a billed cursor.

## Blocked

- No implementation blocker is known. Recording and submission remain team tasks.

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
