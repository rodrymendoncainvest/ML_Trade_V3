# ============================================================
#  DATASET BUILDER CORE — V4
#  (Sem scaler! Apenas constrói X, y)
# ============================================================

import numpy as np
import pandas as pd
from app.ml_core.config_core import FEATURE_ORDER, SEQ_LEN


class DatasetBuilderCore:

    def __init__(self):
        pass

    # ------------------------------------------------------------
    def _build_target(self, df):
        df["future_return"] = df["close"].pct_change().shift(-1)
        return df.dropna()

    # ------------------------------------------------------------
    def build(self, df_fe):
        df = df_fe.copy()

        df = self._build_target(df)

        feature_matrix = df[FEATURE_ORDER].values
        targets = df["future_return"].values

        X = []
        y = []

        for i in range(SEQ_LEN, len(feature_matrix)):
            X.append(feature_matrix[i - SEQ_LEN:i])
            y.append(targets[i])

        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.float32)

        return X, y
