# ALIAR — invoices, payments, and finance backend

**Read [CONTRACT.md](CONTRACT.md) first.** It is the source of truth for invoice fields, statuses, routes, response fields, and duplicate prevention; tell GSK before changing an interface.

## What we are building

Brightloop is a subscription software company currently tracking customers, renewals, invoices, payments, and revenue by hand. We are building one local web app where an admin configures products and plans, staff manage quotations and billing, and customers manage their own subscriptions and view invoices. The stack is Django REST Framework, SQLite, and React/Vite; this is a working hackathon demo, not a collection of disconnected screens.

The shared demo story begins with YASCN's product, plan, quotation, and active subscription. GSK's **Billing Control Tower** previews and generates an invoice exactly once. ALIAR's area then confirms it, records a partial payment, shows the remaining and overdue balance, and updates the finance dashboard and customer portal. These numbers must agree across every screen; the Control Tower is the standout feature because it makes billing outcomes visible before and after the run.

## Mission

Make generated invoices actionable and show what Brightloop has collected and what it is still owed. Coordinate the invoice schema with GSK before either of you implements it.

## Directory and progress handoff

- Create `aliar/` and keep your Django app code, migrations, tests, and edits inside it. Do not edit `gsk/`, `gdm/`, `yascn/`, or root integration files; GSK handles integration.
- Create `aliar/aliarprogress.md`. After each checkpoint, record **done**, **next**, **blocked**, invoice/API contract changes, migration names, and the latest relevant test command/result.
- Give GSK import paths, app registration needs, endpoint routes, and the invoice creation interface. If integration requires a change outside `aliar/`, describe it in your progress file for GSK to apply.

## Build

- Own invoice and payment models. Invoice stores customer/subscription reference, period and revision constraints from the contract, issue/due dates, immutable line and calculation snapshots, subtotal/discount/tax/total in paise, and state.
- Expose staff actions to confirm, cancel, send, print, and explicitly reissue a cancelled invoice. Preserve cancelled records; at most one non-cancelled invoice may exist for a subscription period.
- Record multiple payments against an invoice with method, amount, date, and note. Reject nonpositive or over-balance payments. Derive `balance_paise`; set `paid` only when balance reaches zero.
- Show outstanding and overdue invoices using due date and remaining balance. A cancelled invoice is excluded from revenue and balances.
- Implement `GET /api/dashboard` with the contract's date filters and metrics, including gross MRR from GSK's shared calculation. Use indexed, paginated queries rather than loading every record into Python.
- Provide seed data for one clear demonstration story and enough generated records for a basic performance check. Add targeted tests for partial payments, overdue status, invoice actions, and customer ownership.

## API handoffs

Own the ALIAR routes in [CONTRACT.md](CONTRACT.md). GSK alone owns pricing and invoice generation; provide the invoice creation interface and schema to GSK by 0:30. Base reporting on saved invoice and payment amounts.

## Completion check

One invoice can receive two partial payments and show the correct remaining balance after each; it becomes paid only after settlement. An unpaid invoice becomes overdue after its due date. Customer A cannot see customer B's invoice. Repeated billing cannot create a second active invoice for the same subscription period.

## Phase 1 — invoice and payment foundation (hours 0–4)

- By 0:30, agree on the invoice schema and creation interface with GSK. Prioritize invoice/payment models, migrations, list/detail/confirm, partial payments, derived balances, and a basic dashboard response.
- At the phase gate, fresh migrations and Django checks must pass. Test a manually created invoice receiving two partial payments, a customer ownership check, and the unique active invoice-per-period rule. Fix schema and response mismatches before Phase 2.

## Phase 2 — generated invoices and reporting (hours 4–8)

- Provide the invoice creation interface GSK can call and complete payments and dashboard totals inside `aliar/` by 6:00. Freeze core features then. Add send, cancel/reissue refinements, print support, and broader report filters only after the integrated demo gate passes.
- Verify cancellation/reissue, overdue balances, report filters, and a seeded performance check. Repeat the Phase 1 tests after integration and resolve blocking defects by 7:00.
- Prepare demo data and support the final walkthrough in the last hour.
