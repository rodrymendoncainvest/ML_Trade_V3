# model_inference.py

import torch
import numpy as np

from ml.model_store import load_model
from ml.lstm_model import LSTMModel


class ModelInference:

    def __init__(self, model_key):
        self.model, self.scaler, self.feature_cols, self.n_features = load_model(
            model_key, LSTMModel
        )
        self.model.eval()

    def predict(self, seq_df):
        """
        seq_df: dataframe com EXACTAMENTE 50 timesteps
        """

        data = seq_df[self.feature_cols].copy()
        data = self.scaler.transform(data)

        x = torch.tensor(data, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1).numpy()[0]
            cls = int(np.argmax(probs))

        return {"class": cls, "probs": probs.tolist()}
