# model_trainer.py

import torch
import torch.nn as nn
import torch.optim as optim

from sklearn.preprocessing import StandardScaler

from ml.sequence_builder import SequenceBuilder
from ml.lstm_model import LSTMModel
from ml.model_store import save_model


class ModelTrainer:

    def train(self, df, model_key):

        feature_cols = [c for c in df.columns if c not in ["label"]]

        # Normalização
        scaler = StandardScaler()
        df_scaled = df.copy()
        df_scaled[feature_cols] = scaler.fit_transform(df[feature_cols])

        # Criar sequências
        builder = SequenceBuilder(seq_len=50)
        X, y = builder.build_sequences(df_scaled, feature_cols, "label")

        dataset_size = len(X)
        split = int(dataset_size * 0.8)

        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]

        n_features = X.shape[2]

        model = LSTMModel(n_features=n_features)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)

        epochs = 10

        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad()

            outputs = model(X_train)
            loss = criterion(outputs, y_train)
            loss.backward()
            optimizer.step()

            # Validação
            model.eval()
            with torch.no_grad():
                val_outputs = model(X_val)
                val_loss = criterion(val_outputs, y_val)

            print(f"Epoch {epoch+1}/{epochs}  loss={loss.item():.4f}  val_loss={val_loss.item():.4f}")

        save_model(model_key, model, scaler, feature_cols)

        return {"ok": True, "model_key": model_key}
