# ============================================================
#  MODEL TRAINER V3.5 — Multi-head (direction + trend)
#  Versão afinada: epochs ↑, loss balance, class weights
# ============================================================

import os
import json
import pickle
import torch
import pandas as pd
import numpy as np
from datetime import datetime
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

# IMPORTS
from app.ml.dataset_builder_V3 import DatasetBuilderV3
from app.ml.model_arch_V3 import ModelV3


class ModelTrainerV3:
    """
    Treinador multi-head V3.5:
      - direction_label (0/1)
      - trend_label (0/1/2)
      - loss = 0.7 * CE_dir + 0.3 * CE_trend (ajustado)
    """

    def __init__(
        self,
        symbol,
        variant="v3_multihead",
        seq_len=144,
        batch_size=32,
        epochs=60,                   # <-- aumentado
    ):

        self.symbol = symbol
        self.variant = variant
        self.seq_len = seq_len
        self.batch_size = batch_size
        self.epochs = epochs

        self.sse_callback = None

        # ROOT = api/
        self.ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.DATA_DIR = os.path.join(self.ROOT, "data")
        self.MODEL_DIR = os.path.join(self.DATA_DIR, "models")

        os.makedirs(self.MODEL_DIR, exist_ok=True)

    # SSE callback
    def set_sse_callback(self, fn):
        self.sse_callback = fn

    # Split temporal
    def temporal_split(self, X, dir_y, trend_y, val_ratio=0.2):
        n = len(X)
        split = int(n * (1 - val_ratio))
        return (
            X[:split], dir_y[:split], trend_y[:split],
            X[split:], dir_y[split:], trend_y[split:]
        )

    # -------------------------------------------------------------
    # TRAIN LOOP — AFINADO
    # -------------------------------------------------------------
    def train_loop(self, model, train_loader, val_loader, device):

        ce_dir = nn.CrossEntropyLoss()

        # Class weights para tendência → estabiliza
        trend_weights = torch.tensor([1.3, 1.0, 1.1], dtype=torch.float32).to(device)
        ce_trend = nn.CrossEntropyLoss(weight=trend_weights)

        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

        for epoch in range(1, self.epochs + 1):

            model.train()
            train_loss = 0.0

            if self.sse_callback:
                pct = int((epoch - 1) / self.epochs * 80)
                self.sse_callback(pct, f"Epoch {epoch}/{self.epochs}...")

            for Xb, dirb, trendb in train_loader:
                Xb = Xb.to(device)
                dirb = dirb.to(device)
                trendb = trendb.to(device)

                optimizer.zero_grad()
                dir_logits, trend_logits = model(Xb)

                loss_dir = ce_dir(dir_logits, dirb)
                loss_trend = ce_trend(trend_logits, trendb)

                loss = 0.7 * loss_dir + 0.3 * loss_trend

                loss.backward()
                optimizer.step()

                train_loss += loss.item()

            # validação
            model.eval()
            val_loss = 0.0

            with torch.no_grad():
                for Xb, dirb, trendb in val_loader:
                    Xb = Xb.to(device)
                    dirb = dirb.to(device)
                    trendb = trendb.to(device)

                    dir_logits, trend_logits = model(Xb)

                    loss_dir = ce_dir(dir_logits, dirb)
                    loss_trend = ce_trend(trend_logits, trendb)
                    loss = 0.7 * loss_dir + 0.3 * loss_trend

                    val_loss += loss.item()

            print(
                f"Epoch {epoch}/{self.epochs} | "
                f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}"
            )

        return model

    # -------------------------------------------------------------
    # TRAIN ENTRYPOINT
    # -------------------------------------------------------------
    def train(self):

        if self.sse_callback:
            self.sse_callback(2, "A carregar dados limpos...")

        print(f"\n=== TRAINING MODEL V3.5 FOR {self.symbol} ===")

        # 1. carregar clean
        clean_path = os.path.join(self.DATA_DIR, "clean", f"{self.symbol}_1H_clean.csv")

        if not os.path.exists(clean_path):
            raise FileNotFoundError(f"Clean data not found: {clean_path}")

        df = pd.read_csv(clean_path, index_col=0)
        df.index = pd.to_datetime(df.index)

        # 2. dataset
        builder = DatasetBuilderV3(seq_len=self.seq_len)
        X, dir_y, trend_y, scaler, feature_cols = builder.build_dataset(df)

        print(f"Dataset → X={X.shape} | dir={dir_y.shape} | trend={trend_y.shape}")

        # 3. split temporal
        X_train, dir_train, trend_train, X_val, dir_val, trend_val = \
            self.temporal_split(X, dir_y, trend_y)

        # 4. dataloaders
        train_loader = DataLoader(
            TensorDataset(
                torch.tensor(X_train, dtype=torch.float32),
                torch.tensor(dir_train, dtype=torch.long),
                torch.tensor(trend_train, dtype=torch.long),
            ),
            batch_size=self.batch_size,
            shuffle=True,
        )
        val_loader = DataLoader(
            TensorDataset(
                torch.tensor(X_val, dtype=torch.float32),
                torch.tensor(dir_val, dtype=torch.long),
                torch.tensor(trend_val, dtype=torch.long),
            ),
            batch_size=self.batch_size,
            shuffle=False,
        )

        # 5. model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = ModelV3(
            input_size=X.shape[-1],
            hidden_size=128,
            num_layers=3,
            dropout=0.25,
        ).to(device)

        # 6. train loop
        model = self.train_loop(model, train_loader, val_loader, device)

        # 7. Save
        model_key = f"{self.symbol}_{self.variant}"

        model_path = os.path.join(self.MODEL_DIR, f"{model_key}.pt")
        torch.save(model.state_dict(), model_path)

        with open(os.path.join(self.MODEL_DIR, f"{model_key}_scaler.pkl"), "wb") as f:
            pickle.dump(scaler, f)

        with open(os.path.join(self.MODEL_DIR, f"{model_key}_features.json"), "w") as f:
            json.dump(feature_cols, f)

        meta = {
            "symbol": self.symbol,
            "variant": self.variant,
            "timestamp": datetime.utcnow().isoformat(),
            "seq_len": self.seq_len,
            "input_size": X.shape[-1],
            "features": feature_cols,
            "heads": ["direction", "trend"],
        }
        with open(os.path.join(self.MODEL_DIR, f"{model_key}_meta.json"), "w") as f:
            json.dump(meta, f, indent=4)

        print(f"\nMODEL SAVED: {model_path}")
        print("TRAINING COMPLETE.\n")

        if self.sse_callback:
            self.sse_callback(100, "Treino concluído.")

        return model_path
