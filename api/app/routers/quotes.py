# api/app/routers/quotes.py
# -------------------------------------------------------------
# Endpoint universal de OHLC para qualquer ticker e timeframe.
# Funciona com Yahoo Finance e devolve formato padronizado
# para o frontend React (PriceChart).
# -------------------------------------------------------------

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import yfinance as yf
import pandas as pd
import time

router = APIRouter(prefix="/quotes", tags=["quotes"])


# -------------------------------------------------------------
# Tipos de resposta
# -------------------------------------------------------------

class OhlcBar(BaseModel):
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class OhlcResponse(BaseModel):
    ok: bool
    symbol: str
    tf: str
    limit: int
    rows: list[OhlcBar]


# -------------------------------------------------------------
# Timeframes suportados → conversão para intervalos do Yahoo
# -------------------------------------------------------------

YF_INTERVALS = {
    "1d": "1d",
    "1h": "60m",
    "30m": "30m",
    "15m": "15m",
    "5m": "5m",
}

# Limite máximo que o Yahoo devolve por cada timeframe
YF_MAX_LIMIT = 10000


# -------------------------------------------------------------
# Função utilitária: normalizar timestamps
# -------------------------------------------------------------

def normalize_ts(ts):
    """Converte numpy datetime para unix seconds."""
    if isinstance(ts, pd.Timestamp):
        return int(ts.timestamp())
    if isinstance(ts, float) or isinstance(ts, int):
        return int(ts)
    return int(time.time())


# -------------------------------------------------------------
# Rota principal: /quotes/ohlc
# -------------------------------------------------------------

@router.get("/ohlc", response_model=OhlcResponse)
async def get_ohlc(symbol: str, tf: str, limit: int = 500):
    """
    Devolve candles OHLC normalizados para um ticker.
    Usa Yahoo Finance e converte o formato para o frontend.
    """
    if tf not in YF_INTERVALS:
        raise HTTPException(status_code=400, detail="Timeframe inválido.")

    yf_interval = YF_INTERVALS[tf]

    # Yahoo Finance não permite limites baixos quando há caching interno.
    real_limit = min(limit, YF_MAX_LIMIT)

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            interval=yf_interval,
            period="max" if tf == "1d" else "60d"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao obter dados: {str(e)}")

    if df is None or df.empty:
        return OhlcResponse(ok=False, symbol=symbol, tf=tf, limit=limit, rows=[])

    df = df.tail(real_limit)
    df = df.reset_index()

    if "Datetime" in df.columns:
        df.rename(columns={"Datetime": "timestamp"}, inplace=True)
    elif "Date" in df.columns:
        df.rename(columns={"Date": "timestamp"}, inplace=True)
    else:
        df["timestamp"] = df.index

    rows = []
    for _, row in df.iterrows():
        try:
            ts = normalize_ts(row["timestamp"])
            rows.append(OhlcBar(
                ts=ts,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]) if not pd.isna(row["Volume"]) else 0.0,
            ))
        except Exception:
            continue

    return OhlcResponse(
        ok=True,
        symbol=symbol,
        tf=tf,
        limit=limit,
        rows=rows,
    )
