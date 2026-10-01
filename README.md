# Tripple Phase Electricals

A Django application for creating, printing, and reporting on quotations and invoices for Tripple Phase Electricals Limited. Documents are entered directly; the app does not maintain a customer or product catalog.

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

## Tests

Run the Django test suite with the project's virtual environment active:

```bash
python manage.py test
```

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
- `/admin/` - Django administration
- `/health/` - deployment health check