# Brightloop

Subscription billing demo built by four owners. Read [CONTRACT.md](CONTRACT.md) for shared models and API shapes; the individual handoff files describe each owner's work. GSK owns the Django project and billing engine, YASCN owns identity/catalog/subscriptions, ALIAR owns invoices/payments/reporting, and GDM owns React UI.

## GSK setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s gsk/tests -v
```

Once `yascn/` and `aliar/` are delivered, GSK will connect their models in `gsk/integration.py`, register their routes in `gsk/urls.py`, and then run migrations and the full Django check. The app is intentionally not migrated with Django's default User: `yascn.User` must exist before the first migration.

