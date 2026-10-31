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
```

The frontend has responsive admin, customer, and Billing Control Tower views,
but currently uses local in-memory demo records. GDM's next handoff is to
connect these screens to authenticated backend APIs and add an individual
invoice print view from the saved invoice snapshot.
The Vite development server proxies `/api` to Django on `127.0.0.1:8000`, so frontend calls can use relative API paths.

YASCN's custom User and ALIAR's finance app are installed, routed, and connected
through GSK's production billing repository. The app is intentionally not
migrated with Django's default User.

`gsk.test_settings` is only for isolated billing API tests. It omits teammate
apps and uses Django's User solely in that test process; never use it for
production migrations.

