# ============================================================
#  MODEL INFERENCE V3 — Multi-head (direção + tendência)
#  ALINHADO COM TRAINER V3.5 (hidden=128, layers=3, dropout=0.25)
# ============================================================

import os
import json
import torch
import pickle
import numpy as np
import pandas as pd

from app.ml.feature_engineer_V3 import FeatureEngineerV3
from app.ml.model_arch_V3 import ModelV3


class ModelInferenceV3:
    """
    Inferência multi-head:
      - direção (down/up)
      - tendência (down/up/range)
    """

    def __init__(self, symbol, variant="v3_multihead", seq_len=144):
        self.symbol = symbol
        self.variant = variant
        self.seq_len = seq_len

        # ROOT → api/
        self.ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.DATA_DIR = os.path.join(self.ROOT, "data")
        self.MODEL_DIR = os.path.join(self.DATA_DIR, "models")

        # ----------------------------------------------
        # LOAD METADATA
        # ----------------------------------------------
        meta_path = os.path.join(self.MODEL_DIR, f"{symbol}_{variant}_meta.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"[Inference] Metadata not found: {meta_path}")

        with open(meta_path, "r") as f:
            self.meta = json.load(f)

        self.feature_cols = self.meta["features"]
        self.input_size = len(self.feature_cols)
        self.seq_len = self.meta.get("seq_len", seq_len)

        # ----------------------------------------------
        # LOAD SCALER
        # ----------------------------------------------
        scaler_path = os.path.join(self.MODEL_DIR, f"{symbol}_{variant}_scaler.pkl")
        if not os.path.exists(scaler_path):
            raise FileNotFoundError(f"[Inference] Scaler not found: {scaler_path}")

        with open(scaler_path, "rb") as f:
            self.scaler = pickle.load(f)

        # ----------------------------------------------
        # LOAD MODEL
        # (mesma arquitetura usada no treino)
        # ----------------------------------------------
        model_path = os.path.join(self.MODEL_DIR, f"{symbol}_{variant}.pt")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"[Inference] Model .pt not found: {model_path}")

        self.model = ModelV3(
            input_size=self.input_size,
            hidden_size=128,        # <-- ALINHADO COM TRAINER V3.5
            num_layers=3,           # <-- ALINHADO COM TRAINER V3.5
            dropout=0.25            # <-- ALINHADO COM TRAINER V3.5
        )

        self.model.load_state_dict(torch.load(model_path, map_location="cpu"))
        self.model.eval()

        # Feature engineer
        self.fe = FeatureEngineerV3()

    # ------------------------------------------------------------
    # Pre-processamento dos dados brutos (raw → features → escala)
    # ------------------------------------------------------------
    def preprocess(self, df_raw: pd.DataFrame):

        df = self.fe.transform(df_raw.copy())

        missing = [c for c in self.feature_cols if c not in df.columns]
        if missing:
            raise ValueError(
                f"[Inference] Missing required feature columns: {missing}"
            )

        if len(df) < self.seq_len:
            raise ValueError(
                f"[Inference] Not enough data (need {self.seq_len}, have {len(df)})"
            )

        # cortar último segmento
        df = df.iloc[-self.seq_len:]

        # ordenar colunas corretamente
        features = df[self.feature_cols].values

        # escalar
        scaled = self.scaler.transform(features)

        # adicionar batch
        X = np.array([scaled], dtype=np.float32)

        return X

    # ------------------------------------------------------------
    # Inferência completa
    # ------------------------------------------------------------
    def predict(self, df_raw: pd.DataFrame):

        X = self.preprocess(df_raw)
        X = torch.tensor(X, dtype=torch.float32)

        with torch.no_grad():
            dir_logits, trend_logits = self.model(X)

        dir_probs = torch.softmax(dir_logits, dim=1).cpu().numpy()[0]
        trend_probs = torch.softmax(trend_logits, dim=1).cpu().numpy()[0]

        return {
            "direction_probs": dir_probs.tolist(),
            "trend_probs": trend_probs.tolist(),
            "direction": int(np.argmax(dir_probs)),
            "trend": int(np.argmax(trend_probs)),
        }
