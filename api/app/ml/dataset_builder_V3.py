# ============================================================
#  DATASET BUILDER V3 — 22 FEATURES (multi-head)
# ============================================================

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from ml.feature_engineer_V3 import FeatureEngineerV3


class DatasetBuilderV3:

    def __init__(self, seq_len=144):
        self.seq_len = seq_len
        self.fe = FeatureEngineerV3()

    # ------------------------------------------------------------
    # LABEL DIREÇÃO 6H (0/1/2 → depois 0/1)
    # ------------------------------------------------------------
    def make_direction_label(self, df):

        df["future_6h"] = df["close"].shift(-6)
        df["return_6h"] = (df["future_6h"] - df["close"]) / df["close"]

        ret_norm = df["return_6h"] / (df["atr_pct"] + 1e-9)

        up_th = 0.4
        down_th = -0.4

        raw = np.where(
            ret_norm > up_th, 1,
            np.where(ret_norm < down_th, 0, 2)  # 2 = neutro
        )

        label = pd.Series(raw, index=df.index)
        return label

    # ------------------------------------------------------------
    # LABEL TREND (0 = down, 1 = up, 2 = range)
    # ------------------------------------------------------------
    def make_trend_label(self, df):
        trend_up = (df["ema20"] > df["ema50"]) & (df["ema20_slope"] > 0) & (df["adx"] > 20)
        trend_down = (df["ema20"] < df["ema50"]) & (df["ema20_slope"] < 0) & (df["adx"] > 20)
        trend_range = ~(trend_up | trend_down)

        return (
            trend_down.astype(int) * 0 +
            trend_up.astype(int) * 1 +
            trend_range.astype(int) * 2
        )

    # ------------------------------------------------------------
    # NORMALIZAÇÃO
    # ------------------------------------------------------------
    def scale_features(self, df_num, fit=True, scaler=None):

        data = df_num.values

        if fit:
            scaler = StandardScaler()
            scaler.fit(data)

        scaled = scaler.transform(data)
        scaled_df = pd.DataFrame(scaled, index=df_num.index, columns=df_num.columns)

        return scaled_df, scaler

    # ------------------------------------------------------------
    # SEQUÊNCIAS
    # ------------------------------------------------------------
    def build_sequences(self, X, d, t):

        X_out = []
        D_out = []
        T_out = []

        for i in range(len(X) - self.seq_len):
            X_out.append(X[i:i + self.seq_len])
            D_out.append(d[i + self.seq_len])
            T_out.append(t[i + self.seq_len])

        return (
            np.array(X_out, dtype=np.float32),
            np.array(D_out, dtype=np.int64),
            np.array(T_out, dtype=np.int64),
        )

    # ------------------------------------------------------------
    # PIPELINE COMPLETA
    # ------------------------------------------------------------
    def build_dataset(self, df_clean):

        # 1) Feature engineering completo
        df = self.fe.transform(df_clean.copy())

        # 2) Labels
        dir_raw = self.make_direction_label(df)
        trend_label = self.make_trend_label(df)

        # remover neutros da direção → empurrar como up fraco
        dir_final = dir_raw.replace({2: 1})

        # 3) FEATURES NUMÉRICAS
        drop = [
            "future_6h", "return_6h",
        ]

        feature_cols = [
            c for c in df.columns
            if c not in drop and df[c].dtype != "object"
        ]

        # garantir 22 features numéricas estáveis
        if len(feature_cols) != 22:
            raise RuntimeError(
                f"Feature count mismatch: expected 22, got {len(feature_cols)} → {feature_cols}"
            )

        df_scaled, scaler = self.scale_features(df[feature_cols], fit=True)

        # 4) SEQUÊNCIAS
        X, d, t = self.build_sequences(
            df_scaled.values,
            dir_final.values,
            trend_label.values
        )

        return X, d, t, scaler, feature_cols
