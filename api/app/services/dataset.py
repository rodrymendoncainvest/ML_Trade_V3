# api/app/services/dataset.py
from __future__ import annotations

import os
import math
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import yfinance as yf

# -------------------------------
# Config
# -------------------------------

YF_RANGE_60M = os.getenv("YF_RANGE_60M", "30d")
YF_RANGE_1D  = os.getenv("YF_RANGE_1D",  "1y")
YF_RANGE_1WK = os.getenv("YF_RANGE_1WK", "5y")
YF_RANGE_1MO = os.getenv("YF_RANGE_1MO", "10y")

EXCHANGE_SUFFIX = {
    # Euronext
    "XAMS": ".AS", "AMS": ".AS",
    "XPAR": ".PA", "PAR": ".PA",
    "XLIS": ".LS", "LIS": ".LS",
    "XBRU": ".BR", "BRU": ".BR",
    "XETR": ".DE", "ETR": ".DE",
    # Itália
    "XMIL": ".MI", "MIL": ".MI", "BIT": ".MI",
    # UK
    "XLON": ".L", "LON": ".L",
    # Espanha
    "XMAD": ".MC", "MAD": ".MC",
    # Suíça
    "XSWX": ".SW", "SWX": ".SW",
    # Dinamarca
    "XCSE": ".CO", "CSE": ".CO",
    # Suécia
    "XSTO": ".ST", "STO": ".ST",
    # Noruega
    "XOSL": ".OL", "OSL": ".OL",
    # EUA
    "XNYS": "", "XNMS": "", "NASDAQ": "", "NYSE": "",
}

# -------------------------------
# Helpers
# -------------------------------

def _qualify_symbol_for_yahoo(symbol: str, exchange: Optional[str]) -> str:
    if not exchange:
        return symbol
    suf = EXCHANGE_SUFFIX.get(exchange.upper())
    if suf is None:
        return symbol
    if suf == "" or symbol.endswith(tuple(EXCHANGE_SUFFIX.values())):
        return symbol
    return f"{symbol}{suf}"

def _tf_to_yf(tf: str) -> Tuple[str, str]:
    t = (tf or "").lower()
    if t in ("1h", "60m"):
        return "60m", YF_RANGE_60M
    if t in ("30m", "30min"):
        return "30m", "30d"
    if t in ("15m", "15min"):
        return "15m", "30d"
    if t in ("5m", "5min"):
        return "5m", "7d"
    if t in ("1m", "1min"):
        return "1m", "7d"
    if t in ("1wk", "1w", "weekly"):
        return "1wk", YF_RANGE_1WK
    if t in ("1mo", "monthly"):
        return "1mo", YF_RANGE_1MO
    return "1d", YF_RANGE_1D

def _coerce_columns_arg(columns: Any) -> List[str]:
    if columns is None:
        return ["time", "open", "high", "low", "close", "volume"]
    if isinstance(columns, str):
        parts = [p.strip() for p in columns.split(",") if p.strip()]
        return parts or ["time", "open", "high", "low", "close", "volume"]
    if isinstance(columns, (list, tuple)):
        return [str(c) for c in columns]
    return ["time", "open", "high", "low", "close", "volume"]

def _base_key(name: str) -> str:
    """
    Normaliza nomes de coluna:
    - remove espaços
    - passa a minúsculas
    - corta tudo após o 1º '_' (para lidar com 'Close_ASML.AS', 'Adj Close_STM.MI', etc.)
    """
    s = str(name).strip().lower().replace(" ", "")
    if "_" in s:
        s = s.split("_", 1)[0]
    return s

def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza quaisquer variações de nomes (com ou sem sufixo de ticker, MultiIndex, etc.)
    e garante SEMPRE uma coluna 'close' (usa 'adj close' se preciso).
    """
    if df is None or df.empty:
        return df.copy()

    df = df.copy()

    # Achatar MultiIndex (se houver)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([str(c) for c in col if str(c) != ""]) for col in df.columns.to_list()]

    # Construir mapa de renomeação robusto
    rename_map: Dict[str, str] = {}
    candidates_close: List[str] = []
    candidates_adj: List[str] = []

    for c in df.columns:
        key = _base_key(c)  # ex.: 'close_asml.as' → 'close'
        if key == "open":
            rename_map[c] = "open"
        elif key == "high":
            rename_map[c] = "high"
        elif key == "low":
            rename_map[c] = "low"
        elif key == "close":
            rename_map[c] = "close"
            candidates_close.append(c)
        elif key in ("adjclose", "adjustedclose"):
            rename_map[c] = "adj_close"
            candidates_adj.append(c)
        elif key == "volume":
            rename_map[c] = "volume"

    df = df.rename(columns=rename_map)

    # Se não foi mapeado nenhum 'close', tentar criar a partir de adj_close ou dos candidatos crus
    if "close" not in df.columns:
        if "adj_close" in df.columns and not df["adj_close"].isna().all():
            df["close"] = df["adj_close"]
        elif candidates_close:
            # usar o primeiro candidato 'Close_*'
            series = df[candidates_close[0]]
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            df["close"] = series
        elif candidates_adj:
            series = df[candidates_adj[0]]
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            df["close"] = series

    # Se existirem duplicados por alguma razão, manter a 1ª
    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated(keep="first")]

    return df

def _epoch(ts: pd.Timestamp) -> int:
    return int(pd.Timestamp(ts).tz_localize(None).timestamp())

def _round_row(d: Dict[str, Any], decimals: Optional[int]) -> Dict[str, Any]:
    if decimals is None:
        return d
    out = {}
    for k, v in d.items():
        if isinstance(v, float) and math.isfinite(v):
            out[k] = round(v, decimals)
        else:
            out[k] = v
    return out

# -------------------------------
# API
# -------------------------------

def get_dataset(
    symbol: str,
    tf: str,
    columns: Any,
    dropna: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    decimals: Optional[int] = None,
    *,
    provider: Optional[str] = None,
    exchange: Optional[str] = None,
    start: Optional[Any] = None,  # aceitamos mas ignoramos por agora
    end: Optional[Any] = None,    # idem
) -> Dict[str, Any]:

    cols_req = _coerce_columns_arg(columns)
    prov = (provider or "yahoo").lower()
    if prov != "yahoo":
        # Outros providers tratados noutros serviços; aqui só Yahoo.
        raise KeyError("close")

    ticker = _qualify_symbol_for_yahoo(symbol, exchange)
    interval, period = _tf_to_yf(tf)

    try:
        df = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            prepost=False,
            progress=False,
            threads=False,
        )
    except Exception as e:
        raise KeyError(str(e))

    if df is None or df.empty:
        raise KeyError("close")

    df = _normalize_ohlcv(df)

    # DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True, errors="coerce")
    df = df[~df.index.isna()]
    if df.empty:
        raise KeyError("close")

    # Montar DataFrame de saída
    out = pd.DataFrame({"time": [_epoch(ts) for ts in df.index]}, index=df.index)

    for c in cols_req:
        if c == "time":
            continue
        if c in df.columns:
            series = df[c]
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            out[c] = series

    # Se pediram close e ainda não temos, tenta descobrir automaticamente
    if "close" in cols_req and "close" not in out.columns:
        # procurar qualquer coluna que contenha 'close'
        cand = [col for col in df.columns if "close" in str(col).lower()]
        if cand:
            series = df[cand[0]]
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            out["close"] = series

    # dropna (não conta 'time')
    if dropna:
        subset = [c for c in cols_req if c != "time" and c in out.columns]
        if subset:
            out = out.dropna(subset=subset)

    # offset/limit
    if offset:
        out = out.iloc[offset:]
    if limit:
        out = out.iloc[:limit]

    # ordenar colunas finais
    final_cols = [c for c in cols_req if (c == "time" or c in out.columns)]
    if not final_cols:
        final_cols = ["time"]
    out = out[final_cols]

    # arredondar
    if decimals is not None:
        for c in final_cols:
            if c != "time" and pd.api.types.is_float_dtype(out[c]):
                out[c] = out[c].round(decimals)

    # serializar
    rows = []
    for rec in out.reset_index(drop=True).to_dict(orient="records"):
        clean = {}
        for k, v in rec.items():
            if pd.isna(v):
                clean[k] = None
            elif isinstance(v, (float, int)) and k != "time":
                clean[k] = float(v)
            else:
                clean[k] = v
        rows.append(_round_row(clean, decimals))

    return {
        "symbol": symbol if not exchange else f"{symbol}@{exchange}",
        "tf": tf,
        "columns": final_cols,
        "rows": rows,
    }
