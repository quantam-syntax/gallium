# YASCN core integration handoff to GSK, ALIAR, and GDM

YASCN implements the shared contract in `CONTRACT.md`. All delivered source,
migrations, tests, demo data creation, and documentation live in `yascn/`.

## Integration changes for GSK

1. Keep `AUTH_USER_MODEL = "yascn.User"` before the first migration. `yascn` and
   `rest_framework.authtoken` are already in `gsk.settings.INSTALLED_APPS`.
2. ALIAR's invoice/payment models, migrations, API, and creation service arrived
   in `dc60886` and pass compatibility tests with YASCN. Register its full-path
   routes with `path("", include("aliar.urls"))` in root URLs.
3. YASCN's routes are already registered by GSK via
   `path("api/", include("yascn.urls"))` alongside billing routes.
4. Use `yascn.billing.due_candidates` for the billing repository read side (see
   below), then connect `aliar.services.create_for_candidate` for transactional
   invoice creation in `gsk/integration.py`. Implement `invoice_exists` using
   `aliar.models.Invoice`, including cancelled revisions. ALIAR consumes discount
   usage and advances the cursor; do not duplicate those writes in GSK.
5. Run migrations, check, and the app tests with the integrated settings. No
   root configuration or another owner's source has been edited by YASCN.

All model imports are from `yascn.models`: `User`, `Product`, `Variant`, `Plan`,
`Tax`, `Discount`, `QuotationTemplate`, `TemplateLine`, `Subscription`, and
`SubscriptionLine`. Initial migration: `yascn.0001_initial` (depends on Django
auth, contains the custom User; ALIAR should use a swappable user dependency).

## Verification and local demo data

From the repository root:

```bash
.venv/bin/python manage.py test yascn --settings=yascn.test_settings -v 2
.venv/bin/python manage.py check --settings=yascn.test_settings
.venv/bin/python manage.py makemigrations yascn --check --dry-run --settings=yascn.test_settings
.venv/bin/python manage.py test yascn gsk.tests
.venv/bin/python manage.py check
```

`test_settings` deliberately omits ALIAR, uses in-memory SQLite by default,
mounts YASCN at `/api/`, captures mail in memory, and uses a fast **test-only**
password hasher. It is for verification, not the demo server.

After GSK integration, create repeatable demo data:

```bash
.venv/bin/python manage.py migrate
read -rs -p 'Demo password: ' BRIGHTLOOP_DEMO_PASSWORD
export BRIGHTLOOP_DEMO_PASSWORD
.venv/bin/python manage.py seed_yascn_demo
unset BRIGHTLOOP_DEMO_PASSWORD
```

Use a password longer than eight characters containing uppercase, lowercase,
and special characters. The command creates `admin@brightloop.example` and
`customer@brightloop.example`, a monthly ₹1,000 plan, GST 18%, a ₹0 connector
product with Odoo +₹560, a quotation template, and active `SUB-DEMO-0001` due
today. It preserves existing account passwords and never resets an existing
demo subscription or its billing cursor. No invoice is created; GSK owns that.
Default account emails can be changed using `--admin-email` / `--customer-email`.
For bootstrap without demo data, use `manage.py createsuperuser` (email login).

## Routes and permissions

All routes have no trailing slash. Authentication is `Authorization: Token …`.
All lists return `count`, `results`, `next`, `previous` with page size 25.

| Route | Behavior |
| --- | --- |
| `POST /api/auth/register` | Public customer signup; authenticated admin can explicitly set staff/admin role. No public elevation. |
| `POST /api/auth/login` | Email/password login; returns token and public user object. |
| `GET /api/auth/me` | Current public user object for UI refresh. |
| `/api/products`, `/api/plans`, `/api/taxes`, `/api/discounts`, `/api/templates` | List/detail to staff/admin; create/edit/delete admin only. Customers do not receive internal cost prices or discount rules. |
| `POST /api/products/{id}/variants` | Admin creates a variant. |
| `PATCH/DELETE /api/products/{id}/variants/{variant_id}` | Admin edits/removes a variant belonging to that product. |
| `/api/subscriptions` | Staff/admin manage drafts; customers can only read their own list/detail. |
| `POST /api/subscriptions/{id}/transition` | Staff/admin core actions `quote`, `confirm`, `activate`. |

Referenced records cannot be deleted; errors are field errors or `detail`.
Product creation accepts nested `variants`. Existing variants use their explicit
endpoint, preserving IDs referenced by subscription lines. Templates and draft
subscriptions accept complete replacement `lines` arrays on PUT/PATCH; each
line must include product and quantity. Only drafts may be edited or deleted.
Customers receive an empty `permitted_actions` list during Phase 1. Server-owned
subscription status, number, and billing cursor cannot be supplied in requests.

## JSON examples

Login request and response:

```json
{"email":"admin@brightloop.example","password":"<configured password>"}
```

```json
{"token":"<token>","user":{"id":1,"email":"admin@brightloop.example","full_name":"Demo Admin","company_name":"Brightloop","role":"admin"}}
```

Create a product (tax 1 must already exist):

```json
{"name":"Integration","type":"service","sale_price_paise":0,"cost_price_paise":0,"tax_id":1,"variants":[{"name":"Odoo","price_delta_paise":56000}]}
```

Create a plan:

```json
{"name":"Monthly","base_price_paise":100000,"tax_id":1,"frequency":"monthly","minimum_quantity":1,"auto_close":false,"allow_pause":true,"allow_renew":true,"allow_cancel":true}
```

Create a template (identifiers illustrative):

```json
{"name":"Monthly + Odoo","plan_id":1,"valid_days":14,"lines":[{"product_id":1,"variant_id":1,"quantity":1}]}
```

Create a subscription:

```json
{"customer":2,"template_id":1,"start_date":"2026-10-31","expiry_date":"2027-10-31","payment_terms_days":14}
```

Alternatively supply `plan` and `lines` directly. Template creation uses
`plan_id`; subscription input/output uses `plan` and `customer` integer IDs, as
specified for subscription responses. Dates above are illustrative; use current
dates for the demo. Template application copies its effective line prices and
sets quotation expiry to local midnight at today + `valid_days`. Direct
quotations default to fourteen days when quoted. Expiry is exclusive: a quote
cannot be confirmed or activated at or after its expiry timestamp. Expired
quotations are persisted on their next read or transition attempt; a scheduled
expiry worker is outside Phase 1.

Send `{"action":"quote"}`, then `{"action":"confirm"}`, then
`{"action":"activate"}` to the transition route. Example active response:

```json
{"id":1,"number":"SUB-DEMO-0001","customer":2,"plan":1,"status":"active","start_date":"2026-10-31","expiry_date":"2027-10-31","quote_expires_at":"2026-11-14T00:00:00+05:30","payment_terms_days":14,"next_bill_date":"2026-10-31","subscription_discount_id":null,"lines":[{"id":1,"product_id":1,"variant_id":1,"quantity":1,"unit_price_paise":56000,"tax_id":1,"active":true}],"permitted_actions":[]}
```

Ordinary numbers are unique `SUB-` plus an uppercase UUID; the seed has a stable
demo number. No sequential numbering format was prescribed by the contract.

## Billing adapter data for GSK

The complete read mapper is now implemented and tested with GSK's actual preview
calculation and shared HTTP route:

```python
from yascn.billing import due_candidates

class Repository:
    def due_candidates(self, as_of):
        return due_candidates(as_of)
    # GSK/ALIAR still implement invoice_exists and create_period_if_missing.
```

It returns `list[gsk.service.BillingCandidate]`. Due subscriptions, active
effective-price lines, tax rates, assigned subscription discounts, and matching
product discounts are mapped without changing stored records. Loading 1 or 13
subscriptions with product lines uses the same **three database queries**;
an empty due list uses one query. Inactive/missing taxes map to zero. Product
discounts are restricted to active rules for products on active due lines;
dates, thresholds, and usage limits are preserved for GSK's period-specific
eligibility checks, including old catch-up periods. Inactive catalog products
do not remove existing contract lines. No variant surcharge is added again.

The lower-level ORM query remains available:

```python
from yascn.services import due_subscriptions

subscriptions = due_subscriptions(as_of)
```

This returns an ordered queryset of active subscriptions with
`next_bill_date <= as_of` and `next_bill_date < expiry_date`. This includes
missed cycles when the contract expiry date has already passed; GSK's period
calculator stops at the exclusive expiry date. Paused/expired/closed records and
future cycles are excluded. Customer, plan tax, assigned discount, and line
relations are loaded for the adapter. Billing is stopped at exclusive expiry;
expired subscriptions await Phase 2 renewal. Never filter availability dates
when billing existing subscriptions; availability controls new signups only.

For each GSK `BillingCandidate`, map:

| Candidate field | ORM source |
| --- | --- |
| `id`, `number`, dates, `payment_terms_days` | Same names on subscription |
| `customer_name` | `customer.company_name or customer.full_name` |
| `frequency`, `plan_fee_paise` | `plan.frequency`, `plan.base_price_paise` |
| `plan_tax_rate_bps` | `plan.tax.rate_bps` when tax exists and is active, else 0 |
| `lines` | `subscription.lines.all()`, including only `active` rows; `BillableLine` takes product name, quantity, unit price, active tax rate or 0, product ID |
| `product_discounts` | `Discount.objects.filter(scope="product", active=True)` mapped to `DiscountRule`; GSK evaluates dates/thresholds/usage for each period |
| `subscription_discount` | Assigned `subscription_discount` mapped to `DiscountRule`, else `None` |

**Do not add variant surcharge again:** `unit_price_paise` already includes it.
An omitted price is derived from sale price + surcharge on creation; an explicit
price is treated as the full negotiated unit price. Product/variant/template
price edits never rewrite copied subscription lines. Product taxes are copied
as line tax references; GSK snapshots rates and financial amounts on invoicing.
`Discount.used_count` is read-only in the API and advanced only by GSK's atomic
invoice creation adapter. Assigned whole discounts have scope `subscription`;
product discounts require a product. Values are paise or basis points as in the
contract. GSK remains responsible for invoice uniqueness, discount consumption,
locking, and transactional cursor advancement with ALIAR.

`yascn.services.transition(subscription, action)` now reloads and locks the
subscription before validating its current state, customer, and plan. Callers
must use the returned fresh instance. This prevents stale Python model state
from reopening a subscription that was already closed. Drafts whose template
validity has elapsed no longer advertise or accept `quote`.

## Phase 2 boundary

The unblocked core integration handoff is delivered. Tests use the real YASCN
database models and GSK's preview function; HTTP preview tests inject only a
read repository and an explicit no-existing-invoice answer. They do **not** prove
invoice persistence, rerun idempotency, payments, or the full integrated demo.
ALIAR's new combined tests now cover real invoice persistence, partial payments,
dashboard totals, customer ownership, catch-up, and a duplicate-free second run.
The combined command `.venv/bin/python manage.py test aliar.tests yascn.tests
gsk.tests --settings=aliar.test_settings --verbosity 1` passes **76 tests**.
Those tests still patch repository selection and use test URL wiring; they do
not establish that the production wiring or browser demo gate has passed.
Shared billing endpoints still return 503 until GSK implements the repository.
The new GDM dashboard is present but still uses local in-memory demo data.

Password reset/SMTP delivery, pause/resume/renew/close, subscription-expiry state
maintenance/auto-close, and customer next-cycle add-on/quantity changes are
deferred as instructed. Flags and states are modeled now; unsupported actions
are not advertised. Active-line writes remain blocked until the catch-up billing
integration can ensure old periods use old terms. Full billing/payment/dashboard
and frontend gates require the other owners' deliveries.
