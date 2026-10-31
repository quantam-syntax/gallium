# Brightloop

Subscription billing demo built by four owners. Read [CONTRACT.md](CONTRACT.md) for shared models and API shapes; the individual handoff files describe each owner's work. GSK owns the Django project and billing engine, YASCN owns identity/catalog/subscriptions, ALIAR owns invoices/payments/reporting, and GDM owns React UI.

## GSK setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py test gsk.tests --settings=gsk.test_settings
.venv/bin/python manage.py check --settings=gsk.test_settings
```

## Frontend check

```bash
cd gdm
npm ci
npm run build
```

Current frontend code is a buildable welcome screen. GDM's contract-shaped admin, customer, and Billing Control Tower views are still in progress.
The Vite development server proxies `/api` to Django on `127.0.0.1:8000`, so frontend calls can use relative API paths.

YASCN's custom User, catalog, and subscription app is present and routed. Once `aliar/` is delivered, GSK will connect both apps in `gsk/integration.py`, register ALIAR's routes, then run migrations and the full Django check. The app is intentionally not migrated with Django's default User.

`gsk.test_settings` is only for isolated billing API tests. It omits unfinished teammate apps and uses Django's User solely in that test process; never use it for production migrations.

