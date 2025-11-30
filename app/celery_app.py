"""
Celery application configuration.
"""

from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "aiqso_seo",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
)
