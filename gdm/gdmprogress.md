# GDM progress

## Latest integration handoff

- Added a responsive catalog summary and richer product/variant cards with subtle motion and reduced-motion support.
- Admin forms now create variants, taxes, fixed/percentage discounts, and multi-line quotation templates through the live API. Product and plan forms expose tax and availability/permission settings. Quotation creation can use a saved template and assign a subscription discount.
- Browser-verified variant, tax, discount, and template creation; removed the temporary verification records. `npm run build` passes.
- Next for Gauthami: password reset, customer add-on/quantity edit, and invoice send/cancel/reissue screens. Validate each with backend role checks and a build. Keep UI changes in `gdm/` and ask GSK to integrate root changes.

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
- GSK's live browser walkthrough found that draft invoices had no Confirm
  action, so the invoice table now offers Confirm for drafts and Record payment
  only for confirmed invoices. The real admin/customer path through quotation,
  billing, payment, refresh, print preview, and a duplicate-free run passed.

## Integration gaps

- GSK now registers ALIAR routes; the core API-backed browser path works.
- Password-reset and customer add-on/quantity screens are still pending after
  YASCN's Phase 2 API delivery. Invoice send/cancel/reissue controls are also
  not yet exposed in the staff UI.
- There is no customer-directory API route yet. The staff customer list is
  derived from invoices and subscriptions; accounts created in the current
  session are additionally available for quotation creation.

## Verification

- `npm run build` in `gdm/`: passed with Vite 6.4.5.
- GSK completed the live browser walkthrough, then verified the new Confirm
  button against a real draft invoice: it changed to confirmed and exposed
  Record payment. `npm run build` passed after the change.
- With temporary demo data containing 1,003 subscriptions and 1,004 invoices,
  local headless Chromium displayed the overview at 733 ms, subscriptions at
  1,237 ms, and invoices at 1,687 ms from navigation start. The demo database
  was restored afterward; deployment latency remains environment dependent.
