from __future__ import annotations

import os
from celery import Celery


def make_celery() -> Celery:
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    celery_app = Celery(
        "dna_analysis_tasks",
        broker=broker_url,
        backend=result_backend,
        include=["tasks.analysis_tasks"],
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        result_expires=3600,
    )

    return celery_app


celery_app = make_celery()
