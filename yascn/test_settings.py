"""Run Phase 1 independently while the ALIAR handoff is missing.

Usage: .venv/bin/python manage.py test yascn --settings=yascn.test_settings
"""
import os

from gsk.settings import *  # noqa: F403

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "aliar"]  # noqa: F405
ROOT_URLCONF = "yascn.test_urls"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.environ.get("YASCN_DB_PATH", ":memory:")}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
