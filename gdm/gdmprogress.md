# GDM progress

## Done

- Created an isolated React/Vite frontend starter in `gdm/`.
- Built responsive staff views for the Billing Control Tower, subscriptions,
  quotations, invoices, catalog, and customers.
- Built a customer portal view with subscription controls and invoice/payment
  access, scoped to the seeded demo customer.
- Added contract-shaped preview/run data, INR formatting from paise, billing-run
  results, partial-payment validation, and local subscription transitions.
- Added empty states, search, responsive navigation, and print-friendly layout
  rules.

## Next

- Replace in-memory demo state with the shared API, including `/api/auth/me`
  after refresh and backend-provided `permitted_actions`.
- Add loading/error handling, pagination, and API-backed product, plan, and
  quotation forms.
- Verify role navigation, refresh persistence, invoice print output, and a
  second no-op billing run against the integrated backend.

## Blocked

- API integration is blocked until the backend endpoints are available together
  for the seeded demo. The current interactions use local in-memory demo data.

## API response mismatches

- None observed; the UI has not called the API yet.

## Verification

- `npm run build`: passed with Vite 6.4.5; production bundle generated successfully.
- GSK review added a local `/api` proxy to the Django server on `127.0.0.1:8000`; `npm run build` still passes.

## Commands for GSK

- Start: `cd gdm && npm run dev`
- Build: `cd gdm && npm run build`
