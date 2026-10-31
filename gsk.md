# GSK — team lead and billing engine

## What we are building

Brightloop is a subscription software company currently tracking customers, renewals, invoices, payments, and revenue by hand. We are building one local web app where an admin configures products and plans, staff manage quotations and billing, and customers manage their own subscriptions and view invoices. The stack is Django REST Framework, SQLite, and React/Vite; this is a working hackathon demo, not a collection of disconnected screens.

Our judge-facing story is: create an Odoo product variant with a ₹560 surcharge, make a recurring plan and quotation, activate a customer's subscription, preview the next billing run, generate one accurate invoice, record a partial payment, and show the remaining balance in the customer portal and finance dashboard. The **Billing Control Tower** is the standout feature: it reveals what is due, expected revenue, and exceptions before billing, then shows exactly what the run created. GSK's engine makes that story correct and repeatable.

## Mission

Own the hardest path: turn an active subscription into one correct invoice for each due billing period. Integrate the four workstreams and deliver the repository and video within eight hours.

## Directory and progress handoff

- Work in `gsk/` for project configuration, shared API wiring, billing code, and integration. The other owners create and edit only their own directories: `gdm/`, `yascn/`, and `aliar/`.
- Create your separate progress file `gsk/gskprogress.md`. Ask each teammate to create `gdm/gdmprogress.md`, `yascn/yascnprogress.md`, or `aliar/aliarprogress.md` in their own directory. Each update should state **done**, **next**, **blocked**, changed API contracts, and a command/result proving the current work runs.
- You alone modify root integration files, connect Django apps and frontend to the runnable system, resolve cross-directory conflicts, and run the final end-to-end tests. Teammates provide code and handoff notes; they do not integrate one another's work.

## Build

- In the first 30 minutes, create the Django REST Framework project skeleton and a minimal React/Vite interface contract, agree on the API contract below, and provide mock JSON to GDM. GDM owns the actual frontend in `gdm/`.
- Implement `GET /api/billing/preview` and `POST /api/billing/run`. Preview shows due subscriptions, expected invoice totals, and actionable exceptions; run creates invoices and returns created/skipped/error counts.
- Put preview and run on the same calculation service. Invoice the plan base fee plus product, variant, and add-on lines. Use integer paise, apply the best eligible product discount **or** whole-subscription discount, then calculate percentage tax on the discounted amount.
- Make billing idempotent with a unique subscription-and-period key. Catch up missed periods; skip paused or expired cycles. Save invoice line, tax, and discount snapshots.
- Expose a scheduled management command using the same billing service. A UI button may call the run endpoint for the demo.
- Integrate YASCN's subscription data and ALIAR's invoice model. Resolve interface mismatches, run the end-to-end smoke test, seed the demonstration story, record the video, and submit the single-branch repository.

## Shared contract to lock at 0:30

- JSON endpoints live under `/api`; authentication uses a token returned by `/api/auth/login` and sent as `Authorization: Token <token>`.
- Money is integer paise in storage and API responses; the UI formats INR. Dates are ISO `YYYY-MM-DD`; timestamps include a timezone.
- Subscription states: `draft`, `quotation`, `confirmed`, `active`, `paused`, `expired`, `closed`. Invoice states: `draft`, `confirmed`, `paid`, `cancelled`; a partially paid confirmed invoice retains `confirmed` status and exposes `balance_paise`.
- Standard list responses: `{ "results": [...], "count": 0, "next": null, "previous": null }`. Errors: `{ "detail": "..." }` or field-specific validation errors.
- Brightloop is one business. Customers see only their own records. Admin owns catalog and discount configuration; staff handle quotations, subscriptions, invoices, and payments.

## Completion check

Run billing twice against the same due subscription: the first run creates one invoice, the second creates none. Show plan fee, variant surcharge, discount, tax, and remaining balance correctly. Run a missed-period catch-up case. Confirm the Control Tower preview matches the created invoice.

## Phase 1 — foundation and contract (hours 0–4)

- By 0:30, scaffold both apps and freeze model ownership, endpoint paths, JSON examples, status values, and the invoice creation interface with all three teammates.
- Build billing calculations and preview against seed data. Add the subscription-and-period uniqueness constraint before implementing the run action.
- Run the phase gate with the team: fresh database migration, Django system check, API login and ownership smoke tests, preview calculation against a known expected total, and React build. Record any failing check in one shared issue list and fix it before Phase 2.

## Phase 2 — integration and core verification (hours 4–6)

- Connect preview and run to the real subscription and invoice models. Integrate the UI by 6:00.
- Verify the seeded path from login through payment and dashboard. Run billing twice, test a missed period, and confirm invoice totals match the preview. Repeat all Phase 1 checks after integration.
- Do not start Phase 3 while any core flow or billing check is failing.

## Phase 3 — optional AI collections assistant and delivery (hours 6–8)

- If Phase 2 passes by 6:00, add a staff-only **Draft follow-up** action for an overdue invoice. Give a configurable LLM only the invoice's customer name, due date, outstanding balance, and payment history; request a polite email draft grounded in those facts.
- Show the draft for staff review and editing. Never send it automatically, invent payment facts, or expose another customer's data. If no API key is configured or generation fails, show a clear unavailable message and keep the ordinary manual follow-up workflow usable.
- Stop feature work by 7:00. Use the final hour for defect fixes, local setup instructions, demo rehearsal, video, and single-branch submission. If the core flow is late, skip the assistant entirely and finish the billing demo.
