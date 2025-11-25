# ============================================================
#  ML_Trade V4 — TRAINER CORE (PatchTST)
# ============================================================

import os
import json
import pickle
import torch
import numpy as np
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from .model_core import ModelCore
from .config_core import (
    MODELS_DIR,
    SCALERS_DIR,
    META_DIR,
    SEQ_LEN,
    NUM_FEATURES,
    EPOCHS,
    LEARNING_RATE,
    BATCH_SIZE,
    SHUFFLE,
    EARLY_STOPPING_PATIENCE,
    EARLY_STOPPING_MIN_DELTA,
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ============================================================
#  TRAINER CORE (PatchTST)
# ============================================================

class TrainerCore:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.tf = "1H"

        # PatchTST model
        self.model = ModelCore().to(device)

        # Loss & Optimizer
        self.criterion = torch.nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=LEARNING_RATE)

        # Scaler para features
        self.scaler = StandardScaler()

    # ------------------------------------------------------------
    # Caminhos
    # ------------------------------------------------------------
    @property
    def model_path(self):
        return os.path.join(MODELS_DIR, f"{self.symbol}_{self.tf}_model.pt")

    @property
    def scaler_path(self):
        return os.path.join(SCALERS_DIR, f"{self.symbol}_{self.tf}_scaler.pkl")

    @property
    def meta_path(self):
        return os.path.join(META_DIR, f"{self.symbol}_{self.tf}_meta.json")

    # ------------------------------------------------------------
    # Carregar dados + aplicar scaler
    # ------------------------------------------------------------
    def load_data(self, X, y, X_val=None, y_val=None):
        # Se não existir validação, usar simples split 90/10
        if X_val is None:
            size = int(len(X) * 0.90)
            X_train, X_val = X[:size], X[size:]
            y_train, y_val = y[:size], y[size:]
        else:
            X_train, y_train = X, y

        # Fit scaler apenas no treino
        self.scaler.fit(X_train.reshape(-1, NUM_FEATURES))

        # Guardar scaler
        with open(self.scaler_path, "wb") as f:
            pickle.dump(self.scaler, f)

        # Transform datasets
        X_train_s = np.zeros_like(X_train)
        X_val_s = np.zeros_like(X_val)

        for i in range(X_train.shape[0]):
            X_train_s[i] = self.scaler.transform(X_train[i])

        for i in range(X_val.shape[0]):
            X_val_s[i] = self.scaler.transform(X_val[i])

        # Torch tensors
        self.X_train = torch.tensor(X_train_s, dtype=torch.float32)
        self.y_train = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)

        self.X_val = torch.tensor(X_val_s, dtype=torch.float32)
        self.y_val = torch.tensor(y_val, dtype=torch.float32).unsqueeze(1)

        # DataLoaders
        self.train_loader = DataLoader(
            TensorDataset(self.X_train, self.y_train),
            batch_size=BATCH_SIZE,
            shuffle=SHUFFLE
        )

        self.val_loader = DataLoader(
            TensorDataset(self.X_val, self.y_val),
            batch_size=BATCH_SIZE,
            shuffle=False
        )

    # ------------------------------------------------------------
    # Forward pass de validação
    # ------------------------------------------------------------
    def validate(self):
        self.model.eval()
        losses = []

        with torch.no_grad():
            for X_batch, y_batch in self.val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                pred = self.model(X_batch)
                loss = self.criterion(pred, y_batch)
                losses.append(loss.item())

        return float(np.mean(losses))

    # ------------------------------------------------------------
    # Treinar PatchTST
    # ------------------------------------------------------------
    def train(self):
        best_val = float("inf")
        patience = 0

        for epoch in range(EPOCHS):
            self.model.train()
            batch_losses = []

            for X_batch, y_batch in self.train_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)

                self.optimizer.zero_grad()
                pred = self.model(X_batch)
                loss = self.criterion(pred, y_batch)
                loss.backward()
                self.optimizer.step()

                batch_losses.append(loss.item())

            val_loss = self.validate()

            print(f"[Epoch {epoch+1}/{EPOCHS}] "
                  f"Train={np.mean(batch_losses):.6f}  Val={val_loss:.6f}")

            # Early stopping
            if val_loss + EARLY_STOPPING_MIN_DELTA < best_val:
                best_val = val_loss
                patience = 0
                self.save()
            else:
                patience += 1

            if patience >= EARLY_STOPPING_PATIENCE:
                print("Early stopping.")
                break

    # ------------------------------------------------------------
    # Guardar modelo + meta
    # ------------------------------------------------------------
    def save(self):
        torch.save(self.model.state_dict(), self.model_path)

        meta = {
            "symbol": self.symbol,
            "timeframe": self.tf,
            "seq_len": SEQ_LEN,
            "num_features": NUM_FEATURES,
            "model_type": "PatchTST",
        }

        with open(self.meta_path, "w") as f:
            json.dump(meta, f, indent=4)

        print(f"✔ Modelo guardado: {self.model_path}")
        print(f"✔ Scaler guardado: {self.scaler_path}")
        print(f"✔ Meta guardado:   {self.meta_path}")
