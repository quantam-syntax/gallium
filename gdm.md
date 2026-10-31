# GDM — UI and customer experience

## What we are building

Brightloop is a subscription software company currently tracking customers, renewals, invoices, payments, and revenue by hand. We are building one local web app where an admin configures products and plans, staff manage quotations and billing, and customers manage their own subscriptions and view invoices. The stack is Django REST Framework, SQLite, and React/Vite; this is a working hackathon demo, not a collection of disconnected screens.

The judge should be able to follow one customer story through the UI: an Odoo product variant adds ₹560, a recurring plan becomes a quotation and active subscription, the **Billing Control Tower** previews the upcoming invoice, staff run billing and record a partial payment, and the customer and finance views show the resulting balance. Make the Control Tower the visual centerpiece because it explains how Brightloop prevents missed or duplicate billing. GDM owns the clarity and usability of that story; the backend supplies all financial calculations.

## Mission

Build a polished React/Vite interface that tells the Brightloop story clearly. Use Antigravity for implementation, but keep generated code in the agreed frontend directory and commit only working changes.

## Directory and progress handoff

- Create `gdm/` and keep all UI source, assets, frontend configuration, and your edits inside it. Do not edit `gsk/`, `yascn/`, `aliar/`, or root integration files; GSK handles integration.
- Create `gdm/gdmprogress.md`. After each checkpoint, record **done**, **next**, **blocked**, API response mismatches, and the latest `npm run build` result. Put the exact UI start/build commands there for GSK.
- Hand GSK a buildable frontend and its expected API contract. You may connect real endpoints from within `gdm/`, but ask GSK to change backend contracts or shared configuration.

## Build

- Create responsive layouts for admin/staff and customer roles. Give each role an appropriate navigation menu and clear status badges.
- Build the demo path: login → product and plan setup → quotation/subscription → Billing Control Tower preview → run result → invoice → partial payment → finance dashboard.
- Build a customer portal showing only that customer's subscriptions and invoices, with add-on changes and permitted pause, renew, and cancel actions.
- Make the Control Tower the standout screen: due count, expected INR total, exceptions requiring action, a preview table of invoice calculations, and a before/after run summary.
- Provide usable form validation, empty/loading/error states, pagination controls, and a print-friendly invoice view. Keep charts secondary to readable totals and the working flow.
- Start with mock JSON matching GSK's shared contract. Replace mocks with API calls as endpoints arrive. Never calculate invoice totals in the browser; display backend values.

## API handoffs

Use `POST /api/auth/login`, `/api/products`, `/api/plans`, `/api/templates`, `/api/subscriptions`, `GET /api/billing/preview`, `POST /api/billing/run`, `/api/invoices`, `/api/invoices/{id}/payments`, and `GET /api/dashboard`. Send `Authorization: Token <token>`. All money values are integer paise and must be formatted as INR. Ask the endpoint owner immediately if a response shape differs from the agreed mock.

## Completion check

A judge can follow the full seeded customer story without opening an API client. The UI visibly distinguishes draft, active, paused, expired, paid, and overdue records. Refreshing a page retains backend data. A customer cannot navigate to staff screens, and backend checks remain the security boundary.

## Phase 1 — screens against a fixed contract (hours 0–4)

- By 0:30, agree on routes and example JSON with GSK. Build the demo screens against those examples, including loading, empty, and error states.
- At the phase gate, every demo route must render without console errors, money must format correctly from paise, and `npm run build` must pass. Give GSK any mismatch between mock data and the backend contract before Phase 2.

## Phase 2 — API integration and demo (hours 4–8)

- Replace mock calls with real endpoints and complete the seeded story by 6:00. Freeze new UI features then.
- Test refresh, role navigation, form errors, invoice actions, and the Control Tower before/after run view. Repeat `npm run build` after integration.
- Fix blocking UI defects in `gdm/` by 7:00 and support screenshots and rehearsal in the last hour. GSK performs final integration. Favor a complete flow over extra charts.
