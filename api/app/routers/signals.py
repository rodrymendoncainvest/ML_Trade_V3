# api/app/routers/signals.py
# -------------------------------------------------------------
# Sinais: rsi_cross, ema_cross, macd_cross, rsi_ema_combo, mtf
# -------------------------------------------------------------
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.routers.dataset import _safe_get_dataset, _resolve_symbol

router = APIRouter(prefix="/signals", tags=["signals"])


# -------------------------------------------------------------
# RSI
# -------------------------------------------------------------
def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()

    rs = gain / (loss.replace(0, pd.NA))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _calc_signal_rsi(df: pd.DataFrame, lower: float, upper: float, rsi_period: int):
    rsi = _rsi(df["close"], period=rsi_period)
    last_rsi = float(rsi.iloc[-1])

    if last_rsi <= lower:
        side = "buy"
    elif last_rsi >= upper:
        side = "sell"
    else:
        side = "hold"

    return side, last_rsi


# -------------------------------------------------------------
# EMA
# -------------------------------------------------------------
def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _calc_signal_ema(df: pd.DataFrame, fast: int, slow: int):
    closes = df["close"]
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    last_fast = float(ema_fast.iloc[-1])
    last_slow = float(ema_slow.iloc[-1])

    if last_fast > last_slow:
        side = "buy"
    elif last_fast < last_slow:
        side = "sell"
    else:
        side = "hold"

    return side, {"ema_fast": last_fast, "ema_slow": last_slow}


# -------------------------------------------------------------
# MACD (12,26,9 default)
# -------------------------------------------------------------
def _calc_macd(df: pd.DataFrame, fast: int, slow: int, signal: int):
    closes = df["close"]

    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line

    last_macd = float(macd_line.iloc[-1])
    last_signal = float(signal_line.iloc[-1])
    last_hist = float(hist.iloc[-1])

    if last_macd > last_signal:
        side = "buy"
    elif last_macd < last_signal:
        side = "sell"
    else:
        side = "hold"

    return side, {
        "macd": last_macd,
        "signal": last_signal,
        "hist": last_hist,
    }


# -------------------------------------------------------------
# RSI + EMA COMBO
# -------------------------------------------------------------
def _combine_rsi_ema(rsi_side: str, ema_side: str):
    if rsi_side == ema_side:
        return rsi_side
    return "hold"


# -------------------------------------------------------------
# /signals/check (single-timeframe)
# -------------------------------------------------------------
@router.get("/check")
def check_signal(
    symbol: str = Query(...),
    tf: str = Query(...),
    strategy: str = Query(...),
    exchange: Optional[str] = Query(None),
    provider: str = Query("yahoo"),

    # RSI
    rsi_period: int = Query(14),
    lower: float = Query(30.0),
    upper: float = Query(70.0),

    # EMA
    fast: int = Query(9),
    slow: int = Query(21),

    # MACD
    macd_fast: int = Query(12),
    macd_slow: int = Query(26),
    macd_signal: int = Query(9),
) -> Dict[str, Any]:

    _ = _resolve_symbol(symbol, exchange, provider)

    df, resolved = _safe_get_dataset(
        symbol=symbol,
        tf=tf,
        columns=["time", "close"],
        provider=provider,
        exchange=exchange,
        dropna=True,
    )

    if df.empty:
        raise HTTPException(404, "no data")

    last_close = float(df["close"].iloc[-1])

    # ------------ RSI CROSS --------------
    if strategy == "rsi_cross":
        rsi_side, last_rsi = _calc_signal_rsi(df, lower, upper, rsi_period)

        return {
            "symbol": resolved,
            "tf": tf,
            "strategy": strategy,
            "signal": rsi_side,
            "rsi": last_rsi,
            "last_close": last_close,
            "thresholds": {"lower": lower, "upper": upper},
            "provider": provider,
        }

    # ------------ EMA CROSS --------------
    if strategy == "ema_cross":
        ema_side, values = _calc_signal_ema(df, fast, slow)

        return {
            "symbol": resolved,
            "tf": tf,
            "strategy": strategy,
            "signal": ema_side,
            "values": values,
            "last_close": last_close,
            "params": {"fast": fast, "slow": slow},
            "provider": provider,
        }

    # ------------ MACD CROSS --------------
    if strategy == "macd_cross":
        macd_side, values = _calc_macd(df, macd_fast, macd_slow, macd_signal)

        return {
            "symbol": resolved,
            "tf": tf,
            "strategy": strategy,
            "signal": macd_side,
            "macd": values,
            "last_close": last_close,
            "params": {
                "fast": macd_fast,
                "slow": macd_slow,
                "signal": macd_signal,
            },
            "provider": provider,
        }

    # ------------ RSI + EMA COMBO --------------
    if strategy == "rsi_ema_combo":
        rsi_side, last_rsi = _calc_signal_rsi(df, lower, upper, rsi_period)
        ema_side, values = _calc_signal_ema(df, fast, slow)

        final_signal = _combine_rsi_ema(rsi_side, ema_side)

        return {
            "symbol": resolved,
            "tf": tf,
            "strategy": strategy,
            "signal": final_signal,
            "rsi_side": rsi_side,
            "ema_side": ema_side,
            "rsi": last_rsi,
            "values": values,
            "last_close": last_close,
            "thresholds": {"lower": lower, "upper": upper},
            "params": {"fast": fast, "slow": slow},
            "provider": provider,
        }

    raise HTTPException(422, "unsupported strategy")


# -------------------------------------------------------------
# /signals/mtf (Multi-Timeframe real: 1D, 1H, 30M)
# -------------------------------------------------------------
@router.get("/mtf")
def mtf_signal(
    symbol: str = Query(...),
    exchange: Optional[str] = Query(None),
    provider: str = Query("yahoo"),

    # parâmetros iguais aos single-TF
    rsi_period: int = Query(14),
    lower: float = Query(30.0),
    upper: float = Query(70.0),

    ema_fast: int = Query(9),
    ema_slow: int = Query(21),

    macd_fast: int = Query(12),
    macd_slow: int = Query(26),
    macd_signal: int = Query(9),
):
    """MTF real: 1D, 1H, 30M"""

    tfs = ["1d", "1h", "30m"]
    results = {}

    for tf in tfs:
        df, resolved = _safe_get_dataset(
            symbol=symbol,
            tf=tf,
            columns=["time", "close"],
            provider=provider,
            exchange=exchange,
            dropna=True,
        )

        if df.empty:
            results[tf] = {"error": "no data"}
            continue

        # RSI
        rsi_side, rsi_value = _calc_signal_rsi(df, lower, upper, rsi_period)

        # EMA
        ema_side, ema_vals = _calc_signal_ema(df, ema_fast, ema_slow)

        # MACD
        macd_side, macd_vals = _calc_macd(df, macd_fast, macd_slow, macd_signal)

        results[tf] = {
            "signal_rsi": rsi_side,
            "rsi": rsi_value,

            "signal_ema": ema_side,
            "ema_fast": ema_vals["ema_fast"],
            "ema_slow": ema_vals["ema_slow"],

            "signal_macd": macd_side,
            "macd": macd_vals,
        }

    # sinal final baseado no timeframe mais forte (1D)
    final_signal = results["1d"]["signal_macd"]

    return {
        "symbol": resolved,
        "provider": provider,
        "final_signal": final_signal,
        "tfs": results,
    }
