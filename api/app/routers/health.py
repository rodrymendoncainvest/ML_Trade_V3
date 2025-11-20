from fastapi import APIRouter
import os
import time

router = APIRouter()

START_TS = time.time()

@router.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_sec": round(time.time() - START_TS, 1),
        "env": {
            "EODHD_KEY_present": bool(os.getenv("EODHD_KEY")),
            "TWELVE_DATA_KEY_present": bool(os.getenv("TWELVE_DATA_KEY")),
            "YF_RANGE_60M": os.getenv("YF_RANGE_60M", "7d"),
            "YF_RANGE_SUBH": os.getenv("YF_RANGE_SUBH", "5d"),
            "INTRADAY_CACHE_TTL": int(os.getenv("INTRADAY_CACHE_TTL", "90")),
        }
    }

@router.get("/readyz")
def readyz():
    # hook futuro: checks a disco, cache externa, etc.
    return {"ready": True}
