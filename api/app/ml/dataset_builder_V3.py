# ============================================================
#  DATASET BUILDER V3 — versão original (22 features)
# ============================================================

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from app.ml.feature_engineer_V3 import FeatureEngineerV3

class DatasetBuilderV3:

    def __init__(self, seq_len=144):
        self.seq_len = seq_len
        self.fe = FeatureEngineerV3()

    # ------------------------------------------------------------
    def make_direction_label(self, df):
        df["future_6h"] = df["close"].shift(-6)
        df["return_6h"] = (df["future_6h"] - df["close"]) / df["close"]
        df["return_norm"] = df["return_6h"] / (df["atr_pct"] + 1e-9)

        label = np.where(
            df["return_norm"] > 0.4, 1,
            np.where(df["return_norm"] < -0.4, 0, 2)
        )

        return pd.Series(label, index=df.index)

    # ------------------------------------------------------------
    def make_trend_label(self, df):
        trend_up = (df["ema20"] > df["ema50"]) & (df["ema20_slope"] > 0) & (df["adx"] > 20)
        trend_down = (df["ema20"] < df["ema50"]) & (df["ema20_slope"] < 0) & (df["adx"] > 20)

        return (
            trend_down.astype(int) * 0 +
            trend_up.astype(int) * 1 +
            (~(trend_up | trend_down)).astype(int) * 2
        )

    # ------------------------------------------------------------
    def scale_features(self, df_num, fit=True, scaler=None):
        X = df_num.values

        if fit:
            scaler = StandardScaler()
            scaler.fit(X)

        X_scaled = scaler.transform(X)
        return (
            pd.DataFrame(X_scaled, index=df_num.index, columns=df_num.columns),
            scaler
        )

    # ------------------------------------------------------------
    def build_sequences(self, X, d, t):
        X_out, D_out, T_out = [], [], []

        for i in range(len(X) - self.seq_len):
            X_out.append(X[i:i + self.seq_len])
            D_out.append(d[i + self.seq_len])
            T_out.append(t[i + self.seq_len])

        return (
            np.array(X_out, dtype=np.float32),
            np.array(D_out, dtype=np.int64),
            np.array(T_out, dtype=np.int64)
        )

    # ------------------------------------------------------------
    def build_dataset(self, df_clean):

        df = self.fe.transform(df_clean.copy())

        dir_raw = self.make_direction_label(df)
        trend_raw = self.make_trend_label(df)

        dir_final = dir_raw.replace({2: 1})

        drop = ["future_6h", "return_6h", "return_norm", "symbol"]

        feature_cols = [
            c for c in df.columns
            if c not in drop and df[c].dtype != "object"
        ]

        if len(feature_cols) != 22:
            raise RuntimeError(
                f"Esperava 22 features, recebi {len(feature_cols)} → {feature_cols}"
            )

        df_scaled, scaler = self.scale_features(df[feature_cols], fit=True)

        X, d, t = self.build_sequences(
            df_scaled.values,
            dir_final.values,
            trend_raw.values
        )

        return X, d, t, scaler, feature_cols
