from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, Dict, List

import os
import pandas as pd
import yfinance as yf

try:
    import requests  # usado só para EODHD (EOD / daily+)
except ImportError:  # se não existir, simplesmente não usamos EODHD
    requests = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Timeframes e mapeamentos
# ---------------------------------------------------------------------------

_INTERVAL_MAP: Dict[str, str] = {
    "1m": "1m",
    "2m": "2m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "60m": "60m",
    "1h": "60m",
    "90m": "90m",
    "1d": "1d",
    "5d": "5d",
    "1wk": "1wk",
    "1mo": "1mo",
    "3mo": "3mo",
}
_ALLOWED_TF = set(_INTERVAL_MAP.keys())

INTRADAY_TFS = {"1m", "2m", "5m", "15m", "30m", "60m", "1h", "90m"}
EOD_TFS = {"1d", "5d", "1wk", "1mo", "3mo"}

# Defaults/YF config (podem ser override por .env)
YF_RANGE_60M_DEFAULT = "30d"
YF_RANGE_SUBH_DEFAULT = "7d"

YF_RANGE_60M = os.getenv("YF_RANGE_60M", YF_RANGE_60M_DEFAULT)
YF_RANGE_SUBH = os.getenv("YF_RANGE_SUBH", YF_RANGE_SUBH_DEFAULT)

# EODHD config
EODHD_KEY = os.getenv("EODHD_KEY", "").strip()
EODHD_INTRADAY = os.getenv("EODHD_INTRADAY", "0").strip()  # só para garantir política


# ---------------------------------------------------------------------------
# Normalização comum de OHLCV para o formato interno
# ---------------------------------------------------------------------------

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza qualquer DataFrame OHLCV para colunas:

        ts, open, high, low, close, volume

    - ts: datetime (naive, UTC)
    - volume: >= 0, NaN -> 0
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])

    # Renomear colunas para lower
    cols = {c.lower(): c for c in df.columns}
    rename_map: Dict[str, str] = {}

    for want in ["open", "high", "low", "close", "volume"]:
        if want in cols:
            rename_map[cols[want]] = want

    df = df.rename(columns=rename_map)

    # Construir coluna ts
    if isinstance(df.index, pd.DatetimeIndex):
        ts = df.index
    elif "datetime" in df.columns:
        ts = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    elif "date" in df.columns:
        ts = pd.to_datetime(df["date"], utc=True, errors="coerce")
    else:
        ts = pd.to_datetime(df.index, utc=True, errors="coerce")

    # Garantir UTC naive
    if getattr(ts, "tz", None) is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    else:
        # assume naive -> UTC
        ts = ts.tz_localize("UTC").tz_convert("UTC").tz_localize(None)

    df = df.assign(ts=ts.values)

    # Garantir colunas base
    keep = ["ts", "open", "high", "low", "close", "volume"]
    for k in keep:
        if k not in df.columns:
            df[k] = pd.NA

    df = df[keep]
    df = df.dropna(subset=["ts", "close"]).sort_values("ts").reset_index(drop=True)

    # Numéricos
    for k in ["open", "high", "low", "close", "volume"]:
        df[k] = pd.to_numeric(df[k], errors="coerce")

    df = df.dropna(subset=["close"])

    if "volume" in df.columns:
        df["volume"] = df["volume"].fillna(0).clip(lower=0)

    return df


# ---------------------------------------------------------------------------
# Helpers de providers
# ---------------------------------------------------------------------------

def resolve_symbol(symbol: str) -> str:
    return symbol.strip().upper()


# ----- yfinance loader ------------------------------------------------------

def _load_ohlc_yf(
    symbol: str,
    tf: str,
    *,
    limit: int = 1500,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    Loader base usando yfinance.

    - Intraday: usa period dinamicamente com YF_RANGE_SUBH / YF_RANGE_60M
    - EOD: usa period fixo em função do tf (5y / 20y / 60d)
    """
    if tf not in _ALLOWED_TF:
        raise ValueError(f"tf inválido: {tf}. Aceites: {sorted(_ALLOWED_TF)}")

    yf_symbol = resolve_symbol(symbol)
    interval = _INTERVAL_MAP[tf]
    ticker = yf.Ticker(yf_symbol)

    kwargs = dict(interval=interval, auto_adjust=False, prepost=False)

    # start/end explícitos
    if start or end:
        if start and start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        raw = ticker.history(start=start, end=end, **kwargs)
    else:
        # Sem start/end -> escolher period
        if tf in INTRADAY_TFS:
            if tf in {"60m", "1h", "90m"}:
                period = YF_RANGE_60M
            else:
                period = YF_RANGE_SUBH
        else:
            if tf in {"1d", "5d"}:
                period = "5y"
            elif tf in {"1wk", "1mo", "3mo"}:
                period = "20y"
            else:
                period = "60d"
        raw = ticker.history(period=period, **kwargs)

    df = _normalize_df(raw)
    if limit and limit > 0:
        df = df.tail(limit).reset_index(drop=True)

    return df


# ----- EODHD EOD loader (daily/weekly/monthly only) ------------------------

def _load_ohlc_eodhd_eod(
    symbol: str,
    tf: str,
    *,
    limit: int = 1500,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    Loader EODHD para EOD (timeframes >= 1d).

    Notas importantes:
      - NÃO é usado para intraday (INTRADAY_TFS).
      - Depende de EODHD_KEY no .env.
      - Assume símbolo no mercado US por omissão (pode precisar ajustes futuros).
    """
    if tf not in EOD_TFS:
        # Por segurança, nunca usar EODHD para intraday ou TFs fora de EOD_TFS
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])

    if not EODHD_KEY or requests is None:
        # Sem key ou sem requests -> não usamos EODHD
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])

    # Política explícita: EODHD_INTRADAY=0 -> intraday desativado (já cumprido)    
    # Construir range de datas
    now_utc = datetime.now(timezone.utc)

    if end is None:
        end = now_utc

    if start is None:
        # Heurística simples: pedir 2x o número de dias pretendidos, até máx ~20 anos
        days_back = min(max(limit * 2, 365), 365 * 20)
        start = end - timedelta(days=days_back)

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    from_str = start.strftime("%Y-%m-%d")
    to_str = end.strftime("%Y-%m-%d")

    # ATENÇÃO: isto assume mercado US (".US").
    # Se no futuro quiseres generalizar, precisas de mapear símbolo -> exchange.
    base_url = "https://eodhistoricaldata.com/api/eod"
    eod_symbol = f"{resolve_symbol(symbol)}.US"
    url = f"{base_url}/{eod_symbol}"
    params = {
        "api_token": EODHD_KEY,
        "from": from_str,
        "to": to_str,
        "period": "d",
        "fmt": "json",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)  # type: ignore[arg-type]
        if resp.status_code != 200:
            return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])
        data = resp.json()
        if not isinstance(data, list) or not data:
            return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])
        df = pd.DataFrame(data)
    except Exception:
        # Qualquer erro de rede/parsing -> tratamos como sem dados
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])

    # Esperado: colunas tipo date, open, high, low, close, adjusted_close, volume
    if "date" not in df.columns:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])

    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df = df.set_index("date")

    # Normalizar para OHLCV diário
    daily = df.copy()
    daily = daily.rename(
        columns={
            "adjusted_close": "adj_close",
            "close": "close",
            "open": "open",
            "high": "high",
            "low": "low",
            "volume": "volume",
        }
    )

    # Agora, se tf > 1d, fazemos resample a partir deste diário
    if tf == "1d":
        out = daily
    else:
        # Definir rule de resample
        if tf == "5d":
            rule = "5D"
        elif tf == "1wk":
            rule = "W"
        elif tf == "1mo":
            rule = "M"
        elif tf == "3mo":
            rule = "Q"
        else:
            # fallback: não devíamos chegar aqui
            rule = "D"

        agg = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
        out = daily.resample(rule).agg(agg).dropna(how="any")

    out = _normalize_df(out)

    if limit and limit > 0:
        out = out.tail(limit).reset_index(drop=True)

    return out


# ---------------------------------------------------------------------------
# API pública: get_ohlc / get_quotes / latest_close
# ---------------------------------------------------------------------------

def get_ohlc(
    symbol: str,
    tf: Literal[
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "1h",
        "90m",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    ],
    *,
    limit: int = 1500,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    Loader principal de OHLCV, com política:

      - Intraday (tf em INTRADAY_TFS):
          -> yfinance APENAS (grátis)
          -> sem fallback para EODHD (não tem intraday no plano atual)

      - EOD (tf em EOD_TFS):
          -> tenta yfinance primeiro
          -> se vier vazio, tenta EODHD (EOD only)
          -> se ambos falharem, devolve DataFrame vazio
    """
    if tf not in _ALLOWED_TF:
        raise ValueError(f"tf inválido: {tf}. Aceites: {sorted(_ALLOWED_TF)}")

    # INTRADAY: yfinance only
    if tf in INTRADAY_TFS:
        df_yf = _load_ohlc_yf(symbol, tf, limit=limit, start=start, end=end)
        return df_yf

    # EOD/daily+: yfinance -> fallback EODHD
    df_yf = _load_ohlc_yf(symbol, tf, limit=limit, start=start, end=end)
    if not df_yf.empty:
        return df_yf

    # fallback: EODHD para EOD (se disponível)
    df_eodhd = _load_ohlc_eodhd_eod(symbol, tf, limit=limit, start=start, end=end)
    return df_eodhd


def get_quotes(symbol: str, tf: str, *, limit: int = 1500) -> pd.DataFrame:
    """
    Wrapper compatível com código antigo.
    """
    return get_ohlc(symbol, tf, limit=limit)


def latest_close(symbol: str, tf: str = "1d") -> Optional[float]:
    df = get_ohlc(symbol, tf, limit=1)
    if df.empty:
        return None
    return float(df["close"].iloc[-1])
