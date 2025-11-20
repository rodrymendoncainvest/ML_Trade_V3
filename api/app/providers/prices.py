# app/providers/prices.py
from __future__ import annotations

import os
import time
import math
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

# --- API KEYS ---
EODHD_KEY = os.getenv("EODHD_KEY", "")
POLYGON_KEY = os.getenv("POLYGON_KEY", "")
ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_KEY", "")
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_KEY", "")  # <- NOVO (opcional)

# --- TUNING / LIMITS ---
INTRADAY_CACHE_TTL = int(os.getenv("INTRADAY_CACHE_TTL", "90"))  # segundos
YF_RANGE_60M = os.getenv("YF_RANGE_60M", "7d")  # antes era 1mo; 7d reduz 429
YF_RANGE_SUBH = os.getenv("YF_RANGE_SUBH", "5d")

Candle = Dict[str, float | int]

# --------------------------- utils ---------------------------

def _get_json(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 20) -> Any:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MLTrade/1.0; +http://localhost)"
    }
    r = requests.get(url, params=params or {}, timeout=timeout, headers=headers)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return json.loads(r.text)

def _is_us_symbol(symbol: str) -> bool:
    return "." not in symbol and "-" not in symbol and ":" not in symbol

def _to_epoch_seconds(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

def _mk_candle(ts_sec: int, o: float, h: float, l: float, c: float, v: float | int | None) -> Candle:
    return {
        "time": int(ts_sec),
        "open": float(o),
        "high": float(h),
        "low": float(l),
        "close": float(c),
        "volume": float(v or 0.0),
    }

# --------------------------- cache ---------------------------

class _IntradayCache:
    def __init__(self, ttl: int = 90) -> None:
        self.ttl = ttl
        self._mem: Dict[Tuple[str, str], Tuple[float, List[Candle], str]] = {}
    def get(self, symbol: str, tf: str) -> Optional[Tuple[List[Candle], str]]:
        key = (symbol.upper(), tf.lower())
        hit = self._mem.get(key)
        if not hit:
            return None
        ts, candles, src = hit
        if time.time() - ts <= self.ttl:
            return candles, f"cache:{src}"
        self._mem.pop(key, None)
        return None
    def set(self, symbol: str, tf: str, candles: List[Candle], src: str) -> None:
        key = (symbol.upper(), tf.lower())
        self._mem[key] = (time.time(), candles, src)

_INTRADAY_CACHE = _IntradayCache(INTRADAY_CACHE_TTL)

# ------------------------ parsers ----------------------------

def _parse_polygon_aggs(data: Dict[str, Any]) -> List[Candle]:
    out: List[Candle] = []
    for row in data.get("results", []) or []:
        ts = int(row.get("t", 0)) // 1000
        out.append(_mk_candle(ts, row["o"], row["h"], row["l"], row["c"], row.get("v", 0)))
    return out

def _parse_eodhd_intraday(rows: List[Dict[str, Any]]) -> List[Candle]:
    out: List[Candle] = []
    for r in rows or []:
        if "timestamp" in r:
            ts = int(r["timestamp"])
        else:
            ts = _to_epoch_seconds(datetime.strptime(r["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc))
        out.append(_mk_candle(ts, r["open"], r["high"], r["low"], r["close"], r.get("volume", 0)))
    return out

def _parse_eodhd_daily(rows: List[Dict[str, Any]]) -> List[Candle]:
    out: List[Candle] = []
    for r in rows or []:
        ts = _to_epoch_seconds(datetime.strptime(r["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc))
        out.append(_mk_candle(ts, r["open"], r["high"], r["low"], r["close"], r.get("volume", 0)))
    return out

def _parse_av_intraday(data: Dict[str, Any]) -> List[Candle]:
    series_key = next((k for k in data.keys() if "Time Series" in k), None)
    meta: Dict[str, Any] = data.get("Meta Data", {})
    tz_name = meta.get("6. Time Zone") or meta.get("5. Time Zone") or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        try:
            tz = ZoneInfo("America/New_York")
        except Exception:
            tz = timezone.utc
    out: List[Candle] = []
    if not series_key:
        return out
    series: Dict[str, Dict[str, str]] = data[series_key]
    for ts_str, v in series.items():
        local_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
        ts = int(local_dt.astimezone(timezone.utc).timestamp())
        o = float(v.get("1. open", v.get("open", 0)))
        h = float(v.get("2. high", v.get("high", 0)))
        l = float(v.get("3. low",  v.get("low", 0)))
        c = float(v.get("4. close", v.get("close", 0)))
        vol_s = v.get("5. volume", v.get("volume", "0"))
        try:
            vol = float(vol_s)
        except Exception:
            vol = 0.0
        out.append(_mk_candle(ts, o, h, l, c, vol))
    out.sort(key=lambda x: x["time"])  # type: ignore
    return out

def _parse_yahoo_chart(data: Dict[str, Any]) -> List[Candle]:
    out: List[Candle] = []
    result = (data.get("chart", {}) or {}).get("result", [])
    if not result:
        return out
    r0 = result[0]
    timestamps = r0.get("timestamp") or []
    quotes = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
    opens = quotes.get("open") or []
    highs = quotes.get("high") or []
    lows = quotes.get("low") or []
    closes = quotes.get("close") or []
    vols = quotes.get("volume") or []
    for i in range(min(len(timestamps), len(opens), len(highs), len(lows), len(closes), len(vols))):
        ts = int(timestamps[i])
        o = float(opens[i]) if opens[i] is not None else math.nan
        h = float(highs[i]) if highs[i] is not None else math.nan
        l = float(lows[i]) if lows[i] is not None else math.nan
        c = float(closes[i]) if closes[i] is not None else math.nan
        v = float(vols[i] or 0)
        if not (math.isnan(o) or math.isnan(h) or math.isnan(l) or math.isnan(c)):
            out.append(_mk_candle(ts, o, h, l, c, v))
    return out

def _parse_twelvedata(data: Dict[str, Any]) -> List[Candle]:
    # estrutura típica:
    # {"status":"ok","values":[{"datetime":"2025-11-07 16:00:00","open":"...","high":"..."}], ...}
    values = data.get("values", []) or []
    out: List[Candle] = []
    for r in values:
        dt_str = r.get("datetime")
        if not dt_str:
            continue
        # TD responde em UTC (documentação); se não, tratamos como naive UTC
        ts = _to_epoch_seconds(datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc))
        out.append(_mk_candle(
            ts,
            float(r["open"]),
            float(r["high"]),
            float(r["low"]),
            float(r["close"]),
            float(r.get("volume", 0) or 0),
        ))
    out.sort(key=lambda x: x["time"])  # type: ignore
    return out

# ------------------------ mappings ---------------------------

def _map_tf(tf: str) -> Tuple[str, str, str, str]:
    """
    Devolve:
      (polygon_timespan, eodhd_interval, av_interval, yf_interval)
    """
    tf = tf.lower()
    if tf in ("1h", "60m", "60min"):
        return ("hour", "1h", "60min", "60m")
    if tf in ("5m", "5min"):
        return ("minute", "5m", "5min", "5m")
    if tf in ("15m", "15min"):
        return ("minute", "15m", "15min", "15m")
    if tf in ("30m", "30min"):
        return ("minute", "30m", "30min", "30m")
    if tf in ("1m", "1min"):
        return ("minute", "1m", "1min", "1m")
    return ("hour", "1h", "60min", "60m")

_SUFFIX_TO_TWELVE = {
    "AS": "AMS",
    "L": "LSE",
    "DE": "XETRA",
    "PA": "PAR",
    "MI": "MIL",
    "SW": "SWX",
    "BR": "BRU",
    "HE": "HEL",
    "ST": "STO",
    "CO": "CPH",
    "OL": "OSL",
    "MC": "BME",
    "VX": "SWX",
    "VI": "VIE",
    "TO": "TSX",
    "V": "TSXV",
}

def _to_twelvedata_symbol(symbol: str) -> str:
    if ":" in symbol:
        return symbol
    if "." in symbol:
        left, suf = symbol.split(".", 1)
        ex = _SUFFIX_TO_TWELVE.get(suf.upper())
        if ex:
            return f"{left}:{ex}"
    return symbol

# ------------------------ fetchers ---------------------------

def fetch_intraday(symbol: str, tf: str = "1h") -> Tuple[List[Candle], str]:
    """
    Intraday com cache e multiple fallback.
    Retorna (candles, source).
    """
    # 0) cache
    cached = _INTRADAY_CACHE.get(symbol, tf)
    if cached:
        return cached

    is_us = _is_us_symbol(symbol)
    polygon_span, eodhd_interval, av_interval, yf_interval = _map_tf(tf)

    now = datetime.now(timezone.utc)
    start_dt = now - timedelta(days=30 if "60" in av_interval or "1h" in tf else 7)
    start_iso = start_dt.date().isoformat()
    end_iso = now.date().isoformat()

    errors: List[str] = []

    # 1) Polygon (US)
    if is_us and POLYGON_KEY:
        try:
            if polygon_span == "hour":
                multiplier = 1
            else:
                try:
                    multiplier = int("".join(ch for ch in tf if ch.isdigit()) or "5")
                except Exception:
                    multiplier = 5
            url = (
                f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/"
                f"{multiplier}/{polygon_span}/{start_iso}/{end_iso}"
            )
            params = {"adjusted": "true", "limit": 50000, "apiKey": POLYGON_KEY}
            data = _get_json(url, params)
            candles = _parse_polygon_aggs(data)
            if candles:
                _INTRADAY_CACHE.set(symbol, tf, candles, "polygon")
                return (candles, "polygon")
        except Exception as e:
            errors.append(f"polygon:{e}")

    # 2) EODHD (global; pode 403)
    if EODHD_KEY:
        try:
            url = f"https://eodhd.com/api/intraday/{symbol}"
            params = {"interval": eodhd_interval, "fmt": "json", "api_token": EODHD_KEY}
            data = _get_json(url, params)
            if isinstance(data, list):
                candles = _parse_eodhd_intraday(data)
                if candles:
                    _INTRADAY_CACHE.set(symbol, tf, candles, "eodhd")
                    return (candles, "eodhd")
            else:
                # mensagem de erro legível
                raise RuntimeError(data.get("message") or "EODHD intraday not permitted")
        except Exception as e:
            errors.append(f"eodhd:{e}")

    # 3) Alpha Vantage (US intraday)
    if is_us and ALPHAVANTAGE_KEY:
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol,
                "interval": av_interval,
                "apikey": ALPHAVANTAGE_KEY,
                "outputsize": "full",
            }
            data = _get_json(url, params)
            if any("Invalid API call" in str(v) for v in data.values() if isinstance(v, str)):
                raise RuntimeError("AlphaVantage intraday unsupported for this symbol")
            candles = _parse_av_intraday(data)
            if candles:
                _INTRADAY_CACHE.set(symbol, tf, candles, "alphavantage")
                return (candles, "alphavantage")
        except Exception as e:
            errors.append(f"alphavantage:{e}")

    # 4) Twelve Data (global; opcional)
    if TWELVE_DATA_KEY:
        try:
            td_symbol = _to_twelvedata_symbol(symbol)
            # intervals compatíveis: 1min,5min,15min,30min,1h
            interval = {"60m": "1h"}.get(yf_interval, yf_interval)
            url = "https://api.twelvedata.com/time_series"
            params = {
                "symbol": td_symbol,
                "interval": interval,
                "outputsize": "5000",
                "timezone": "UTC",
                "apikey": TWELVE_DATA_KEY,
            }
            data = _get_json(url, params)
            if str(data.get("status", "ok")).lower() == "error":
                raise RuntimeError(data.get("message", "TwelveData error"))
            candles = _parse_twelvedata(data)
            if candles:
                _INTRADAY_CACHE.set(symbol, tf, candles, "twelvedata")
                return (candles, "twelvedata")
        except Exception as e:
            errors.append(f"twelvedata:{e}")

    # 5) Yahoo (global; rate-limit sensível)
    try:
        rng = YF_RANGE_60M if yf_interval == "60m" else YF_RANGE_SUBH
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": yf_interval, "range": rng}
        data = _get_json(url, params)
        candles = _parse_yahoo_chart(data)
        if candles:
            _INTRADAY_CACHE.set(symbol, tf, candles, "yahoo")
            return (candles, "yahoo")
    except requests.HTTPError as e:
        # 429 + cache: devolve cache se existir
        if e.response is not None and e.response.status_code == 429:
            cached = _INTRADAY_CACHE.get(symbol, tf)
            if cached:
                return cached
        errors.append(f"yahoo:{e}")
    except Exception as e:
        errors.append(f"yahoo:{e}")

    raise RuntimeError("intraday_unavailable: " + " | ".join(errors[:4]))

def fetch_daily(symbol: str, start: Optional[str] = None, end: Optional[str] = None) -> List[Candle]:
    # 1) EODHD diário
    if EODHD_KEY:
        try:
            params = {"period": "d", "fmt": "json", "order": "a", "api_token": EODHD_KEY}
            if start:
                params["from"] = start
            if end:
                params["to"] = end
            url = f"https://eodhd.com/api/eod/{symbol}"
            data = _get_json(url, params)
            if isinstance(data, list):
                return _parse_eodhd_daily(data)
        except Exception:
            pass

    # 2) Alpha Vantage diário
    if ALPHAVANTAGE_KEY:
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": symbol,
                "apikey": ALPHAVANTAGE_KEY,
                "outputsize": "full",
            }
            data = _get_json(url, params)
            series_key = next((k for k in data.keys() if "Time Series" in k), None)
            if series_key:
                rows = []
                for dstr, v in (data[series_key] or {}).items():
                    dt_utc = datetime.strptime(dstr, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    ts = _to_epoch_seconds(dt_utc)
                    rows.append(_mk_candle(
                        ts,
                        float(v.get("1. open", v.get("open", 0))),
                        float(v.get("2. high", v.get("high", 0))),
                        float(v.get("3. low",  v.get("low", 0))),
                        float(v.get("4. close", v.get("close", 0))),
                        float(v.get("6. volume", v.get("volume", 0))),
                    ))
                rows.sort(key=lambda x: x["time"])  # type: ignore
                if start:
                    start_ts = _to_epoch_seconds(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc))
                    rows = [c for c in rows if c["time"] >= start_ts]  # type: ignore
                if end:
                    end_ts = _to_epoch_seconds(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc))
                    rows = [c for c in rows if c["time"] <= end_ts]  # type: ignore
                return rows
        except Exception:
            pass

    # 3) Yahoo diário
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": "1d", "range": "5y"}
        data = _get_json(url, params)
        rows = _parse_yahoo_chart(data)
        if start:
            start_ts = _to_epoch_seconds(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc))
            rows = [c for c in rows if c["time"] >= start_ts]  # type: ignore
        if end:
            end_ts = _to_epoch_seconds(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc))
            rows = [c for c in rows if c["time"] <= end_ts]  # type: ignore
        return rows
    except Exception:
        pass

    return []
