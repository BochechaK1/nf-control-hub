from .base import *  # noqa: F403


DEBUG = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

if env_bool("NFCH_ALLOW_SQLITE_TESTS", False):  # noqa: F405
    DATABASES = {  # noqa: F405
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": env("NFCH_SQLITE_NAME", str(BASE_DIR / "local_preview.sqlite3")),  # noqa: F405
        }
    }
else:
    DATABASES["default"]["TEST"] = {"NAME": env("POSTGRES_TEST_DB", "test_nf_control_hub")}  # noqa: F405
