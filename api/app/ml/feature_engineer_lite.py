import pandas as pd
import numpy as np


class FeatureEngineerLite:
    """
    Reconstrói exatamente as mesmas features usadas no treino Lite.
    Mantém coerência com DatasetBuilderLite.
    """

    def __init__(self):
        pass

    def add_returns(self, df):
        df["return_1h"] = df["close"].pct_change() * 100
        df["return_6h"] = df["close"].pct_change(6) * 100
        df["return_24h"] = df["close"].pct_change(24) * 100
        return df

    def add_volatility(self, df):
        df["volatility_6h"] = df["return_1h"].rolling(6).std()
        df["volatility_24h"] = df["return_1h"].rolling(24).std()
        return df

    def add_moving_averages(self, df):
        df["ema_10"] = df["close"].ewm(span=10).mean()
        df["ema_20"] = df["close"].ewm(span=20).mean()
        return df

    def add_all_features(self, df):
        df = df.copy()

        # converter numéricos
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()

        df = self.add_returns(df)
        df = self.add_volatility(df)
        df = self.add_moving_averages(df)

        df = df.dropna()

        return df
