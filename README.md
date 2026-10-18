# Tripple Phase Electricals

A Django application for creating, printing, and reporting on quotations and invoices for Tripple Phase Electricals Limited. Save customer contact details for reuse or enter client details directly on each document.

## Requirements

- Python 3.12 or later
- MySQL for a shared or production deployment; local development can use SQLite
- The system libraries listed under [Railway deployment](#railway-deployment) when using WeasyPrint on Linux

## Local setup

Create and activate a virtual environment, install the project requirements, and prepare environment variables:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `DJANGO_SECRET_KEY` to a long random value in `.env`. For local SQLite, leave `MYSQL_URL` empty and clear `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `DB_HOST`. To use MySQL, instead set `MYSQL_URL` or fill in all `DB_*` values with your local database credentials. Do not commit `.env`.

Initialize the database and create an administrator:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/` and sign in. Company contact, payment, VAT, and terms details can be edited under Company settings.

Use Customers in the sidebar to add and update saved customer details. When creating a quotation or invoice, choose a saved customer to fill in their contact details, or leave the selector blank and enter the client details manually.

## Tests

Run the Django test suite with the project's virtual environment active:

```bash
python manage.py test
```

## Vercel deployment

This project can run on Vercel's Python runtime. The Vercel configuration sets
Python 3.12 and a 60-second function duration; Vercel automatically detects the
Django WSGI application and serves collected static files from its CDN.

Vercel does not provide persistent MySQL storage for this app. Create a separate
MySQL database that allows remote connections, and use its connection URL as
`MYSQL_URL`. Do not use local SQLite on Vercel: the function filesystem is not
persistent and does not provide shared database storage. Uploaded media files
are also not persistent there.

**Vercel's free Hobby plan is for personal, non-commercial use only.** This is a
company quotation and invoice system, so use Hobby only for personal evaluation;
company production use requires a plan whose terms permit commercial use.
See [Vercel's Hobby plan terms](https://vercel.com/docs/plans/hobby#hobby-billing-cycle).

1. Import the Git repository into Vercel and leave the Django framework preset,
   build command, and output directory at their detected defaults.
2. Add these project environment variables for Production (and Preview if
   needed):

   ```text
   DJANGO_ENV=production
   DJANGO_DEBUG=False
   DJANGO_SECRET_KEY=<a-long-random-secret>
   MYSQL_URL=<your-external-mysql-connection-url>
   ```

   Vercel supplies `VERCEL_URL` and the project domain automatically; Django
   uses those for allowed hosts and CSRF origins. Add any custom domains to
   `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` as needed.
3. Deploy the project. Before first use, link the Vercel project locally, pull
   its environment variables, and apply the database migrations:

   ```bash
   npx vercel link
   npx vercel env pull .env.local
   venv/bin/python manage.py migrate
   venv/bin/python manage.py createsuperuser
   ```

   `.env.local` is ignored by Git. Do not commit it or put credentials in the
   repository.
4. Confirm `/health/` returns `OK`, then sign in to the deployed application.

WeasyPrint requires native Pango and Cairo libraries that may not be available
in Vercel's Python runtime. If they are missing, PDF download returns an explicit
503 response; use the document print view and the browser's print-to-PDF feature.
Uploaded files are ephemeral on Vercel, so keep the company logo in the bundled
`static/` directory unless persistent object storage is configured.

## Railway deployment

The included `railway.json` runs static collection, database migrations, and Gunicorn at Railway's `$PORT`. It also configures `/health/` as the deployment health check.

1. Create a Railway project and add a MySQL service.
2. Deploy this repository as an application service and connect its `MYSQL_URL` variable to the MySQL service's connection URL.
3. Set `DJANGO_SECRET_KEY` to a unique, long random value and set `DJANGO_ENV=production`.
4. Configure a Railway public domain. The app uses `RAILWAY_PUBLIC_DOMAIN` to allow the host and trust its HTTPS origin. Set `DJANGO_ALLOWED_HOSTS` or `CSRF_TRUSTED_ORIGINS` only when additional domains are needed.
5. Add this Railway variable for WeasyPrint's Debian system dependencies:

   ```text
   RAILPACK_DEPLOY_APT_PACKAGES=libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libglib2.0-0t64 libcairo2 libffi-dev shared-mime-info
   ```

   `libglib2.0-0t64` supplies `libgobject-2.0.so.0`, which WeasyPrint needs when loading its native text-rendering backend. If Railway already has this variable, append `libglib2.0-0t64` to its existing value, save it, and redeploy so the image is rebuilt.

6. After the first deployment, create an administrator using Railway's application shell:

   ```bash
   python manage.py createsuperuser
   ```

Production settings require `MYSQL_URL` or all `DB_*` connection values and a configured `DJANGO_SECRET_KEY`; the app does not silently fall back to local SQLite in production. HTTPS redirects and secure session/CSRF cookies are enabled automatically in production.

## Key routes

- `/` - dashboard
- `/documents/?type=quotation` - quotations
- `/documents/?type=sales` - paid invoice transactions
- `/documents/?type=invoice` - invoices
- `/documents/customers/` - saved customers
- `/admin/` - Django administration
- `/health/` - deployment health check