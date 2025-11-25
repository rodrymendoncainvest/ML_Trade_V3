# ============================================================
#  ML_Trade V4 — INFERENCE CORE (compatível PatchTST)
#  - Carrega scaler por símbolo
#  - Carrega PatchTST por símbolo
#  - Produz output achatado
# ============================================================

import os
import json
import torch
import pickle
import numpy as np

from .model_core import ModelCore
from .config_core import (
    MODELS_DIR,
    SCALERS_DIR,
    META_DIR,
    SEQ_LEN,
    NUM_FEATURES,
    BASE_THRESHOLD,
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ============================================================
#  Signal Engine (versão achatada)
# ============================================================

class SignalEngineCore:
    """Converte retorno previsto → sinal (-1, 0, 1)"""

    def __init__(self, threshold=BASE_THRESHOLD):
        self.threshold = threshold

    def generate(self, predicted_return: float):
        if predicted_return > self.threshold:
            return 1, float(predicted_return)

        if predicted_return < -self.threshold:
            return -1, float(predicted_return)

        return 0, float(predicted_return)


# ============================================================
#  Inference Core
# ============================================================

class InferenceCore:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.tf = "1H"

        # Caminhos finais
        self.model_path = os.path.join(MODELS_DIR, f"{self.symbol}_{self.tf}_model.pt")
        self.scaler_path = os.path.join(SCALERS_DIR, f"{self.symbol}_{self.tf}_scaler.pkl")
        self.meta_path = os.path.join(META_DIR, f"{self.symbol}_{self.tf}_meta.json")

        # Verificações
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Modelo não encontrado: {self.model_path}")

        if not os.path.exists(self.scaler_path):
            raise FileNotFoundError(f"Scaler não encontrado: {self.scaler_path}")

        if not os.path.exists(self.meta_path):
            raise FileNotFoundError(f"Meta não encontrada: {self.meta_path}")

        # META (não vital mas útil)
        with open(self.meta_path, "r") as f:
            self.meta = json.load(f)

        # SCALER
        with open(self.scaler_path, "rb") as f:
            self.scaler = pickle.load(f)

        # MODELO PatchTST
        self.model = ModelCore().to(device)
        self.model.load_state_dict(torch.load(self.model_path, map_location=device))
        self.model.eval()

        # Engine de sinal
        self.signals = SignalEngineCore()

    # ------------------------------------------------------------
    # Preparação da sequência
    # ------------------------------------------------------------
    def _prepare_sequence(self, seq_array):
        """
        seq_array shape esperado: (SEQ_LEN, NUM_FEATURES)
        """
        if seq_array.shape != (SEQ_LEN, NUM_FEATURES):
            raise ValueError(
                f"Esperado shape ({SEQ_LEN}, {NUM_FEATURES}), recebido {seq_array.shape}"
            )

        seq_scaled = self.scaler.transform(seq_array)
        seq_scaled = np.expand_dims(seq_scaled, axis=0)  # batch = 1

        return torch.tensor(seq_scaled, dtype=torch.float32).to(device)

    # ------------------------------------------------------------
    # Previsão pura
    # ------------------------------------------------------------
    def predict(self, seq_array):
        x = self._prepare_sequence(seq_array)

        with torch.no_grad():
            pred = self.model(x)

        return float(pred.cpu().numpy()[0, 0])

    # ------------------------------------------------------------
    # Previsão + Sinal → formato achatado
    # ------------------------------------------------------------
    def predict_with_signal(self, seq_array):
        predicted_return = self.predict(seq_array)

        signal, strength = self.signals.generate(predicted_return)

        return {
            "predicted_return": predicted_return,
            "signal": signal,
            "signal_strength": strength,
        }
