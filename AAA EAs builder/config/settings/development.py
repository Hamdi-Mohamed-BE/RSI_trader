from .base import *  # noqa: F403

DEBUG = True
GENERATION_RUN_INLINE = env.bool("GENERATION_RUN_INLINE", default=True)  # noqa: F405
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
}
