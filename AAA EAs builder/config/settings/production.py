from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
GENERATION_RUN_INLINE = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if SECRET_KEY == "dev-only-change-before-production":  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")
if not MODEL_CONFIG_ENCRYPTION_KEY:  # noqa: F405
    raise ImproperlyConfigured("MODEL_CONFIG_ENCRYPTION_KEY must be set in production.")
