# features.py

import pandas as pd

class FeatureEngineer:
    """
    Gera features técnicas simples e robustas.
    """

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["ret_1"] = df["close"].pct_change() * 100
        df["ret_3"] = df["close"].pct_change(3) * 100
        df["ret_6"] = df["close"].pct_change(6) * 100

        df["vol_6"] = df["close"].rolling(6).std()
        df["vol_12"] = df["close"].rolling(12).std()

        df["ema20_slope"] = df["ema_20"].diff()
        df["ema50_slope"] = df["ema_50"].diff()

        df = df.dropna().reset_index(drop=True)
        return df
