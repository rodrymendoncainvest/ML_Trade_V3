# model_inference_V3.py
# Inferência completa do modelo multi-head V3 (direção + tendência)

import os
import json
import torch
import pickle
import numpy as np
import pandas as pd

from ml.feature_engineer_V3 import FeatureEngineerV3
from ml.model_arch_V3 import ModelV3


class ModelInferenceV3:
    """
    Inferência multi-head:
      - direção (down/up)
      - tendência (down/up/range)

    Nota: o controlo de risco (risk_mode) é feito a jusante,
    no SignalEngineV3. Aqui só produzimos probabilidades limpas.
    """

    def __init__(self, symbol, variant="v3_multihead", seq_len=144):
        self.symbol = symbol
        self.variant = variant
        self.seq_len = seq_len

        # ROOT → api/
        self.ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.DATA_DIR = os.path.join(self.ROOT, "data")
        self.MODEL_DIR = os.path.join(self.DATA_DIR, "models")

        # carregar metadados
        meta_path = os.path.join(self.MODEL_DIR, f"{symbol}_{variant}_meta.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Metadata not found: {meta_path}")

        with open(meta_path, "r") as f:
            self.meta = json.load(f)

        # features usadas pelo modelo
        self.feature_cols = self.meta["features"]

        # scaler
        scaler_path = os.path.join(self.MODEL_DIR, f"{symbol}_{variant}_scaler.pkl")
        with open(scaler_path, "rb") as f:
            self.scaler = pickle.load(f)

        # modelo
        model_path = os.path.join(self.MODEL_DIR, f"{symbol}_{variant}.pt")
        self.model = ModelV3(
            input_size=len(self.feature_cols),
            hidden_size=64,
            num_layers=2,
            dropout=0.15,
        )

        self.model.load_state_dict(torch.load(model_path, map_location="cpu"))
        self.model.eval()

        # feature engineer
        self.fe = FeatureEngineerV3()

    # ------------------------------------------------------------
    # Preprocess (constrói X sequencial)
    # ------------------------------------------------------------
    def preprocess(self, df_raw: pd.DataFrame):
        df = self.fe.transform(df_raw.copy())

        # garantir que temos suficientes barras
        if len(df) < self.seq_len:
            raise ValueError(
                f"Not enough data for inference (need {self.seq_len}, have {len(df)})"
            )

        df = df.iloc[-self.seq_len:]  # últimas seq_len barras

        # normalizar features
        # IMPORTANTE: usar .values para evitar o aviso do sklearn
        features = df[self.feature_cols].values  # (seq_len, n_features)
        df_scaled = self.scaler.transform(features)

        X = np.array([df_scaled], dtype=np.float32)  # (1, seq_len, features)

        return X

    # ------------------------------------------------------------
    # Inferência
    # ------------------------------------------------------------
    def predict(self, df_raw: pd.DataFrame):
        X = self.preprocess(df_raw)
        X = torch.tensor(X, dtype=torch.float32)

        with torch.no_grad():
            dir_logits, trend_logits = self.model(X)

        dir_probs = torch.softmax(dir_logits, dim=1).cpu().numpy()[0]
        trend_probs = torch.softmax(trend_logits, dim=1).cpu().numpy()[0]

        direction = int(np.argmax(dir_probs))
        trend = int(np.argmax(trend_probs))

        return {
            "direction_probs": dir_probs.tolist(),
            "trend_probs": trend_probs.tolist(),
            "direction": direction,   # 0=down, 1=up
            "trend": trend            # 0=down,1=up,2=range
        }
