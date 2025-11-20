# dataset_builder.py

import pandas as pd

class DatasetBuilder:
    """
    Constrói dataset com horizon futuro (1H) para labels multiclass.
    """

    def __init__(self, horizon_minutes=60):
        self.horizon = horizon_minutes

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["future_close"] = df["close"].shift(-1)
        df["future_return_pct"] = (df["future_close"] - df["close"]) / df["close"] * 100

        df["label"] = pd.qcut(df["future_return_pct"], 5, labels=[0, 1, 2, 3, 4])

        df = df.dropna().reset_index(drop=True)
        return df
