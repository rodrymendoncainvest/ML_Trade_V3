from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.providers.quotes import get_ohlc
from app.ml.features import build_features, feature_columns
from app.ml.labels import make_binary_labels
from app.ml.registry import (
    model_key,
    save_model,
    list_models,
    load_model,
)

from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score

router = APIRouter(prefix="/ml", tags=["ml"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TrainRequest(BaseModel):
    symbol: str
    tf: str = "1d"
    limit: int = 1200
    eps: float = 0.002


class PredictRequest(BaseModel):
    symbol: str
    tf: str = "1d"
    limit: int = 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_dataset(symbol: str, tf: str, limit: int) -> pd.DataFrame:
    df = get_ohlc(symbol=symbol, tf=tf, limit=limit)
    return df


def _build_xy(df: pd.DataFrame, eps: float) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    feats = build_features(df)
    y = make_binary_labels(feats, eps=eps)
    feats = feats.iloc[:-1]
    y = y.dropna()
    feats = feats.loc[y.index]
    cols = [c for c in feats.columns if c not in ("ts", "symbol")]
    X = feats[cols]
    return X, y.astype(int), cols


def _select_and_fit_model(X: pd.DataFrame, y: pd.Series) -> Tuple[Any, Dict[str, Any]]:
    models = {
        "logreg": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]),
        "rf": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("clf", RandomForestClassifier(
                n_estimators=300,
                max_depth=6,
                min_samples_leaf=3,
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=42,
            )),
        ]),
        "gbrt": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("clf", GradientBoostingClassifier(
                n_estimators=400,
                learning_rate=0.03,
                max_depth=2,
                random_state=42,
            )),
        ]),
    }

    tscv = TimeSeriesSplit(n_splits=5)
    best_name, best_model, best_score = None, None, -np.inf

    for name, est in models.items():
        scores = []
        for train_idx, val_idx in tscv.split(X):
            est.fit(X.iloc[train_idx], y.iloc[train_idx])
            pred = est.predict(X.iloc[val_idx])
            scores.append(accuracy_score(y.iloc[val_idx], pred))
        mean_acc = np.mean(scores)
        if mean_acc > best_score:
            best_name, best_model, best_score = name, est, mean_acc

    best_model.fit(X, y)
    metrics = {"model": best_name, "cv_acc_mean": float(best_score)}
    return best_model, metrics


def _predict_proba(model: Any, feats: pd.DataFrame, cols: List[str]) -> np.ndarray:
    missing = [c for c in cols if c not in feats.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Colunas em falta para previsão: {missing}",
        )
    X = feats[cols]
    proba_fn = getattr(model, "predict_proba", None)
    if proba_fn is None:
        decision = model.decision_function(X)
        p1 = 1.0 / (1.0 + np.exp(-decision))
        return np.column_stack([1.0 - p1, p1])
    return model.predict_proba(X)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/train")
def train(req: TrainRequest):
    df = _fetch_dataset(req.symbol, req.tf, req.limit)
    if df is None or df.empty:
        raise HTTPException(status_code=400, detail="Sem dados")

    X, y, cols = _build_xy(df, eps=req.eps)
    model, metrics = _select_and_fit_model(X, y)

    key = model_key(req.symbol, req.tf)
    as_of = int(pd.to_datetime(df["ts"].iloc[-1]).timestamp())

    meta = {
        "symbol": req.symbol.upper(),
        "tf": req.tf,
        "features": cols,
        "as_of": as_of,
        "metrics": metrics,
    }

    save_model(key, model, meta)
    return {"ok": True, "key": key, "meta": meta}


@router.get("/signal")
def signal(symbol: str, tf: str = "1d"):
    key = model_key(symbol, tf)
    try:
        model, meta, _ = load_model(key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")

    df = _fetch_dataset(symbol, tf, 400)
    if df is None or df.empty:
        raise HTTPException(status_code=400, detail="Sem dados OHLC")

    feats = build_features(df)
    cols = meta.get("features", [c for c in feats.columns if c not in ("ts", "symbol")])

    proba = _predict_proba(model, feats.tail(1), cols)
    p_up = float(proba[-1, 1]) if len(proba) else 0.5

    return {
        "ok": True,
        "key": key,
        "signal": {
            "proba_up": p_up,
            "signal": "long" if p_up >= 0.55 else "cash",
            "last_close": float(df["close"].iloc[-1]),
        },
        "meta": meta,
    }
