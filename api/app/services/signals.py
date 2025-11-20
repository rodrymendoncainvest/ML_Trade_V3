import json
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import os

SELF_BASE_URL = os.getenv("SELF_BASE_URL", "http://127.0.0.1:8000")

def _http_dataset(symbol: str, tf: str, columns: List[str], dropna: bool = True) -> Dict[str, Any]:
    params = {
        "symbol": symbol,
        "tf": tf,
        "columns": ",".join(columns),
        "dropna": "true" if dropna else "false",
    }
    url = f"{SELF_BASE_URL}/dataset/?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "signals/1.0"})
    with urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"/dataset HTTP {resp.status}")
        return json.loads(resp.read().decode("utf-8"))

def _series(rows: List[Dict[str, Any]], key: str) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for r in rows:
        out.append(r.get(key))
    return out

def _last_two(vals: List[Optional[float]]) -> Tuple[Optional[float], Optional[float]]:
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[-1], None
    return vals[-1], vals[-2]

# ---------- Estratégias ----------

def signal_rsi_cross(
    symbol: str,
    tf: str,
    rsi_period: int = 14,
    lower: float = 30.0,
    upper: float = 70.0,
) -> Dict[str, Any]:
    cols = ["time", "close", f"rsi{rsi_period}"]
    data = _http_dataset(symbol, tf, cols, dropna=True)
    rows = data.get("rows", [])
    if not rows:
        return {"symbol": symbol, "tf": tf, "strategy": "rsi_cross", "signal": "no-data"}

    rsi_key = f"rsi{rsi_period}"
    times = _series(rows, "time")
    closes = _series(rows, "close")
    rsis = _series(rows, rsi_key)

    cur, prev = _last_two(rsis)
    if cur is None or prev is None:
        return {"symbol": symbol, "tf": tf, "strategy": "rsi_cross", "signal": "insufficient"}

    # cruzamentos
    crossed_up = prev <= lower and cur > lower
    crossed_down = prev >= upper and cur < upper

    if crossed_up:
        signal = "long-entry"
    elif crossed_down:
        signal = "flat/exit"
    else:
        # estado
        if cur < lower:
            signal = "oversold"
        elif cur > upper:
            signal = "overbought"
        else:
            signal = "neutral"

    return {
        "symbol": symbol,
        "tf": tf,
        "strategy": "rsi_cross",
        "params": {"rsi_period": rsi_period, "lower": lower, "upper": upper},
        "signal": signal,
        "time": times[-1],
        "close": closes[-1],
        "rsi": cur,
    }

def signal_sma_cross(
    symbol: str,
    tf: str,
    fast: int = 20,
    slow: int = 50,
) -> Dict[str, Any]:
    if fast >= slow:
        raise ValueError("fast < slow obrigatório para SMA cross")
    cols = ["time", "close", f"sma{fast}", f"sma{slow}"]
    data = _http_dataset(symbol, tf, cols, dropna=True)
    rows = data.get("rows", [])
    if not rows:
        return {"symbol": symbol, "tf": tf, "strategy": "sma_cross", "signal": "no-data"}

    s_fast = _series(rows, f"sma{fast}")
    s_slow = _series(rows, f"sma{slow}")
    times = _series(rows, "time")
    closes = _series(rows, "close")

    fast_cur, fast_prev = _last_two(s_fast)
    slow_cur, slow_prev = _last_two(s_slow)
    if None in (fast_cur, fast_prev, slow_cur, slow_prev):
        return {"symbol": symbol, "tf": tf, "strategy": "sma_cross", "signal": "insufficient"}

    crossed_up = fast_prev <= slow_prev and fast_cur > slow_cur
    crossed_down = fast_prev >= slow_prev and fast_cur < slow_cur

    if crossed_up:
        signal = "long-entry"
    elif crossed_down:
        signal = "flat/exit"
    else:
        signal = "long" if fast_cur > slow_cur else "flat"

    return {
        "symbol": symbol,
        "tf": tf,
        "strategy": "sma_cross",
        "params": {"fast": fast, "slow": slow},
        "signal": signal,
        "time": times[-1],
        "close": closes[-1],
        "fast": fast_cur,
        "slow": slow_cur,
    }
