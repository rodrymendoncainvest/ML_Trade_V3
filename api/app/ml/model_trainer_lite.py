# model_trainer_lite.py

import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import joblib

from ml.dataset_builder_lite import DatasetBuilderLite
from ml.lstm_model_lite import LSTMLiteModel


# ================================================================
# Caminho consistente: api/data/models/
# ================================================================
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_DIR = os.path.join(ROOT, "data", "models")
os.makedirs(MODEL_DIR, exist_ok=True)


class ModelTrainerLite:
    def __init__(self, model_key: str,
                 sequence_length=50,
                 epochs=10,
                 lr=1e-3,
                 batch_size=32):

        self.model_key = model_key
        self.seq_len = sequence_length
        self.epochs = epochs
        self.lr = lr
        self.batch_size = batch_size

        self.builder = DatasetBuilderLite(sequence_length=self.seq_len)

        # caminhos finais
        self.model_path = os.path.join(MODEL_DIR, f"{model_key}.pt")
        self.scaler_path = os.path.join(MODEL_DIR, f"{model_key}_scaler.pkl")
        self.features_path = os.path.join(MODEL_DIR, f"{model_key}_features.txt")

    # ---------------------------------------------------------
    # TREINO
    # ---------------------------------------------------------
    def train(self, df):

        # construir dataset (X seq, y seq, scaler, features)
        X, y, scaler, feature_cols = self.builder.build(df)

        input_size = X.shape[2]
        num_classes = 5

        model = LSTMLiteModel(
            input_size=input_size,
            num_classes=num_classes
        )
        model.train()

        X_tensor = torch.tensor(X, dtype=torch.float32)
        y_tensor = torch.tensor(y, dtype=torch.long)

        dataset = TensorDataset(X_tensor, y_tensor)
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=self.lr)

        # ---------------------------------------------------------
        # LOOP DE TREINO
        # ---------------------------------------------------------
        for epoch in range(self.epochs):
            epoch_loss = 0.0

            for xb, yb in loader:
                optimizer.zero_grad()
                preds = model(xb)
                loss = criterion(preds, yb)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            print(f"Epoch {epoch+1}/{self.epochs}  loss={epoch_loss/len(loader):.5f}")

        # ---------------------------------------------------------
        # GUARDAR MODELO + SCALER + FEATURES
        # ---------------------------------------------------------
        torch.save(model.state_dict(), self.model_path)
        joblib.dump(scaler, self.scaler_path)

        with open(self.features_path, "w") as f:
            f.write("\n".join(feature_cols))

        print(f"\nModelo guardado em:   {self.model_path}")
        print(f"Scaler guardado em:   {self.scaler_path}")
        print(f"Features guardadas em:{self.features_path}")

        return model, scaler, feature_cols
