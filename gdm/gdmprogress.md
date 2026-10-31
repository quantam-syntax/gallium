# GDM progress

## Done

- Built the responsive Brightloop Control Tower, staff billing screens, and
  customer portal using GSK's updated visual design.
- Added token-based login and registration, session restoration through
  `/api/auth/me`, explicit API errors, loading states, and authenticated
  paginated list requests.
- Connected subscriptions, products, plans, invoices, dashboard and billing
  preview/run data to the API. Money remains in integer paise until formatted
  for display.
- Added authenticated forms for products, plans, quotations, and customer
  registration. Subscription actions use the backend-provided
  `permitted_actions`; customer screens are read-only.
- Added a print view that renders each invoice from its saved `snapshot`.
- Prevented stale in-flight requests from populating state after a later refresh
  or sign-out.

## Integration gaps

- The current root URL configuration registers YASCN and billing routes, but
  does not yet register ALIAR invoice, payment, or dashboard URLs. The UI
  reports those endpoint failures explicitly rather than substituting demo data.
- There is no customer-directory API route yet. The staff customer list is
  derived from invoices and subscriptions; accounts created in the current
  session are additionally available for quotation creation.

## Verification

- `npm run build` in `gdm/`: passed with Vite 6.4.5.
- End-to-end API and browser validation remains pending until the required
  backend routes are registered and available.
