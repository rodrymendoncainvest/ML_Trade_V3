# ml/model_inference_lite.py

import os
import torch
import pandas as pd
import numpy as np
import joblib

from ml.lstm_model_lite import LSTMLiteModel
from ml.dataset_builder_lite import DatasetBuilderLite


class ModelInferenceLite:

    def __init__(self, model_key: str):

        base = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "models")
        )

        self.model_path = os.path.join(base, f"{model_key}.pt")
        self.scaler_path = os.path.join(base, f"{model_key}_scaler.pkl")
        self.features_path = os.path.join(base, f"{model_key}_features.txt")

        # carregar scaler
        if not os.path.exists(self.scaler_path):
            raise FileNotFoundError(f"Scaler não encontrado: {self.scaler_path}")
        self.scaler = joblib.load(self.scaler_path)

        # carregar features
        if not os.path.exists(self.features_path):
            raise FileNotFoundError(f"Features não encontradas: {self.features_path}")
        with open(self.features_path, "r") as f:
            self.feature_cols = [x.strip() for x in f.readlines()]

        # modelo
        input_size = len(self.feature_cols)
        num_classes = 5

        self.model = LSTMLiteModel(input_size=input_size, num_classes=num_classes)
        self.model.load_state_dict(torch.load(self.model_path, map_location="cpu"))
        self.model.eval()

        # builder para replicar feature engineering
        self.builder = DatasetBuilderLite()

        print(f"Modelo carregado: {self.model_path}")

    # ---------------------------------------------------------------
    # Preprocessamento completo (igual ao treino)
    # ---------------------------------------------------------------
    def preprocess(self, df, seq_len=50):

        df = df.copy()

        # 1. limpeza
        df = self.builder.clean(df)

        # 2. gerar features
        df = self.builder.add_features(df)

        # garantir que as features existem
        missing = [c for c in self.feature_cols if c not in df.columns]
        if missing:
            raise RuntimeError(f"Faltam features no dataframe antes do scaler: {missing}")

        # 3. normalizar
        scaled = self.scaler.transform(df[self.feature_cols])
        scaled = pd.DataFrame(scaled, index=df.index, columns=self.feature_cols)

        # 4. última sequência
        if len(scaled) < seq_len:
            raise RuntimeError(f"Dataset demasiado curto para seq_len={seq_len}")

        seq = scaled.iloc[-seq_len:].values
        seq = np.expand_dims(seq, axis=0)

        return torch.tensor(seq, dtype=torch.float32)

    # ---------------------------------------------------------------
    def predict(self, df, seq_len=50):

        X = self.preprocess(df, seq_len)

        with torch.no_grad():
            out = self.model(X)
            probs = torch.softmax(out, dim=1).cpu().numpy()[0]

        pred_class = int(np.argmax(probs))

        return {
            "class": pred_class,
            "probs": probs.tolist()
        }
