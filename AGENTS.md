# Tripple Phase Electricals - Quotation & Invoice System

Build a simple Django + MySQL web app for creating, printing and reporting on
quotations and invoices. There is **no product catalog and no customer table**:
the user types every detail onto each document.

## Company

- Name: Tripple Phase Electricals Limited
- KRA PIN: P051777360U
- Currency: KES
- VAT: 16% (configurable in settings, default 16.00)
- Logo: `static/img/logo.png` (black swoosh arcs, red and blue dots)
- Colours: black primary, red `#E10600` and blue `#0A2EFF` as accents
- Address: CHARLES RUBIA LANE, NAIROBI 586635-00100, Kenya
- Phone: 0748645468; email: info@tripplephaseelectricals.com
- Payment details: Tripple Phase Electricals Limited, Equity Bank,
  account 0940278884568
- Company details remain editable in the app (CompanySettings) and are read by
  every PDF.

## Tech stack

- Django (latest stable), MySQL, PyMySQL (`pymysql.install_as_MySQLdb()` in `config/__init__.py`)
- Tailwind CSS (CDN is fine), Chart.js for the dashboard
- WeasyPrint for PDFs, openpyxl for Excel exports
- whitenoise + gunicorn for deployment, python-dotenv for local `.env`

## Project layout

```
config/       settings, urls, wsgi
accounts/     login/logout, user management (superuser only)
core/         CompanySettings, dashboard, health check
documents/    Document, DocumentItem, forms, views, PDF/print
reports/      monthly reports and exports
templates/    base.html + app templates + print/PDF templates
static/       css, js, img/logo.png
```

## Models

**CompanySettings** (single row, editable by superusers)
name, logo, address, phone, email, kra_pin, payment_details, terms, vat_rate (default 16.00)

**Document**
- doc_type: `quotation` / `invoice`
- number: auto, `QT-0001` and `INV-0001` with separate sequences, generated safely
  inside a transaction (no duplicates under concurrent saves)
- issue_date, valid_until (quotations), due_date (invoices)
- client_name, client_phone, client_email, client_address, client_pin (all free text)
- notes
- apply_vat (bool, default True)
- subtotal, vat_amount, total (Decimal)
- status: quotation = draft / sent / accepted / converted; invoice = unpaid / paid / cancelled
- paid_date, payment_method (cash / M-Pesa / bank / cheque)
- converted_from (self FK, nullable)
- created_by (User), created_at, updated_at

**DocumentItem**
document FK, description, quantity, unit_price, line_total

Rules: use `Decimal` everywhere. VAT = subtotal x vat_rate / 100, rounded to 2 places
(ROUND_HALF_UP). Prices are exclusive of VAT; VAT is added on top. Example that must
pass a test: subtotal 1,139,000.00 -> VAT 182,240.00 -> total 1,321,240.00.

## Features

1. **Auth**: login required everywhere. Superusers manage users, settings and reports.
   Staff can create, edit, print and convert documents.
2. **Document form**: dynamic add/remove item rows, live subtotal / VAT / total,
   VAT on/off toggle.
3. **Autocomplete** (datalist) for item descriptions, unit prices and client names
   drawn from previous documents. This replaces catalogs, so no extra tables.
4. **Convert quotation to invoice** in one click (copies client and items, links
   `converted_from`, marks the quotation `converted`). Also "duplicate document".
5. **Mark invoice paid**: paid date and payment method.
6. **Print view and PDF download** for quotations and invoices: logo, company
   details, KRA PIN, client details, items table, subtotal, VAT 16%, grand total,
   payment details and terms. The PDF must fit cleanly on one page for typical
   documents and paginate correctly for long ones (repeat table header, no
   near-empty trailing page).
7. **Dashboard**: this month's quoted, invoiced and paid totals; outstanding amount;
   VAT for the month; document counts; 12-month invoiced-vs-paid chart; recent
   documents. Greeting must follow time of day (Africa/Nairobi).
8. **Reports** (superusers): choose month and year; table of invoices with subtotal,
   VAT and total, a totals row, and a VAT summary. Download as **Excel** and **PDF**.
9. **Lists**: search and filter by number, client, status and date range; pagination.

## Phases - finish one, then stop and check in with me

1. Scaffold, auth, CompanySettings, base layout with sidebar and branding
2. Document models, form with item rows, numbering, VAT maths, tests
3. Print view and PDF generation
4. Quotation to invoice, duplicate, mark as paid
5. Dashboard
6. Monthly reports with Excel and PDF export
7. Polish: empty states, validation, seed demo data, README

Do not start the next phase until I confirm the current one works.

## Deployment (Railway) - lessons from a previous project

- Read the database from `MYSQL_URL` (parse with `urlparse`), fall back to
  `DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT` locally. In production, fail loudly
  with `ImproperlyConfigured` if values are empty; never silently default to localhost.
- Bind gunicorn to `$PORT`. Add a `/health/` route returning `OK`.
- Keep `railway.json` minimal: startCommand runs `collectstatic`, `migrate`, then gunicorn.
- WeasyPrint needs system libraries. Document this in the README: set the Railway
  variable `RAILPACK_DEPLOY_APT_PACKAGES` to
  `libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 libffi-dev shared-mime-info`
  (the package is `libgdk-pixbuf-2.0-0` on Debian Trixie).
- `.gitignore` must exclude `venv/`, `.env`, `staticfiles/`, `media/`, `__pycache__/`.
  It already exists; do not commit those.
- Provide `.env.example` with placeholders only. Never write real secrets into any file.
- Set `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and secure-cookie settings from the
  environment, using `RAILWAY_PUBLIC_DOMAIN` when present.

## Working rules

- Keep it simple. This is a small single-company tool, not a multi-tenant platform.
- Explain each phase briefly when finished and list the commands to run and test it.
- Write tests for VAT rounding and document numbering.
- Ask before adding dependencies beyond the stack above.
- Use the project's virtual environment (`venv/`) for all Python commands.

