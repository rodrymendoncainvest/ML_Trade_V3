# ============================================================
#  FEATURE ENGINEER V3 — 22 FEATURES (VERSÃO ORIGINAL)
# ============================================================

import numpy as np
import pandas as pd

class FeatureEngineerV3:

    def __init__(self):
        pass

    # -------------------------------------------------------
    def true_range(self, df):
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)

        return tr

    # -------------------------------------------------------
    def compute_atr(self, df, period=14):
        tr = self.true_range(df)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        df["atr"] = atr
        df["atr_pct"] = atr / df["close"].replace(0, 1e-9)
        return df

    # -------------------------------------------------------
    def compute_adx(self, df, period=14):
        high = df["high"]
        low = df["low"]
        close = df["close"]

        up_move = high.diff()
        down_move = -low.diff()

        plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
        minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

        tr = self.true_range(df)
        atr = tr.ewm(alpha=1/period, adjust=False).mean().replace(0, 1e-9)

        plus_dm_sm = plus_dm.ewm(alpha=1/period, adjust=False).mean()
        minus_dm_sm = minus_dm.ewm(alpha=1/period, adjust=False).mean()

        plus_di = 100 * (plus_dm_sm / atr)
        minus_di = 100 * (minus_dm_sm / atr)

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-9)
        adx = dx.ewm(alpha=1/period, adjust=False).mean()

        df["pdi"] = plus_di
        df["mdi"] = minus_di
        df["adx"] = adx
        return df

    # -------------------------------------------------------
    def compute_emas(self, df):
        df["ema20"] = df["close"].ewm(span=20).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()
        return df

    # -------------------------------------------------------
    def compute_slope(self, df):
        df["ema20_slope"] = df["ema20"].diff()
        df["ema20_slope_norm"] = df["ema20_slope"] / df["close"].replace(0, 1e-9)
        return df

    # -------------------------------------------------------
    def compute_momentum(self, df):
        df["mom_6"] = df["close"].pct_change(6).replace([np.inf, -np.inf], 0)
        df["mom_12"] = df["close"].pct_change(12).replace([np.inf, -np.inf], 0)
        return df

    # -------------------------------------------------------
    def compute_volatility(self, df):
        ret = df["close"].pct_change()
        df["vol_24"] = ret.rolling(24).std()
        df["vol_48"] = ret.rolling(48).std()
        return df

    # -------------------------------------------------------
    def compute_rolling(self, df):
        roll_mean = df["close"].rolling(24).mean()
        roll_std = df["close"].rolling(24).std().replace(0, 1e-9)

        df["roll_mean_24"] = roll_mean
        df["roll_std_24"] = roll_std
        df["zscore_24"] = (df["close"] - roll_mean) / roll_std
        return df

    # -------------------------------------------------------
    def compute_volume_norm(self, df):
        vol_roll = df["volume"].rolling(48).mean().replace(0, 1e-9)
        df["volume_norm"] = df["volume"] / vol_roll
        return df

    # -------------------------------------------------------
    def transform(self, df_clean):

        df = df_clean.copy()

        base_cols = ["open", "high", "low", "close", "volume"]
        for c in base_cols:
            if c not in df.columns:
                raise ValueError(f"Missing column for FE: {c}")

        df = self.compute_atr(df)
        df = self.compute_adx(df)
        df = self.compute_emas(df)
        df = self.compute_slope(df)
        df = self.compute_momentum(df)
        df = self.compute_volatility(df)
        df = self.compute_rolling(df)
        df = self.compute_volume_norm(df)

        df = df.replace([np.inf, -np.inf], np.nan).dropna()

        return df
