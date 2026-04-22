from celery import Celery
from .config import settings

celery_app = Celery(
    "video_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "video_service.tasks.transcode_video": {"queue": "video_transcoding"},
        "video_service.tasks.generate_subtitles": {"queue": "video_processing"},
    },
)
