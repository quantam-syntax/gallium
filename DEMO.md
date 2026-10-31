# Brightloop demo runbook

## Before recording

1. Pull the latest `main`. If your clone predates the Gauthami author correction, follow [README sync instructions](README.md#sync-after-the-author-name-correction) first.
2. In terminal 1, run `.venv/bin/python manage.py migrate` and `.venv/bin/python manage.py runserver 127.0.0.1:8000`.
3. In terminal 2, run `cd gdm && npm ci && npm run dev`. Open the Vite URL, normally `http://127.0.0.1:5173/`.
4. On a fresh database, run `BRIGHTLOOP_DEMO_PASSWORD='your-password' .venv/bin/python manage.py seed_yascn_demo`, then run `BRIGHTLOOP_DEMO_PASSWORD='your-password' .venv/bin/python manage.py seed_showcase`. The second command fills the catalog and reports with fictional data and is safe to rerun. Use the password chosen on the **first** seed for `admin@brightloop.example` and `customer@brightloop.example`; reseeding preserves existing passwords and billed periods.
5. Check that admin login, Products & plans, and Billing Control Tower load without an error banner. Keep browser zoom at 100% and close unrelated tabs and notifications.

## Suggested 3–4 minute recording

| Time | Action | What to say |
| --- | --- | --- |
| 0:00–0:25 | Sign in as admin; open **Products & plans**. Show the product adoption graphs, fastest growing and slowing products, then the Odoo variant surcharge, plan, tax, discount, and template. | “Brightloop configures its recurring offer once, then sees which products are gaining subscriptions.” |
| 0:25–1:05 | Open **Quotations** → **Create quotation**. Choose the seeded customer and template, keep the start date today, save. In the new quotation row, click **Confirm**, then **Activate**. | “The offer becomes a numbered active subscription; only active subscriptions are billable.” |
| 1:05–1:45 | Open **Overview**. Point out the due subscription and expected amount in the Billing Control Tower. Click **Run billing** once, then again to show zero new invoices. | “Preview exposes what will bill; the second run proves the period cannot be billed twice.” |
| 1:45–2:35 | Open **Invoices**. Confirm the new draft invoice, record a ₹500 partial payment with a method, payment date, and a short reference note. Show the remaining balance and use **View / print**. | “The invoice is built from the subscription; payments and outstanding amounts update from saved records.” |
| 2:35–3:15 | Return to **Overview** to show collected and outstanding totals. Sign out and sign in as the seeded customer. Show their subscription, included product, and invoice balance. | “Finance and the customer see consistent numbers, with customer access restricted to their own data.” |
| 3:15–3:45 | If time allows, open **Manage products & quantities** in the customer portal and explain changes apply to future invoices. | “Customers can self-serve without changing an already issued invoice.” |

## Rehearsal notes

- A billed subscription is **not due again today**. For each rehearsal or retake, create and activate a fresh quotation instead of changing an invoice or rewinding its billing cursor.
- The **Expected Total** is the amount **remaining to bill**, so it falls to ₹0 after a successful run. **Invoiced this run** and the invoice/dashboard totals show the amount created. Gross monthly recurring revenue is based on active subscriptions and does not change merely because an invoice was generated.
- The showcase data is fictional. Its historical invoices are already billed, so select the newly activated quotation in the Control Tower when demonstrating a fresh billing run. Product momentum counts currently active subscriptions by contract start date; it does not infer historical add-on edits.
- With the seeded monthly plan and one Odoo variant, the expected invoice is ₹1,840.80 including tax. A ₹500 payment leaves ₹1,340.80 outstanding, unless you changed the catalog or applied a discount.
- If the dashboard is crowded by earlier rehearsal records, use a fresh disposable local database before the final recording. Do not delete production data.
- The default email backend captures invoice and password-reset mail in `.email-outbox/`. The recording does not need an SMTP account.
- Stop when the core story is clear. The AI follow-up idea was optional and is not part of this demo.
