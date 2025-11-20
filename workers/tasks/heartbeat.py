from datetime import datetime
from workers.app import celery_app

@celery_app.task(name="heartbeat.ping")
def heartbeat() -> dict:
    return {"ts": datetime.utcnow().isoformat() + "Z"}
