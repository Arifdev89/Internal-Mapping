
import os
from pathlib import Path

from dotenv import load_dotenv




BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")




SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "dev-only-insecure-key",
)

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]




INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "navigator.apps.NavigatorConfig",
]



MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]




ROOT_URLCONF = "indoor_navigation.urls"

WSGI_APPLICATION = "indoor_navigation.wsgi.application"




TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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



DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",

        "NAME": os.getenv(
            "DB_NAME",
            "indoor_navigation",
        ),

        "USER": os.getenv(
            "DB_USER",
            "nav_user",
        ),

        "PASSWORD": os.getenv(
            "DB_PASSWORD",
            "",
        ),

        "HOST": os.getenv(
            "DB_HOST",
            "127.0.0.1",
        ),

        "PORT": os.getenv(
            "DB_PORT",
            "3306",
        ),

        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": (
                "SET sql_mode='STRICT_TRANS_TABLES'"
            ),
        },
    }
}




AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]



LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True



STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"



DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"



ORS_API_KEY = os.getenv(
    "ORS_API_KEY",
    "",
)

ORS_BASE_URL = os.getenv(
    "ORS_BASE_URL",
    "https://api.openrouteservice.org",
)




OSM_NOMINATIM_SEARCH_URL = (
    "https://nominatim.openstreetmap.org/search"
)

OSM_NOMINATIM_USER_AGENT = os.getenv(
    "OSM_NOMINATIM_USER_AGENT",
    "HybridNavigator/1.0 (contact: YOUR_EMAIL)",
)


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "hybrid-navigator-cache",
        "TIMEOUT": 3600,
    }
}




SECURE_REFERRER_POLICY = (
    "strict-origin-when-cross-origin"
)
