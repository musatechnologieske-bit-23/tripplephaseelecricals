import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

production = (
    os.environ.get("DJANGO_ENV", "").lower() == "production"
    or bool(os.environ.get("RAILWAY_ENVIRONMENT"))
)


def env_bool(name, default):
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if production:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")
    SECRET_KEY = "local-development-only-change-before-deployment"

DEBUG = env_bool("DJANGO_DEBUG", not production)

allowed_hosts = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
if railway_domain and railway_domain not in allowed_hosts:
    allowed_hosts.append(railway_domain)
ALLOWED_HOSTS = allowed_hosts

csrf_origins = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if railway_domain:
    railway_origin = f"https://{railway_domain}"
    if railway_origin not in csrf_origins:
        csrf_origins.append(railway_origin)
CSRF_TRUSTED_ORIGINS = csrf_origins

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "core",
    "documents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

mysql_url = os.environ.get("MYSQL_URL", "").strip()
db_fields = {
    "NAME": os.environ.get("DB_NAME", "").strip(),
    "USER": os.environ.get("DB_USER", "").strip(),
    "PASSWORD": os.environ.get("DB_PASSWORD", ""),
    "HOST": os.environ.get("DB_HOST", "").strip(),
    "PORT": os.environ.get("DB_PORT", "3306").strip(),
}

if mysql_url:
    parsed_database_url = urlparse(mysql_url)
    if parsed_database_url.scheme not in {"mysql", "mysql+pymysql"}:
        raise ImproperlyConfigured("MYSQL_URL must use the mysql:// scheme.")
    database_name = unquote(parsed_database_url.path.lstrip("/"))
    if not all((database_name, parsed_database_url.hostname, parsed_database_url.username)):
        raise ImproperlyConfigured("MYSQL_URL must include a database, host, and user.")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": database_name,
            "USER": unquote(parsed_database_url.username),
            "PASSWORD": unquote(parsed_database_url.password or ""),
            "HOST": parsed_database_url.hostname,
            "PORT": str(parsed_database_url.port or 3306),
            "OPTIONS": {"charset": parse_qs(parsed_database_url.query).get("charset", ["utf8mb4"])[0]},
        }
    }
elif all(db_fields.values()):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            **db_fields,
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
elif production:
    raise ImproperlyConfigured("Set MYSQL_URL or all DB_NAME/DB_USER/DB_PASSWORD/DB_HOST values.")
elif any(db_fields[key] for key in ("NAME", "USER", "PASSWORD", "HOST")):
    raise ImproperlyConfigured("Set all DB_NAME/DB_USER/DB_PASSWORD/DB_HOST values, or none for local SQLite.")
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-ke"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedStaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", production)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
