from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


DEBUG = False

if SECRET_KEY == "dev-insecure-change-me":  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY deve ser definido em producao.")

if not ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS deve ser definido em producao.")
