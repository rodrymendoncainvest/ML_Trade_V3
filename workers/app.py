import os
from celery import Celery

BROKER_URL = os.getenv("BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")
RESULT_BACKEND = os.getenv("RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery("workers", broker=BROKER_URL, backend=RESULT_BACKEND)
celery_app.autodiscover_tasks(["tasks"])
