from __future__ import annotations

import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from celery import Celery


def ensure_rediss_ssl(url: str | None) -> str | None:
    if not url:
        return url

    if url.startswith("rediss://"):
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query))

        if "ssl_cert_reqs" not in query:
            query["ssl_cert_reqs"] = "CERT_NONE"

        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urlencode(query),
                parsed.fragment,
            )
        )

    return url


def make_celery() -> Celery:
    broker_url = (
        os.getenv("CELERY_BROKER_URL")
        or os.getenv("REDIS_URL")
        or "redis://localhost:6379/0"
    )

    result_backend = (
        os.getenv("CELERY_RESULT_BACKEND")
        or os.getenv("REDIS_URL")
        or "redis://localhost:6379/0"
    )

    broker_url = ensure_rediss_ssl(broker_url)
    result_backend = ensure_rediss_ssl(result_backend)

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

    if broker_url and broker_url.startswith("rediss://"):
        celery_app.conf.broker_use_ssl = {
            "ssl_cert_reqs": "CERT_NONE",
        }

    if result_backend and result_backend.startswith("rediss://"):
        celery_app.conf.redis_backend_use_ssl = {
            "ssl_cert_reqs": "CERT_NONE",
        }

    return celery_app


celery_app = make_celery()
