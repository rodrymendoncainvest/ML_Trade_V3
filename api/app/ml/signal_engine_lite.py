# signal_engine_lite.py

import os
import pandas as pd
from datetime import datetime
from ml.model_inference_lite import ModelInferenceLite


class SignalEngineLite:

    def __init__(self, symbol: str):

        # símbolo tal como existe no disco e nos modelos
        self.symbol = symbol
        self.model_key = f"{symbol}_lite"

        # caminho BASE fixo: api/data/clean
        base_data = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",   # sair de ml
                "..",   # sair de app → estamos em api
                "data",
                "clean"
            )
        )

        # FICHEIRO LIMPO → SEM SUBSTITUIR PONTOS
        filename = f"{symbol}_1H_clean.csv"

        self.data_path = os.path.join(base_data, filename)

        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"CSV limpo não encontrado: {self.data_path}")

        # carregar modelo
        self.infer = ModelInferenceLite(model_key=self.model_key)

    # ---------------------------------------------------------------
    def load_data(self):
        return pd.read_csv(self.data_path, index_col=0, parse_dates=True)

    @staticmethod
    def class_to_action(pred_class: int):
        if pred_class in [0, 1]:
            return "vende"
        elif pred_class == 2:
            return "mantém"
        return "compra"

    # ---------------------------------------------------------------
    def generate_signal(self, seq_len=50):
        df = self.load_data()
        result = self.infer.predict(df, seq_len=seq_len)

        return {
            "symbol": self.symbol,
            "action": self.class_to_action(result["class"]),
            "class": result["class"],
            "confidence": float(max(result["probs"])),
            "probabilities": result["probs"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
