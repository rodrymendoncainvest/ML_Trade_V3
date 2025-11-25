# api/app/main.py
# -------------------------------------------------------------
# FastAPI principal + routers estáveis
# -------------------------------------------------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers funcionais / não-ML
from app.routers import quotes, signals, dataset, news
from app.routers import signals_mtf

# Nova arquitetura ML
from app.routers import data_router
from app.routers import ml_core


# -------------------------------------------------------------
# APP
# -------------------------------------------------------------
app = FastAPI(
    title="ML Trade API",
    version="2.0.0",
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
# INCLUDE ROUTERS (APENAS OS ATUAIS E FUNCIONAIS)
# -------------------------------------------------------------
app.include_router(quotes.router)
app.include_router(signals.router)
app.include_router(signals_mtf.router)
app.include_router(dataset.router)
app.include_router(news.router)

# --- NOVO PIPELINE MODERNO ---
app.include_router(data_router.router)   # Download & Clean
app.include_router(ml_core.router)       # Treino / Inferência / Backtest

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
            "/data/*",
            "/ml_core/*",
        ],
    }
