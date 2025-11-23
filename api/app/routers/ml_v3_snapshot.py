# ============================================================
#  ML_V3 SNAPSHOT — Inferência rápida do modelo treinado
# ============================================================

from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
import joblib
import torch

from app.ml.feature_engineer_V3 import FeatureEngineerV3
from app.ml.data_manager import DataManager
from app.ml.model_inference_V3 import ModelInferenceV3
from app.ml.signal_engine_V3 import SignalEngineV3


router = APIRouter(prefix="/ml_v3", tags=["ML_V3_SNAPSHOT"])


# ------------------------------------------------------------
# RESPONSE
# ------------------------------------------------------------
class SnapshotResponse(BaseModel):
    ok: bool
    signal: str
    prob_up: float
    last_close: float
    detail: str | None = None


# ------------------------------------------------------------
# /snapshot — devolve inferência instantânea usando o modelo treinado
# ------------------------------------------------------------
@router.get("/snapshot", response_model=SnapshotResponse)
async def ml_snapshot(symbol: str):

    dm = DataManager()

    clean_path = os.path.join(dm.CLEAN_DIR, f"{symbol}_1H_clean.csv")
    if not os.path.exists(clean_path):
        return SnapshotResponse(
            ok=False,
            signal="none",
            prob_up=0.5,
            last_close=0.0,
            detail="Clean dataset não encontrado. Corre o TREINO primeiro."
        )

    df_clean = pd.read_csv(clean_path, index_col=0)
    df_clean.index = pd.to_datetime(df_clean.index)

    # FEATURE ENGINEERING
    fe = FeatureEngineerV3()
    df_fe = fe.transform(df_clean)

    # MODEL INFERENCE
    infer = ModelInferenceV3(symbol)
    out = infer.predict(df_fe)

    # SIGNAL
    se = SignalEngineV3()
    signal = se.generate_signal(out)

    return SnapshotResponse(
        ok=True,
        signal=signal["signal"],
        prob_up=float(signal["prob_up"]),
        last_close=float(out["last_close"]),
        detail=signal.get("detail")
    )
