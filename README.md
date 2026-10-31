# Brightloop

Subscription billing demo built by four owners. Read [CONTRACT.md](CONTRACT.md) for shared models and API shapes; the individual handoff files describe each owner's work. GSK owns the Django project and billing engine, YASCN owns identity/catalog/subscriptions, ALIAR owns invoices/payments/reporting, and GDM owns React UI.

## GSK setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py test gsk.tests --settings=gsk.test_settings
.venv/bin/python manage.py check --settings=gsk.test_settings
```

Once `yascn/` and `aliar/` are delivered, GSK will connect their models in `gsk/integration.py`, register their routes in `gsk/urls.py`, and then run migrations and the full Django check. The app is intentionally not migrated with Django's default User: `yascn.User` must exist before the first migration.

`gsk.test_settings` is only for isolated billing API tests. It omits unfinished teammate apps and uses Django's User solely in that test process; never use it for production migrations.

