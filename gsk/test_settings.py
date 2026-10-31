"""Settings for isolated GSK tests while teammate apps are unfinished.

Never use this module for production migrations. The real project uses
`yascn.User`; switching to Django's User here only lets the billing HTTP
contract be tested without creating substitute models in teammates' folders.
"""
from .settings import *  # noqa: F401,F403

INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ("yascn", "aliar")]
AUTH_USER_MODEL = "auth.User"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
