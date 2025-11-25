# ============================================================
#  ML_CORE — Pipeline V4 FINAL
#  Download → Clean → Train (PatchTST) → Predict → Backtest
# ============================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import os
import traceback

# DATA
from app.routers.data_router import download_raw, clean_symbol

# ML Core modules
from app.ml_core.feature_engineer_core import FeatureEngineerCore
from app.ml_core.dataset_builder_core import DatasetBuilderCore
from app.ml_core.trainer_core import TrainerCore
from app.ml_core.inference_core import InferenceCore
from app.ml_core.backtester_core import BacktesterCore

# Config
from app.ml_core.config_core import SEQ_LEN, FEATURE_ORDER


# ============================================================
#  ROUTER
# ============================================================
router = APIRouter(prefix="/ml_core", tags=["MLCore"])


# ============================================================
#  PATHS
# ============================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
CLEAN_DIR = os.path.join(DATA_DIR, "clean")

os.makedirs(CLEAN_DIR, exist_ok=True)


# ============================================================
#  REQUEST MODEL
# ============================================================
class TrainRequest(BaseModel):
    symbol: str


# ============================================================
#  SAFE WRAPPER
# ============================================================
def _safe(name, fn):
    try:
        return fn()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{name} failed: {str(e)}")


# ============================================================
#  TRAIN
# ============================================================
@router.post("/train")
def train_model(req: TrainRequest):
    def run():
        symbol = req.symbol.upper()
        clean_file = os.path.join(CLEAN_DIR, f"{symbol}_1H_clean.csv")

        if not os.path.exists(clean_file):
            raise FileNotFoundError(f"CLEAN dataset missing: {clean_file}")

        df = pd.read_csv(clean_file, index_col=0)
        df.index = pd.to_datetime(df.index)

        fe = FeatureEngineerCore()
        df_fe = fe.transform(df)

        ds = DatasetBuilderCore()
        X, y = ds.build(df_fe)

        trainer = TrainerCore(symbol)
        trainer.load_data(X, y, X, y)
        trainer.train()

        return {"ok": True, "symbol": symbol, "samples": len(X)}

    return _safe("train", run)


# ============================================================
#  PREDICT
# ============================================================
@router.get("/predict")
def predict_model(symbol: str):
    def run():
        symbol_u = symbol.upper()
        clean_file = os.path.join(CLEAN_DIR, f"{symbol_u}_1H_clean.csv")

        if not os.path.exists(clean_file):
            raise FileNotFoundError(f"CLEAN dataset missing: {clean_file}")

        df = pd.read_csv(clean_file, index_col=0)
        df.index = pd.to_datetime(df.index)

        fe = FeatureEngineerCore()
        df_fe = fe.transform(df)

        arr = df_fe[FEATURE_ORDER].values
        if len(arr) < SEQ_LEN:
            raise ValueError("Not enough data.")

        seq = arr[-SEQ_LEN:]

        infer = InferenceCore(symbol_u)
        out = infer.predict_with_signal(seq)

        return {"ok": True, "symbol": symbol_u, **out}

    return _safe("predict", run)


# ============================================================
#  BACKTEST
# ============================================================
@router.get("/backtest")
def backtest(symbol: str):
    def run():
        symbol_u = symbol.upper()
        clean_file = os.path.join(CLEAN_DIR, f"{symbol_u}_1H_clean.csv")

        if not os.path.exists(clean_file):
            raise FileNotFoundError(f"CLEAN dataset missing: {clean_file}")

        df = pd.read_csv(clean_file, index_col=0)
        df.index = pd.to_datetime(df.index)

        bt = BacktesterCore(symbol_u)
        result = bt.run(df)

        return {"ok": True, "symbol": symbol_u, **result}

    return _safe("backtest", run)


# ============================================================
#  FULL PIPELINE
#  Download → Clean → Train → Predict → Backtest
# ============================================================
@router.post("/full_pipeline")
def full_pipeline(req: TrainRequest):
    def run():
        symbol = req.symbol.upper()

        # 1) DOWNLOAD RAW
        download_raw(req)

        # 2) CLEAN
        clean_symbol(req)

        clean_file = os.path.join(CLEAN_DIR, f"{symbol}_1H_clean.csv")
        if not os.path.exists(clean_file):
            raise FileNotFoundError("CLEAN data not generated.")

        df = pd.read_csv(clean_file, index_col=0)
        df.index = pd.to_datetime(df.index)

        # 3) FEATURE ENGINEERING
        fe = FeatureEngineerCore()
        df_fe = fe.transform(df)

        # 4) DATASET
        ds = DatasetBuilderCore()
        X, y = ds.build(df_fe)

        # 5) TRAIN
        trainer = TrainerCore(symbol)
        trainer.load_data(X, y, X, y)
        trainer.train()

        # 6) PREDICT snapshot
        seq = df_fe[FEATURE_ORDER].values[-SEQ_LEN:]
        infer = InferenceCore(symbol)
        snapshot = infer.predict_with_signal(seq)

        # 7) BACKTEST
        bt = BacktesterCore(symbol)
        backtest_result = bt.run(df)

        return {
            "ok": True,
            "symbol": symbol,
            "snapshot": snapshot,
            "backtest": backtest_result
        }

    return _safe("full_pipeline", run)
