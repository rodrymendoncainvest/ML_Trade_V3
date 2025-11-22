# model_trainer_V3.py
# Trainer multi-head para o modelo V3 (direção + tendência)

import os
import json
import pickle
import torch
import pandas as pd
from datetime import datetime
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from ml.dataset_builder_V3 import DatasetBuilderV3
from ml.model_arch_V3 import ModelV3


class ModelTrainerV3:
    """
    Treinador multi-head V3:
      - direction_label (0/1)
      - trend_label (0/1/2)
      - loss = 0.5 * CE_dir + 0.5 * CE_trend
    """

    def __init__(self, symbol, variant="v3_multihead", seq_len=144, batch_size=32, epochs=20):
        self.symbol = symbol
        self.variant = variant
        self.seq_len = seq_len
        self.batch_size = batch_size
        self.epochs = epochs

        # ROOT → api/
        self.ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.DATA_DIR = os.path.join(self.ROOT, "data")
        self.MODEL_DIR = os.path.join(self.DATA_DIR, "models")

        os.makedirs(self.MODEL_DIR, exist_ok=True)

    # -------------------------------------------------------------
    # SPLIT temporal
    # -------------------------------------------------------------
    def temporal_split(self, X, dir_y, trend_y, val_ratio=0.2):
        n = len(X)
        split = int(n * (1 - val_ratio))

        X_train = X[:split]
        dir_train = dir_y[:split]
        trend_train = trend_y[:split]

        X_val = X[split:]
        dir_val = dir_y[split:]
        trend_val = trend_y[split:]

        return X_train, dir_train, trend_train, X_val, dir_val, trend_val

    # -------------------------------------------------------------
    # TRAIN LOOP
    # -------------------------------------------------------------
    def train_loop(self, model, train_loader, val_loader, device):
        ce = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

        for epoch in range(1, self.epochs + 1):
            model.train()
            train_loss = 0.0

            for Xb, dirb, trendb in train_loader:
                Xb = Xb.to(device)
                dirb = dirb.to(device)
                trendb = trendb.to(device)

                optimizer.zero_grad()
                dir_logits, trend_logits = model(Xb)

                loss_dir = ce(dir_logits, dirb)
                loss_trend = ce(trend_logits, trendb)
                loss = 0.5 * loss_dir + 0.5 * loss_trend

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
                    loss_dir = ce(dir_logits, dirb)
                    loss_trend = ce(trend_logits, trendb)
                    loss = 0.5 * loss_dir + 0.5 * loss_trend
                    val_loss += loss.item()

            print(f"Epoch {epoch}/{self.epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")

        return model

    # -------------------------------------------------------------
    # TRAIN
    # -------------------------------------------------------------
    def train(self):
        print(f"\n=== TRAINING MODEL V3 (MULTI-HEAD) FOR {self.symbol} ===")

        # 1. Load clean data
        clean_path = os.path.join(self.DATA_DIR, "clean", f"{self.symbol}_1H_clean.csv")
        if not os.path.exists(clean_path):
            raise FileNotFoundError(f"Clean data not found: {clean_path}")

        df = pd.read_csv(clean_path, index_col=0)
        df.index = pd.to_datetime(df.index)

        # 2. Build dataset
        builder = DatasetBuilderV3(seq_len=self.seq_len)
        X, dir_y, trend_y, scaler, feature_cols = builder.build_dataset(df)

        print(f"Dataset built | X={X.shape} | dir_y={dir_y.shape} | trend_y={trend_y.shape}")

        # 3. Split
        X_train, dir_train, trend_train, X_val, dir_val, trend_val = self.temporal_split(
            X, dir_y, trend_y
        )

        # 4. Dataloaders
        train_ds = TensorDataset(
            torch.tensor(X_train, dtype=torch.float32),
            torch.tensor(dir_train, dtype=torch.long),
            torch.tensor(trend_train, dtype=torch.long),
        )
        val_ds = TensorDataset(
            torch.tensor(X_val, dtype=torch.float32),
            torch.tensor(dir_val, dtype=torch.long),
            torch.tensor(trend_val, dtype=torch.long),
        )

        train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=self.batch_size, shuffle=False)

        # 5. Model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = ModelV3(
            input_size=X.shape[-1],
            hidden_size=64,
            num_layers=2,
            dropout=0.15,
        ).to(device)

        # 6. Train
        model = self.train_loop(model, train_loader, val_loader, device)

        # 7. Save model
        model_key = f"{self.symbol}_{self.variant}"
        model_path = os.path.join(self.MODEL_DIR, f"{model_key}.pt")
        torch.save(model.state_dict(), model_path)

        # 8. Save scaler
        scaler_path = os.path.join(self.MODEL_DIR, f"{model_key}_scaler.pkl")
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)

        # 9. Save features
        feat_path = os.path.join(self.MODEL_DIR, f"{model_key}_features.txt")
        with open(feat_path, "w") as f:
            for col in feature_cols:
                f.write(col + "\n")

        # 10. Metadata
        meta = {
            "symbol": self.symbol,
            "variant": self.variant,
            "timestamp": datetime.utcnow().isoformat(),
            "seq_len": self.seq_len,
            "input_size": X.shape[-1],
            "features": feature_cols,
            "heads": ["direction", "trend"]
        }
        meta_path = os.path.join(self.MODEL_DIR, f"{model_key}_meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=4)

        print(f"\nMODEL SAVED: {model_path}")
        print("TRAINING COMPLETE.\n")

        return model_path
