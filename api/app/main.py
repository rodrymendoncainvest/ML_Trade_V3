# api/app/main.py
# -------------------------------------------------------------
# FastAPI principal + routers estáveis
# -------------------------------------------------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.routers import quotes, signals, dataset, news
from app.routers import signals_mtf            # MTF
from app.routers import ml_v3                  # ML V3 REST
from app.routers import ml_v3_sse              # ML V3 SSE (pipeline completo)
from app.routers import ml_v3_snapshot         # ML V3 Snapshot (novo)


# -------------------------------------------------------------
# APP
# -------------------------------------------------------------
app = FastAPI(
    title="ML Trade API",
    version="1.1.0",
)

# -------------------------------------------------------------
# CORS
# -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# INCLUDE ROUTERS (todos os existentes + SSE + snapshot)
# -------------------------------------------------------------
app.include_router(quotes.router)
app.include_router(signals.router)
app.include_router(signals_mtf.router)
app.include_router(dataset.router)
app.include_router(news.router)

# ML V3
app.include_router(ml_v3.router)          # REST
app.include_router(ml_v3_sse.router)      # SSE pipeline
app.include_router(ml_v3_snapshot.router) # Snapshot novo

# -------------------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "ML Trade API",
        "active_endpoints": [
            "/quotes/*",
            "/signals/*",
            "/signals/mtf",
            "/dataset/*",
            "/news/*",
            "/ml_v3/*",        # REST
            "/ml_v3/full_run_sse",  # SSE FULL PIPELINE
        ],
    }
