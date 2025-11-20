# ============================================================
# feature_engineer.py — LITE FEATURE SET (COMPLETO)
# ============================================================

import pandas as pd
import numpy as np

class FeatureEngineer:
    def __init__(self):
        pass

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # ------------------------------------
        # BASIC RETURNS
        # ------------------------------------
        df["ret_1"] = df["close"].pct_change(1)
        df["ret_3"] = df["close"].pct_change(3)
        df["ret_6"] = df["close"].pct_change(6)

        # ------------------------------------
        # EMA 20 / EMA 50 + slopes
        # ------------------------------------
        df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
        df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

        df["ema20_slope"] = df["ema20"].diff()
        df["ema50_slope"] = df["ema50"].diff()

        # ------------------------------------
        # VOLATILITY (6, 12)
        # ------------------------------------
        df["vol_6"] = df["close"].pct_change().rolling(6).std()
        df["vol_12"] = df["close"].pct_change().rolling(12).std()

        # ------------------------------------
        # VOLUME FEATURES
        # ------------------------------------
        df["vol_mean_12"] = df["volume"].rolling(12).mean()
        df["vol_std_12"] = df["volume"].rolling(12).std()

        # ------------------------------------
        # CANDLE RATIOS
        # ------------------------------------
        body = (df["close"] - df["open"]).abs()
        range_ = (df["high"] - df["low"]).replace(0, np.nan)

        df["candle_body_pct"] = body / range_
        df["upper_wick"] = (df["high"] - df[["open", "close"]].max(axis=1)) / range_
        df["lower_wick"] = (df[["open", "close"]].min(axis=1) - df["low"]) / range_

        # ------------------------------------
        # TIME FEATURES (HOUR SIN/COS)
        # ------------------------------------
        if isinstance(df.index, pd.DatetimeIndex):
            hour = df.index.hour
            df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
            df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        else:
            df["hour_sin"] = np.nan
            df["hour_cos"] = np.nan

        # ------------------------------------
        # DROP NA STARTUP
        # ------------------------------------
        df = df.dropna()

        return df
