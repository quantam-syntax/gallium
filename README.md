# Brightloop

Subscription billing demo built by four owners. Read [CONTRACT.md](CONTRACT.md) for shared models and API shapes; the individual handoff files describe each owner's work. GSK owns the Django project and billing engine, YASCN owns identity/catalog/subscriptions, ALIAR owns invoices/payments/reporting, and GDM owns React UI.

For the recording sequence and setup checklist, use [DEMO.md](DEMO.md).

## Brightloop assistant

The floating **Ask Brightloop** chat is available to signed-in staff and customers.
Without an API key it runs in clearly labelled **data-backed demo mode**, answering
questions about current subscriptions, MRR, monthly revenue, overdue invoices,
product momentum, and customer billing using read-only database queries. Customers
only receive their own subscription and invoice data.

For open-ended app questions, set `GEMINI_API_KEY` in the backend environment or
in a local, Git-ignored `.env` file (`GEMINI_API_KEY=your-key`), then restart
Django. `GEMINI_MODEL` optionally overrides the default `gemini-3.5-flash-lite`.
The key stays on the server; the browser only calls `POST /api/assistant/chat`.
The endpoint is authenticated, limited to 30 requests per user per hour, and
does not perform billing actions. It first checks whether the question is about
Brightloop; unrelated questions receive a refusal. For app questions, Gemini
can call only allowlisted read-only lookups for dashboard totals, catalog,
subscriptions, invoices, payments, customers, product trends, and app workflows.
Every lookup enforces the signed-in user's role and caps result size. The
backend uses Google's [Gemini function-calling API](https://ai.google.dev/gemini-api/docs/generate-content/function-calling.md)
and sends the role-scoped snapshot and recent chat messages to Gemini for each
answer. Never commit an API key.

## Sync after the author-name correction

On 31 October, `main` history was rewritten to correct all GDM commits recorded with **AKASH S KISHOR** and `vgauthami007@gmail.com` to the author and committer name **Gauthami**. The account and email remain the same. Later commits have new hashes because their parent hashes changed; the application changes were preserved. A normal `git pull` from an older clone may report divergent branches.

First save or commit any uncommitted work. In a clone still on the old `main`, preserve the old branch and create a fresh local `main` from the remote:

```bash
git fetch origin
git branch -m main main-before-gauthami-fix
git switch -c main --track origin/main
```

The old branch is retained locally, including any unpushed commits. Ask GSK to help replay those commits onto the new `main` before pushing; do not force-push the old history. New clones need no special action. Gauthami should run `git config user.name "Gauthami"` and `git config user.email "vgauthami007@gmail.com"` in her own clone before another commit.

## Run the integrated backend

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

In another terminal, seed the demo once with a password you choose (more than
eight characters, including uppercase, lowercase, and a special character):

```bash
BRIGHTLOOP_DEMO_PASSWORD='ChooseYourOwn!123' .venv/bin/python manage.py seed_yascn_demo
```

The seed creates `admin@brightloop.example`, `customer@brightloop.example`, and
an active subscription due today. Existing account passwords and billing cursors
are preserved, so use the password from the first seed on subsequent runs.
For a populated, explicitly fictional showcase, run:

```bash
BRIGHTLOOP_DEMO_PASSWORD='ChooseYourOwn!123' .venv/bin/python manage.py seed_showcase
```

This adds 25 products with variants, 3 plans, 2 taxes, 2 discounts, 3 quotation
templates, 50 customer accounts, and 300 active subscriptions. It creates
invoices through the normal billing and finance services, confirms them, and
records a mix of full, partial, and outstanding payments. The command is safe
to rerun: stable `SUB-SHOWCASE-*` numbers prevent duplicate contracts and the
billing period constraint prevents duplicate invoices. It only bills showcase
subscriptions, so the original demo billing cursor is untouched. Existing
account passwords are preserved. The product catalog shows nine weekly adoption
points and the fastest growing and slowing products. `GET /api/analytics/products`
is available to staff and admin; it counts current active subscriptions by
contract start date in adjacent 30-day windows. It is an adoption view, not a
historical add-on event log.
After the first billing run, the seeded subscription is no longer due. Create a
new quotation/subscription in the UI for another walkthrough; do not reset the
cursor on a previously billed subscription.
The admin can log in at `POST /api/auth/login`, preview at
`GET /api/billing/preview`, run billing at `POST /api/billing/run`, and access
invoices, payments, and dashboard data under `/api/invoices` and `/api/dashboard`.
All authenticated requests use `Authorization: Token <login token>`.

Run the integrated checks with:

```bash
.venv/bin/python manage.py test aliar.tests yascn.tests gsk.tests
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```

## Frontend check

```bash
cd gdm
npm ci
npm run build
npm run dev
```

Open the Vite URL and sign in as the seeded admin. The UI now uses authenticated
backend APIs and restores the session after refresh. A useful walkthrough is:
create a quotation from the seeded plan and Odoo product, confirm and activate
the subscription, preview and run billing, confirm the draft invoice, record a
partial payment, inspect the dashboard and saved-snapshot invoice print view,
refresh, then run billing again to show zero duplicates. Sign in as the seeded
customer to see only their subscriptions and invoices. Run
`.venv/bin/python manage.py run_billing` daily, followed by
`.venv/bin/python manage.py maintain_subscriptions`. Billing catches up due
periods before maintenance finalizes expired or auto-close contracts. Both
commands accept `--as-of YYYY-MM-DD` for a past date. The Vite server proxies
`/api` to Django on `127.0.0.1:8000`.

If **Run billing** creates zero invoices, check Quotations for a confirmed
subscription and click **Activate**. The Control Tower's Expected Total is the
amount remaining to bill: it becomes ₹0 after invoicing. The run result shows
the amount just invoiced, and the finance cards show the new outstanding balance.

The React app now includes password recovery, customer add-on/quantity editing,
and staff invoice send/cancel/reissue controls. Their backend routes and payloads
are documented in `yascn/LIFECYCLE.md` and `CONTRACT.md`. The reset-link,
customer quantity edit, invoice cancellation/reissue, and invoice send paths
passed a local browser check against an isolated copy of the demo database.
The final team demo recording remains outstanding.
Staff can retrieve every active customer account through `GET /api/customers`,
so newly registered customers remain available for quotations after refresh.

The local performance check used a temporary database with 1,003 subscriptions
and 1,004 invoices. Headless Chromium reached overview, subscriptions, and
invoices at 0.73 s, 1.24 s, and 1.69 s from navigation start, respectively.
This verifies the two-second target in the local demo environment; deployed
latency should be measured separately.

YASCN's custom User and ALIAR's finance app are installed, routed, and connected
through GSK's production billing repository. The app is intentionally not
migrated with Django's default User.

`gsk.test_settings` is only for isolated billing API tests. It omits teammate
apps and uses Django's User solely in that test process; never use it for
production migrations.

