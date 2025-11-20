import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler


class DatasetBuilderLite:
    """
    Constrói um dataset ML completo, simples mas sólido.
    - Limpa valores inválidos
    - Gera retornos
    - Gera features técnicas básicas
    - Normaliza (StandardScaler)
    - Cria labels (multiclass via quintis)
    - Entrega X, y, scaler e colunas finais
    """

    def __init__(self, sequence_length=50):
        self.seq_len = sequence_length

    # -----------------------------------------------------------
    # 1. LIMPEZA
    # -----------------------------------------------------------
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()
        df = df.sort_index()
        return df

    # -----------------------------------------------------------
    # 2. FEATURES
    # -----------------------------------------------------------
    def add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["return_1h"] = df["close"].pct_change() * 100
        df["return_6h"] = df["close"].pct_change(6) * 100
        df["return_24h"] = df["close"].pct_change(24) * 100

        df["volatility_6h"] = df["return_1h"].rolling(6).std()
        df["volatility_24h"] = df["return_1h"].rolling(24).std()

        df["ema_10"] = df["close"].ewm(span=10).mean()
        df["ema_20"] = df["close"].ewm(span=20).mean()

        df = df.dropna()
        return df

    # -----------------------------------------------------------
    # 3. LABELS
    # -----------------------------------------------------------
    def make_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["future_close"] = df["close"].shift(-1)
        df["future_return"] = (df["future_close"] - df["close"]) / df["close"] * 100

        df["label"] = pd.qcut(
            df["future_return"],
            5,
            labels=[0, 1, 2, 3, 4]
        )

        df = df.dropna()
        return df

    # -----------------------------------------------------------
    # 4. NORMALIZAÇÃO
    # -----------------------------------------------------------
    def scale_features(self, df: pd.DataFrame, feature_cols):
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(df[feature_cols])
        df_scaled = pd.DataFrame(df_scaled, index=df.index, columns=feature_cols)
        return df_scaled, scaler

    # -----------------------------------------------------------
    # 5. SEQUÊNCIAS PARA LSTM
    # -----------------------------------------------------------
    def build_sequences(self, X, y):
        X_seq = []
        y_seq = []

        for i in range(len(X) - self.seq_len):
            X_seq.append(X[i:i + self.seq_len])
            y_seq.append(y[i + self.seq_len])

        return np.array(X_seq), np.array(y_seq)

    # -----------------------------------------------------------
    # 6. PIPELINE COMPLETO
    # -----------------------------------------------------------
    def build(self, df: pd.DataFrame):
        df = self.clean(df)
        df = self.add_features(df)
        df = self.make_labels(df)

        feature_cols = [
            "open", "high", "low", "close", "volume",
            "return_1h", "return_6h", "return_24h",
            "volatility_6h", "volatility_24h",
            "ema_10", "ema_20",
        ]

        df_scaled, scaler = self.scale_features(df, feature_cols)

        X, y = self.build_sequences(df_scaled.values, df["label"].values)

        return X, y, scaler, feature_cols
