# YASCN — identity, catalog, and subscriptions backend

## Current handoff

- Core identity, catalog, quotation, subscription lifecycle, password reset, and next-cycle edit APIs are available. The new catalog forms exercise variant, tax, discount, and template creation through your routes.
- Gauthami has connected password reset and customer add-on/quantity screens. Next: join the full browser rehearsal, resolve any API defects or permission gaps found in `yascn/`, and keep `yascn/yascnprogress.md` current. Recheck ownership and lifecycle tests after fixes.
- GSK owns final integration and the demo; communicate any contract change before making it.

**Read [CONTRACT.md](CONTRACT.md) first.** It is the source of truth for models, statuses, routes, response fields, and the billing cursor; tell GSK before changing an interface.

**Git sync:** `main` history changed to correct GDM's author name. Follow the [README sync steps](README.md#sync-after-the-author-name-correction) before pushing from an older clone; keep any unpushed work on the preserved branch until GSK helps replay it.

## What we are building

Brightloop is a subscription software company currently tracking customers, renewals, invoices, payments, and revenue by hand. We are building one local web app where an admin configures products and plans, staff manage quotations and billing, and customers manage their own subscriptions and view invoices. The stack is Django REST Framework, SQLite, and React/Vite; this is a working hackathon demo, not a collection of disconnected screens.

The shared demo story starts in YASCN's area: admin creates a product whose Odoo variant adds ₹560, sets a recurring plan, and uses a quotation template to create an active customer subscription. GSK's **Billing Control Tower** then previews and runs billing; ALIAR handles the resulting invoice, partial payment, and dashboard. Your models and permissions must give those later steps reliable data and prevent customers from seeing one another's records.

## Mission

Provide the accounts and catalog that the billing engine consumes. Own subscription creation and lifecycle rules; hand a stable data model and endpoints to GSK and GDM early.

## Directory and progress handoff

- Create `yascn/` and keep your Django app code, migrations, tests, and edits inside it. Do not edit `gsk/`, `gdm/`, `aliar/`, or root integration files; GSK handles integration.
- Create `yascn/yascnprogress.md`. After each checkpoint, record **done**, **next**, **blocked**, model/API changes, migration names, and the latest relevant test command/result.
- Give GSK import paths, app registration needs, endpoint routes, and the due-subscription query. If integration requires a change outside `yascn/`, describe it in your progress file for GSK to apply.

## Build

- Implement registration and login with case-insensitive unique email and passwords longer than eight characters containing uppercase, lowercase, and special characters. Add reset-token email delivery through configurable SMTP and a local captured-email mode.
- Define admin, staff, and customer authorization. Only admin may create staff or configure products, plans, taxes, and discounts. Customer queries must be filtered by owner.
- Implement products with name, type, sale price, cost price, notes, and variant surcharges such as Odoo +₹560. Implement plans with recurring base price, daily/weekly/monthly/yearly frequency, minimum quantity, availability dates, and pause/renew/cancel/auto-close permissions.
- Implement configurable percentage taxes and discount rules: fixed or percentage, product or whole-subscription scope, minimum amount or quantity, start/end dates, and usage limit.
- Implement quotation templates with plan, lines, and validity days. Create numbered subscriptions with customer, plan, dates, payment terms, product/variant/add-on lines, and state transitions `draft → quotation → confirmed → active → closed`, plus `paused` and `expired` states.
- Customer add-on and quantity edits apply to the next billing cycle. Paused cycles are skipped; expiry stops billing pending renewal; auto-close plans close at expiry.

## API handoffs

Own the YASCN routes in [CONTRACT.md](CONTRACT.md). Provide GSK with a query for due active subscriptions and stable access to plan fee, lines, taxes, discounts, next billing date, and permissions. Define the custom User before the first migration and include `/api/auth/me` for UI refresh.

## Completion check

Prove a customer cannot read another customer's subscription, staff cannot create staff/admin rules, and an admin can create the seeded product, Odoo variant, plan, template, and active subscription. An invalid email duplicate or password is rejected. A quotation expires on its validity date.

## Phase 1 — models and core endpoints (hours 0–4)

- By 0:30, agree on schema and JSON examples with GSK and ALIAR. Prioritize the custom User, roles, one product/variant, plan, tax/discount, template, and active subscription needed for the seeded story.
- At the phase gate, migrations must work on a fresh database, Django checks must pass, and API tests must show admin setup, customer ownership, valid login, and one active subscription with correct lines. Fix contract mismatches before Phase 2.

## Phase 2 — lifecycle and integration (hours 4–8)

- Expose the subscription query GSK's billing service needs and complete quotation-to-active transitions by 6:00. Freeze core features then. Add password reset and remaining pause, renew, cancel, expiry, and next-cycle edit flows only after the integrated demo gate passes.
- Test password reset, quote expiry, invalid transitions, minimum quantity, and role restrictions. Repeat migrations and checks after integration; resolve blocking defects by 7:00.
- Support the final seeded demo and README in the last hour.
