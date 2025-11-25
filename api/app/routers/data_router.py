# ============================================================
# DATA ROUTER — Download e Clean alinhados com a estrutura real
# ============================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import pandas as pd
import traceback

from app.ml.data_downloader import download_1h
from app.ml.data_manager import DataManager

router = APIRouter(prefix="/data", tags=["DATA"])

# ============================================================
# CAMINHOS CORRETOS (AJUSTADOS)
# ============================================================
# Estrutura real do teu projeto:
# ML_Trade/api/data/history
# ML_Trade/api/data/clean

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DIR = os.path.join(ROOT_DIR, "data", "history")
CLEAN_DIR = os.path.join(ROOT_DIR, "data", "clean")

# Garantir que as pastas existem
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(CLEAN_DIR, exist_ok=True)

dm = DataManager()


# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------
def safe_exec(operation, func):
    try:
        return func()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{operation} failed: {str(e)}")


# ------------------------------------------------------------
# Request Models
# ------------------------------------------------------------
class DataRequest(BaseModel):
    symbol: str


# ------------------------------------------------------------
# /data/download — descarrega RAW e guarda CSV
# ------------------------------------------------------------
@router.post("/download")
def download_raw(req: DataRequest):

    def run():
        symbol = req.symbol.upper()

        df = download_1h(symbol)

        path = os.path.join(RAW_DIR, f"{symbol}_1H.csv")
        df.to_csv(path)

        return {
            "ok": True,
            "symbol": symbol,
            "rows": len(df),
            "path": path,
        }

    return safe_exec("download", run)


# ------------------------------------------------------------
# /data/clean — cria CLEAN dataset a partir do RAW
# ------------------------------------------------------------
@router.post("/clean")
def clean_symbol(req: DataRequest):

    def run():
        symbol = req.symbol.upper()

        # Limpeza REAL usando o DataManager
        df_clean = dm.clean_symbol(symbol, tf="1H")

        clean_path = os.path.join(CLEAN_DIR, f"{symbol}_1H_clean.csv")

        if not os.path.exists(clean_path):
            raise FileNotFoundError(f"Clean file not generated: {clean_path}")

        return {
            "ok": True,
            "symbol": symbol,
            "rows": len(df_clean),
            "path": clean_path,
        }

    return safe_exec("clean", run)


# ------------------------------------------------------------
# /data/get_raw — devolve raw como JSON
# ------------------------------------------------------------
@router.get("/get_raw")
def get_raw(symbol: str):

    def run():
        symbol_u = symbol.upper()
        path = os.path.join(RAW_DIR, f"{symbol_u}_1H.csv")

        if not os.path.exists(path):
            raise FileNotFoundError(f"RAW data not found: {path}")

        df = pd.read_csv(path, index_col=0)
        df.index = pd.to_datetime(df.index)

        return {
            "ok": True,
            "symbol": symbol_u,
            "data": df.tail(1500).to_dict(orient="records"),
        }

    return safe_exec("get_raw", run)


# ------------------------------------------------------------
# /data/get_clean — devolve clean como JSON
# ------------------------------------------------------------
@router.get("/get_clean")
def get_clean(symbol: str):

    def run():
        symbol_u = symbol.upper()
        path = os.path.join(CLEAN_DIR, f"{symbol_u}_1H_clean.csv")

        if not os.path.exists(path):
            raise FileNotFoundError(f"Clean data not found: {path}")

        df = pd.read_csv(path, index_col=0)
        df.index = pd.to_datetime(df.index)

        return {
            "ok": True,
            "symbol": symbol_u,
            "data": df.tail(1500).to_dict(orient="records"),
        }

    return safe_exec("get_clean", run)


# ------------------------------------------------------------
# /data/list — lista símbolos disponíveis no disco
# ------------------------------------------------------------
@router.get("/list")
def list_data():

    def run():
        raw_files = os.listdir(RAW_DIR) if os.path.exists(RAW_DIR) else []
        clean_files = os.listdir(CLEAN_DIR) if os.path.exists(CLEAN_DIR) else []

        def extract(f):
            return f.replace("_1H.csv", "").replace("_1H_clean.csv", "")

        raw_syms = {extract(f) for f in raw_files}
        clean_syms = {extract(f) for f in clean_files}

        return {
            "ok": True,
            "raw": sorted(list(raw_syms)),
            "clean": sorted(list(clean_syms)),
        }

    return safe_exec("list", run)
