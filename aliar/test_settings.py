"""Finance verification with the real YASCN models and a fresh test database.

Never use these in-memory database settings for a persistent demo server.
"""

from gsk.settings import *  # noqa: F403,F401

ROOT_URLCONF = "aliar.test_urls"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
