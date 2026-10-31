# Brightloop

Subscription billing demo built by four owners. Read [CONTRACT.md](CONTRACT.md) for shared models and API shapes; the individual handoff files describe each owner's work. GSK owns the Django project and billing engine, YASCN owns identity/catalog/subscriptions, ALIAR owns invoices/payments/reporting, and GDM owns React UI.

## Sync after the author-name correction

On 31 October, `main` history was rewritten solely to correct GDM's frontend commit author and committer name from **AKASH S KISHOR** to **Gauthami**. The GitHub account and email stayed `vgauthami007-wq` / `vgauthami007@gmail.com`; file contents did not change. The old commit `e2574ba` is now `f58b18f`. A normal `git pull` from a clone of the old history may report divergent branches.

First save or commit any uncommitted work. In a clone still on the old `main`, preserve the old branch and create a fresh local `main` from the remote:

```bash
git fetch origin
git branch -m main main-before-gauthami-fix
git switch -c main --track origin/main
```

The old branch is retained locally, including any unpushed commits. Ask GSK to help replay those commits onto the new `main` before pushing; do not force-push the old history. New clones need no special action. Gauthami should run `git config user.name "Gauthami"` in her own clone so future commits display the correct name.

The later dashboard commit `97f4fa9` was also recorded as **AKASH S KISHOR** with Gauthami's email. Set both `user.name` and `user.email` locally and verify them before making another commit. This published commit remains in shared history; correcting it would require another coordinated rewrite.

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

The reset-password and customer add-on/quantity screens have not yet been
connected in React. Their backend routes and payloads are documented in
`yascn/LIFECYCLE.md` and `CONTRACT.md`.

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

