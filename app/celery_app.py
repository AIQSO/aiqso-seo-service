"""
Celery application configuration with beat scheduling.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings
from app.logging_config import configure_logging

settings = get_settings()
configure_logging(level=settings.log_level, json_logs=settings.log_json)

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

# Celery Beat Schedule for automated audits
celery_app.conf.beat_schedule = {
    # Daily audit for internal sites (aiqso.io) at 6 AM UTC
    "daily-internal-audit": {
        "task": "app.tasks.scheduled_internal_audit",
        "schedule": crontab(hour=6, minute=0),
        "args": (),
    },
    # Weekly full audit for all active customer websites on Sunday at 2 AM UTC
    "weekly-customer-audits": {
        "task": "app.tasks.scheduled_customer_audits",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
        "args": (),
    },
    # Hourly check for scheduled audits (customer-configured schedules)
    "process-scheduled-audits": {
        "task": "app.tasks.process_scheduled_audits",
        "schedule": crontab(minute=0),  # Every hour at :00
        "args": (),
    },
    # Daily score tracking (store historical scores)
    "daily-score-snapshot": {
        "task": "app.tasks.capture_daily_scores",
        "schedule": crontab(hour=0, minute=30),  # 12:30 AM UTC
        "args": (),
    },
    # Check for score drops and send alerts
    "score-drop-monitor": {
        "task": "app.tasks.monitor_score_drops",
        "schedule": crontab(hour="*/6"),  # Every 6 hours
        "args": (),
    },
}
