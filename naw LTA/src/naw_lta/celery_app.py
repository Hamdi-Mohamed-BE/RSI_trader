from celery import Celery
from celery.schedules import schedule

from .settings import settings


celery_app = Celery(
    "naw_lta",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["naw_lta.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "scan-enabled-market": {
            "task": "naw_lta.scan_market",
            "schedule": schedule(15.0),
        }
    },
)
