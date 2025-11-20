# api/app/main.py
# -------------------------------------------------------------
# FastAPI principal + routers estáveis
# -------------------------------------------------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.routers import quotes, signals, dataset, news
from app.routers import signals_mtf   # <-- NOVO MTF IMPORT

app = FastAPI(
    title="ML Trade API",
    version="1.1.0",
)

# -------------------------------------------------------------
# CORS universal
# -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# REGISTAR OS ROUTERS
# -------------------------------------------------------------
app.include_router(quotes.router)
app.include_router(signals.router)
app.include_router(signals_mtf.router)     # <-- MTF ativo aqui
app.include_router(dataset.router)
app.include_router(news.router)

# -------------------------------------------------------------
# Raiz (debug)
# -------------------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "ML Trade API",
        "active_endpoints": [
            "/quotes/*",
            "/signals/*",
            "/dataset/*",
            "/news/*",
        ],
        "mtf": "/signals/mtf",
    }
