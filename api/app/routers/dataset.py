# app/routers/dataset.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.services.symbols import resolve_symbol as _resolve_real, map_for_provider
from app.services.dataset import get_dataset  # usa a tua service existente

router = APIRouter(prefix="/dataset", tags=["dataset"])

# =========================
# SHIMS/HELPERS EXPORTADOS
# =========================

def _resolve_symbol(symbol: str, exchange: Optional[str] = None, provider: Optional[str] = None) -> str:
    return _resolve_real(symbol, exchange, provider or "yahoo")

def _normalize_columns_arg(columns: Any) -> List[str]:
    if columns is None:
        return []
    if isinstance(columns, list):
        return [str(c).strip() for c in columns if str(c).strip()]
    return [c.strip() for c in str(columns).split(",") if c.strip()]

def _coerce_to_df(obj: Any) -> Optional[pd.DataFrame]:
    """Aceita vários formatos de retorno da service e devolve DataFrame ou None."""
    if isinstance(obj, pd.DataFrame):
        return obj
    if isinstance(obj, tuple) and obj and isinstance(obj[0], pd.DataFrame):
        return obj[0]
    if isinstance(obj, dict):
        if "df" in obj and isinstance(obj["df"], pd.DataFrame):
            return obj["df"]
        if "data" in obj:
            data = obj["data"]
            if isinstance(data, pd.DataFrame):
                return data
            if isinstance(data, list):
                return pd.DataFrame(data)
        if "rows" in obj and isinstance(obj["rows"], list):
            return pd.DataFrame(obj["rows"])
    return None

def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # normaliza nomes para minúsculas e mapeia aliases comuns
    rename_map = {c: c.lower() for c in df.columns}
    df = df.rename(columns=rename_map)
    # aliases frequentes do Yahoo
    if "close" not in df.columns:
        if "adj close" in df.columns:
            df = df.rename(columns={"adj close": "close"})
        elif "closing" in df.columns:
            df = df.rename(columns={"closing": "close"})
        elif "price" in df.columns:
            df = df.rename(columns={"price": "close"})
    return df

def _is_good_df(df: Any, want_cols: List[str]) -> bool:
    if not isinstance(df, pd.DataFrame):
        return False
    if df.empty:
        return False
    for c in want_cols:
        if c.lower() == "time":
            continue
        if c not in df.columns:
            return False
    return True

def _df_to_rows(df: pd.DataFrame, want_cols: List[str], decimals: Optional[int] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    include_time = any(c.lower() == "time" for c in want_cols) or ("time" in df.columns)
    idx = df.index
    has_dt_index = isinstance(idx, pd.DatetimeIndex)

    values_cols = [c for c in want_cols if c.lower() != "time"]
    for i in range(len(df)):
        item: Dict[str, Any] = {}
        if include_time:
            if has_dt_index:
                epoch = int(pd.Timestamp(idx[i]).tz_localize(None).timestamp())
                item["time"] = epoch
            elif "time" in df.columns:
                item["time"] = int(df.iloc[i]["time"])
        for c in values_cols:
            val = df.iloc[i][c]
            if decimals is not None and isinstance(val, (int, float)):
                item[c] = round(float(val), int(decimals))
            else:
                item[c] = float(val) if isinstance(val, (int, float)) else val
        rows.append(item)
    return rows

def _safe_get_dataset(
    *,
    symbol: str,
    tf: str,
    columns: List[str],
    provider: str = "yahoo",
    dropna: bool = True,
    limit: Optional[int] = None,
    exchange: Optional[str] = None,
    decimals: Optional[int] = None,
    **_ignore: Any,
) -> Tuple[pd.DataFrame, str]:
    """
    - Resolve candidatos por provider (map_for_provider)
    - Tenta cada candidato
    - Aceita múltiplos formatos da service e normaliza para DataFrame
    - Garante colunas pedidas (excepto 'time')
    - Aplica limit no fim
    """
    want_cols = _normalize_columns_arg(columns)
    if not want_cols:
        raise HTTPException(status_code=422, detail={"error": "invalid-columns"})

    candidates = map_for_provider(symbol, exchange).get(provider.lower(), [symbol])
    last_err: Optional[str] = None

    for cand in candidates:
        try:
            raw = get_dataset(
                symbol=cand,
                tf=tf,
                columns=want_cols,
                provider=provider,
                dropna=dropna,
                limit=limit,
            )
            df = _coerce_to_df(raw)
            if df is None:
                last_err = "service returned non-DataFrame"
                continue

            # normalizar colunas
            df = _standardize_columns(df)

            # Drop NA apenas nas colunas pedidas (exclui 'time')
            drop_cols = [c for c in want_cols if c.lower() != "time" and c in df.columns]
            if dropna and drop_cols:
                df = df.dropna(subset=drop_cols)

            # Garantir ordem temporal (se houver DateTimeIndex)
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.sort_index()

            # Aplicar limit no fim
            if isinstance(limit, int) and limit > 0:
                df = df.tail(limit)

            if _is_good_df(df, want_cols):
                return df, cand

            last_err = "empty"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)

    raise HTTPException(status_code=500, detail={"error": "dataset-failed", "message": last_err or "empty"})

# ==========
# ENDPOINT
# ==========

@router.get("/")
def get_dataset_endpoint(
    symbol: str = Query(..., description="Ticker base (ex.: ASML, ASML.AS)"),
    tf: str = Query(..., description="Timeframe: 1d, 1h, etc."),
    columns: str = Query(..., description="Lista: ex. time,close,open"),
    exchange: Optional[str] = Query(None, description="Exchange ISO (ex.: XAMS, XPAR, XMIL)"),
    provider: str = Query("yahoo", description="Provider preferido"),
    dropna: bool = Query(True),
    limit: Optional[int] = Query(None),
    decimals: Optional[int] = Query(None),
) -> Dict[str, Any]:
    want_cols = _normalize_columns_arg(columns)
    df, resolved = _safe_get_dataset(
        symbol=symbol,
        tf=tf,
        columns=want_cols,
        provider=provider,
        dropna=dropna,
        limit=limit,
        exchange=exchange,
        decimals=decimals,
    )
    rows = _df_to_rows(df, want_cols, decimals=decimals)
    return {
        "symbol": resolved,
        "tf": tf,
        "columns": want_cols,
        "rows": rows,
    }
