import os
import time
from fastapi import APIRouter, Request
from app.utils.debug_state import get_errors

router = APIRouter(prefix="/_debug", tags=["_debug"])

def _dbg() -> bool:
    return str(os.getenv("DEBUG", "")).lower() in ("1", "true", "yes", "on")

@router.get("/health")
def health():
    return {"ok": True, "debug": _dbg(), "ts": int(time.time())}

@router.get("/config")
def config():
    return {"DEBUG": _dbg(), "LOG_LEVEL": os.getenv("LOG_LEVEL", "")}

@router.get("/errors")
def errors(limit: int = 50):
    errs = get_errors(limit)
    return {"count": len(errs), "errors": errs}

@router.get("/echo")
def echo(request: Request):
    return {
        "rid": getattr(request.state, "rid", None),
        "method": request.method,
        "path": request.url.path,
        "query": str(request.url.query),
        "headers": dict(request.headers),
    }
