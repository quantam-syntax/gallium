# YASCN — identity, catalog, and subscriptions backend

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

Own `/api/auth/*`, `/api/products`, `/api/plans`, `/api/taxes`, `/api/discounts`, `/api/templates`, and `/api/subscriptions`. Provide GSK with a query for due active subscriptions and a stable way to read current plan fee, lines, taxes, discounts, next billing date, and lifecycle permissions. Follow GSK's shared JSON, money, date, and status contract.

## Completion check

Prove a customer cannot read another customer's subscription, staff cannot create staff/admin rules, and an admin can create the seeded product, Odoo variant, plan, template, and active subscription. An invalid email duplicate or password is rejected. A quotation expires on its validity date.

## Phase 1 — models and core endpoints (hours 0–4)

- By 0:30, agree on schema and JSON examples with GSK and ALIAR. Deliver accounts, roles, catalog, plan, template, and subscription models plus the endpoints needed for the seeded story.
- At the phase gate, migrations must work on a fresh database, Django checks must pass, and API tests must show admin setup, customer ownership, valid login, and one active subscription with correct lines. Fix contract mismatches before Phase 2.

## Phase 2 — lifecycle and integration (hours 4–8)

- Expose the subscription query GSK's billing service needs and finish permitted pause, renew, cancel, expiry, and next-cycle edits inside `yascn/` by 6:00. Freeze new features then.
- Test password reset, quote expiry, invalid transitions, minimum quantity, and role restrictions. Repeat migrations and checks after integration; resolve blocking defects by 7:00.
- Support the final seeded demo and README in the last hour.
