# api/app/routers/signals_mtf.py
# -------------------------------------------------------------
# Multi-Timeframe Signal  (RSI + EMA + MACD em 5 TFs)
# Totalmente isolado — não interfere com signals.py existente
# -------------------------------------------------------------
from __future__ import annotations
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query

import pandas as pd

from app.routers.dataset import _safe_get_dataset, _resolve_symbol
from app.routers.signals import (
    _rsi,
    _ema,
    _calc_signal_rsi,
    _calc_signal_ema,
)

router = APIRouter(prefix="/signals", tags=["signals-mtf"])


# -------------------------------------------------------------
# FAST HELPERS
# -------------------------------------------------------------
def _calc_macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line

    return float(macd.iloc[-1]), float(signal_line.iloc[-1]), float(hist.iloc[-1])


def _decide(macd_val: float, sig_val: float, rsi_val: float, lower: float, upper: float):
    votes = []

    # RSI vote
    if rsi_val <= lower:
        votes.append("buy")
    elif rsi_val >= upper:
        votes.append("sell")
    else:
        votes.append("hold")

    # MACD vote
    if macd_val > sig_val:
        votes.append("buy")
    elif macd_val < sig_val:
        votes.append("sell")
    else:
        votes.append("hold")

    # Weighted final
    if votes.count("buy") > votes.count("sell"):
        return "buy"
    if votes.count("sell") > votes.count("buy"):
        return "sell"
    return "hold"


# -------------------------------------------------------------
# /signals/mtf?symbol=ASML.AS
# -------------------------------------------------------------
@router.get("/mtf")
def mtf_signal(
    symbol: str = Query(...),
    provider: str = Query("yahoo"),
):
    timeframes = ["1d", "1h", "30m", "15m", "5m"]
    resolved = _resolve_symbol(symbol, None, provider)

    out = {}

    for tf in timeframes:
        df, _ = _safe_get_dataset(
            symbol=symbol,
            tf=tf,
            columns=["time", "close"],
            provider=provider,
            exchange=None,
            dropna=True,
        )

        if df.empty:
            raise HTTPException(404, f"no data for {tf}")

        closes = df["close"]

        # RSI
        rsi_series = _rsi(closes, period=14)
        rsi_val = float(rsi_series.iloc[-1])

        # EMA
        ema_side, ema_vals = _calc_signal_ema(df, fast=9, slow=21)

        # MACD
        macd_val, sig_val, hist_val = _calc_macd(closes)

        # Final vote
        final = _decide(macd_val, sig_val, rsi_val, 30, 70)

        out[tf] = {
            "rsi": rsi_val,
            "ema": ema_side,
            "macd": {
                "macd": macd_val,
                "signal": sig_val,
                "hist": hist_val,
            },
            "final": final,
        }

    return {
        "symbol": resolved,
        "provider": provider,
        "mtf": out,
    }
