import math
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

# Providers intraday (com start/end)
from app.providers.quotes import (
    _yahoo_intraday,
    _twelvedata_intraday_with_candidates,
)

# -------------------------------------------------
# Utils
# -------------------------------------------------
def _series(rows: List[Dict[str, Any]], key: str) -> List[Optional[float]]:
    return [r.get(key) for r in rows]

def _sort_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(rows, key=lambda r: int(r.get("time", 0)))

def _slice_lookback(rows: List[Dict[str, Any]], lookback: Optional[int]) -> List[Dict[str, Any]]:
    if not lookback or lookback <= 0:
        return rows
    return rows[-lookback:]

def _ok(rows: List[Dict[str, Any]]) -> bool:
    return bool(rows) and all("close" in r for r in rows)

# -------------------------------------------------
# Indicadores
# -------------------------------------------------
def _sma(vals: List[Optional[float]], n: int) -> List[Optional[float]]:
    if n <= 0:
        return [None for _ in vals]
    out: List[Optional[float]] = []
    q: deque = deque()
    s = 0.0
    cnt = 0
    for v in vals:
        q.append(v)
        if isinstance(v, (int, float)):
            s += v
            cnt += 1
        if len(q) < n:
            out.append(None)
            continue
        while len(q) > n:
            old = q.popleft()
            if isinstance(old, (int, float)):
                s -= old
                cnt -= 1
        good = [x for x in q if isinstance(x, (int, float))]
        out.append(sum(good) / n if len(good) == n else None)
    return out

def _rsi_wilder(vals: List[Optional[float]], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    prev: Optional[float] = None
    gains: List[float] = []
    losses: List[float] = []
    avg_gain: Optional[float] = None
    avg_loss: Optional[float] = None

    for v in vals:
        if v is None or prev is None:
            out.append(None)
            prev = v
            continue
        ch = v - prev
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))
        prev = v
        if len(gains) < period:
            out.append(None)
            continue
        if len(gains) == period and avg_gain is None:
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
        else:
            g = gains[-1]
            l = losses[-1]
            avg_gain = ((avg_gain * (period - 1)) + g) / period if avg_gain is not None else g
            avg_loss = ((avg_loss * (period - 1)) + l) / period if avg_loss is not None else l

        if avg_loss is None or avg_gain is None:
            out.append(None)
            continue

        if avg_loss == 0:
            rs = float("inf") if avg_gain > 0 else 0.0
        else:
            rs = avg_gain / avg_loss
        rsi = 100.0 - 100.0 / (1.0 + rs) if math.isfinite(rs) else 100.0
        out.append(rsi)
    return out

# -------------------------------------------------
# Carregamento com provider + re-tentativas inteligentes
# -------------------------------------------------
def _load_rows(symbol: str, tf: str, provider: str, start: Optional[str], end: Optional[str]) -> Tuple[List[Dict[str, Any]], str]:
    """
    Estratégia:
      - Se provider=yahoo:
          * tenta Yahoo com start/end se fornecidos
          * se vier vazio, tenta Yahoo sem start/end (pega o range padrão por env)
      - Se provider=auto:
          * tenta o bloco Yahoo acima; se falhar:
          * tenta TwelveData com start/end; se vier vazio, tenta TwelveData sem start/end
      - Se provider=twelvedata:
          * tenta TD com start/end; se falhar, tenta TD sem start/end
    """
    provider = (provider or "auto").lower()
    last_used = "none"

    # ---- Yahoo
    def _try_yf(with_range: bool) -> List[Dict[str, Any]]:
        s = start if with_range else None
        e = end if with_range else None
        rows = _yahoo_intraday(symbol, tf, s, e)
        return _sort_rows(rows)

    # ---- Twelve Data
    def _try_td(with_range: bool) -> List[Dict[str, Any]]:
        s = start if with_range else None
        e = end if with_range else None
        rows = _twelvedata_intraday_with_candidates(symbol, tf, s, e)
        return _sort_rows(rows)

    # Yahoo explicit / auto
    if provider in ("yahoo", "auto"):
        try_order = [True, False] if (start or end) else [False]
        for flag in try_order:
            try:
                rows = _try_yf(flag)
                if _ok(rows):
                    return rows, "yahoo" + ("+range" if flag else "")
            except Exception:
                pass
        last_used = "yahoo"

    # TwelveData explicit / auto
    if provider in ("twelvedata", "auto"):
        try_order = [True, False] if (start or end) else [False]
        for flag in try_order:
            try:
                rows = _try_td(flag)
                if _ok(rows):
                    return rows, "twelvedata" + ("+range" if flag else "")
            except Exception:
                pass
        last_used = "twelvedata"

    return [], last_used

# -------------------------------------------------
# Simulador simples (long only) com custos/stop/take
# -------------------------------------------------
def _simulate_long_only(
    closes: List[Optional[float]],
    signals: List[str],
    fee_bps: float,
    slippage_bps: float,
    stop_pct: Optional[float],
    take_pct: Optional[float],
) -> Dict[str, Any]:
    n = min(len(closes), len(signals))
    if n == 0:
        return {"bars": 0, "equity": [1.0], "trades": 0, "exits": 0}

    cost = max(0.0, (fee_bps or 0.0) + (slippage_bps or 0.0)) / 1e4

    eq: List[float] = [1.0]
    pos = 0
    trades = 0
    exits = 0
    entry_px: Optional[float] = None

    for i in range(1, n):
        p0, p1 = closes[i - 1], closes[i]
        if p0 is None or p1 is None:
            eq.append(eq[-1])
            continue

        if pos == 1 and entry_px is not None:
            if stop_pct and p1 <= entry_px * (1.0 - stop_pct):
                pos = 0
                entry_px = None
                exits += 1
                eq[-1] = eq[-1] * (1.0 - cost)
            elif take_pct and p1 >= entry_px * (1.0 + take_pct):
                pos = 0
                entry_px = None
                exits += 1
                eq[-1] = eq[-1] * (1.0 - cost)

        r = ((p1 - p0) / p0) if pos == 1 else 0.0
        eq.append(eq[-1] * (1.0 + r))

        sig = signals[i]
        if pos == 0 and sig == "long-entry":
            pos = 1
            trades += 1
            entry_px = p1
            eq[-1] = eq[-1] * (1.0 - cost)
        elif pos == 1 and sig == "flat/exit":
            pos = 0
            entry_px = None
            exits += 1
            eq[-1] = eq[-1] * (1.0 - cost)

    return {"bars": n, "equity": eq, "trades": trades, "exits": exits}

def _max_dd(eq: List[float]) -> float:
    if not eq:
        return 0.0
    peak = eq[0]
    mdd = 0.0
    for v in eq:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak else 0.0
        if dd > mdd:
            mdd = dd
    return mdd

# -------------------------------------------------
# Estratégias
# -------------------------------------------------
def backtest_rsi(
    symbol: str,
    tf: str,
    rsi_period: int,
    lower: float,
    upper: float,
    mode: str = "cross",
    lookback: Optional[int] = None,
    provider: str = "auto",
    start: Optional[str] = None,
    end: Optional[str] = None,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
    stop_pct: Optional[float] = None,
    take_pct: Optional[float] = None,
) -> Dict[str, Any]:
    rows, used = _load_rows(symbol, tf, provider, start, end)
    rows = _slice_lookback(rows, lookback)
    if not rows:
        return {"symbol": symbol, "tf": tf, "strategy": "rsi_cross", "provider": used, "error": "no-data"}

    closes = _series(rows, "close")
    rsis = _rsi_wilder(closes, rsi_period)

    signals: List[str] = []
    if mode == "threshold":
        pos = 0
        for cur in rsis:
            if cur is None:
                signals.append("neutral")
            else:
                if pos == 0 and cur < lower:
                    signals.append("long-entry"); pos = 1
                elif pos == 1 and cur > upper:
                    signals.append("flat/exit"); pos = 0
                else:
                    signals.append("long" if pos == 1 else "flat")
    else:
        prev = None
        for cur in rsis:
            if prev is None or cur is None:
                signals.append("neutral")
            else:
                crossed_up = prev <= lower and cur > lower
                crossed_down = prev >= upper and cur < upper
                if crossed_up:
                    signals.append("long-entry")
                elif crossed_down:
                    signals.append("flat/exit")
                else:
                    if cur < lower:
                        signals.append("oversold")
                    elif cur > upper:
                        signals.append("overbought")
                    else:
                        signals.append("neutral")
            prev = cur if cur is not None else prev

    sim = _simulate_long_only(
        closes, signals,
        fee_bps=fee_bps, slippage_bps=slippage_bps,
        stop_pct=stop_pct, take_pct=take_pct,
    )
    eq = sim["equity"]
    return {
        "symbol": symbol,
        "tf": tf,
        "strategy": "rsi_cross",
        "provider": used,
        "params": {
            "rsi_period": rsi_period, "lower": lower, "upper": upper,
            "mode": mode, "lookback": lookback,
            "fee_bps": fee_bps, "slippage_bps": slippage_bps,
            "stop_pct": stop_pct, "take_pct": take_pct,
            "start": start, "end": end,
        },
        "bars": sim["bars"],
        "total_return": (eq[-1] - 1.0) if eq else 0.0,
        "max_drawdown": _max_dd(eq),
        "trades": sim["trades"],
        "exits": sim["exits"],
        "equity_last": eq[-1] if eq else 1.0,
    }

def backtest_sma(
    symbol: str,
    tf: str,
    fast: int,
    slow: int,
    lookback: Optional[int] = None,
    provider: str = "auto",
    start: Optional[str] = None,
    end: Optional[str] = None,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
    stop_pct: Optional[float] = None,
    take_pct: Optional[float] = None,
) -> Dict[str, Any]:
    if fast >= slow:
        return {"symbol": symbol, "tf": tf, "strategy": "sma_cross", "error": "fast-must-be-<slow"}

    rows, used = _load_rows(symbol, tf, provider, start, end)
    rows = _slice_lookback(rows, lookback)
    if not rows:
        return {"symbol": symbol, "tf": tf, "strategy": "sma_cross", "provider": used, "error": "no-data"}

    closes = _series(rows, "close")
    sma_f = _sma(closes, fast)
    sma_s = _sma(closes, slow)

    signals: List[str] = []
    prev_f: Optional[float] = None
    prev_s: Optional[float] = None
    for f, s in zip(sma_f, sma_s):
        if prev_f is None or prev_s is None or f is None or s is None:
            signals.append("neutral")
        else:
            crossed_up = prev_f <= prev_s and f > s
            crossed_down = prev_f >= prev_s and f < s
            if crossed_up:
                signals.append("long-entry")
            elif crossed_down:
                signals.append("flat/exit")
            else:
                signals.append("long" if f > s else "flat")
        prev_f = f if f is not None else prev_f
        prev_s = s if s is not None else prev_s

    sim = _simulate_long_only(
        closes, signals,
        fee_bps=fee_bps, slippage_bps=slippage_bps,
        stop_pct=stop_pct, take_pct=take_pct,
    )
    eq = sim["equity"]
    return {
        "symbol": symbol,
        "tf": tf,
        "strategy": "sma_cross",
        "provider": used,
        "params": {
            "fast": fast, "slow": slow, "lookback": lookback,
            "fee_bps": fee_bps, "slippage_bps": slippage_bps,
            "stop_pct": stop_pct, "take_pct": take_pct,
            "start": start, "end": end,
        },
        "bars": sim["bars"],
        "total_return": (eq[-1] - 1.0) if eq else 0.0,
        "max_drawdown": _max_dd(sim["equity"]),
        "trades": sim["trades"],
        "exits": sim["exits"],
        "equity_last": eq[-1] if eq else 1.0,
    }
