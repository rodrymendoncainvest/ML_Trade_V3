# ============================================================
#  FEATURE ENGINEER CORE — V4
# ============================================================

import pandas as pd
import numpy as np


class FeatureEngineerCore:

    def __init__(self):
        pass

    # -----------------------------
    # RSI
    # -----------------------------
    def compute_rsi(self, close, period=14):
        delta = close.diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        roll_up = up.ewm(alpha=1/period, adjust=False).mean()
        roll_down = down.ewm(alpha=1/period, adjust=False).mean()
        rs = roll_up / roll_down.replace(0, 1e-9)
        return 100 - (100 / (1 + rs))

    # -----------------------------
    def compute_macd(self, close, fast=12, slow=26, signal=9):
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist

    # -----------------------------
    def compute_stoch(self, df, period=14, smooth_k=3, smooth_d=3):
        low_min = df["low"].rolling(period).min()
        high_max = df["high"].rolling(period).max()
        stoch_k = 100 * ((df["close"] - low_min) /
                         (high_max - low_min).replace(0, 1e-9))
        stoch_k = stoch_k.rolling(smooth_k).mean()
        stoch_d = stoch_k.rolling(smooth_d).mean()
        return stoch_k, stoch_d

    # -----------------------------
    def compute_williams_r(self, df, period=14):
        high_max = df["high"].rolling(period).max()
        low_min = df["low"].rolling(period).min()
        return -100 * ((high_max - df["close"]) /
                       (high_max - low_min).replace(0, 1e-9))

    # -----------------------------
    def compute_roc(self, close, period=12):
        return close.pct_change(period)

    # -----------------------------
    def compute_cci(self, df, period=20):
        tp = (df["high"] + df["low"] + df["close"]) / 3
        ma = tp.rolling(period).mean()
        md = (tp - ma).abs().rolling(period).mean().replace(0, 1e-9)
        return (tp - ma) / (0.015 * md)

    # -----------------------------
    def compute_atr(self, df, period=14):
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)

        return tr.ewm(alpha=1/period, adjust=False).mean()

    # -----------------------------
    def compute_obv(self, df):
        obv = (np.sign(df["close"].diff()) * df["volume"]).fillna(0)
        return obv.cumsum()

    # -----------------------------
    # MAIN TRANSFORM
    # -----------------------------
    def transform(self, df_clean):
        df = df_clean.copy()

        required_cols = ["open", "high", "low", "close", "volume"]
        for c in required_cols:
            if c not in df.columns:
                raise ValueError(f"Missing column: {c}")

        df["rsi"] = self.compute_rsi(df["close"])
        df["macd"], df["macd_signal"], df["macd_hist"] = self.compute_macd(df["close"])
        df["sma_fast"] = df["close"].rolling(20).mean()
        df["sma_slow"] = df["close"].rolling(50).mean()
        df["ema_fast"] = df["close"].ewm(span=12).mean()
        df["ema_slow"] = df["close"].ewm(span=26).mean()
        df["stoch_k"], df["stoch_d"] = self.compute_stoch(df)
        df["williams_r"] = self.compute_williams_r(df)
        df["roc"] = self.compute_roc(df["close"])
        df["cci"] = self.compute_cci(df)
        df["atr"] = self.compute_atr(df)
        df["obv"] = self.compute_obv(df)
        df["returns"] = df["close"].pct_change().replace([np.inf, -np.inf], 0)
        df["volatility"] = df["returns"].rolling(30).std().replace([np.inf, -np.inf], 0)

        df = df.replace([np.inf, -np.inf], np.nan).dropna()

        return df
