from __future__ import annotations

import io
import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.ml.engine_backtest import (
    run_backtest,
    sweep_thresholds,
    optimize_threshold,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ml-backtest"])


@router.get("/backtest")
def backtest_get(
    symbol: str,
    tf: str = "1d",
    limit: int = 300,
    threshold: float = 0.55,
    fees_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> Dict[str, Any]:
    try:
        res, _, _ = run_backtest(symbol, tf, limit, threshold, fees_bps, slippage_bps)
        return res
    except Exception as exc:
        logger.exception("Erro em /ml/backtest")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/backtest/equity.csv")
def backtest_equity_csv_get(
    symbol: str,
    tf: str = "1d",
    limit: int = 300,
    threshold: float = 0.55,
    fees_bps: float = 0.0,
    slippage_bps: float = 0.0,
):
    try:
        _, equity, _ = run_backtest(symbol, tf, limit, threshold, fees_bps, slippage_bps)
    except Exception as exc:
        logger.exception("Erro em /ml/backtest/equity.csv")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    df = equity.to_frame("equity")
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=True)
    csv_buf.seek(0)

    return StreamingResponse(
        csv_buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="equity_{symbol}_{tf}.csv"'},
    )


@router.get("/backtest/trades.csv")
def backtest_trades_csv_get(
    symbol: str,
    tf: str = "1d",
    limit: int = 300,
    threshold: float = 0.55,
    fees_bps: float = 0.0,
    slippage_bps: float = 0.0,
):
    try:
        _, _, trades_df = run_backtest(symbol, tf, limit, threshold, fees_bps, slippage_bps)
    except Exception as exc:
        logger.exception("Erro em /ml/backtest/trades.csv")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    csv_buf = io.StringIO()
    trades_df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    return StreamingResponse(
        csv_buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="trades_{symbol}_{tf}.csv"'},
    )


@router.get("/backtest/sweep")
def sweep_get(
    symbol: str,
    tf: str = "1d",
    limit: int = 300,
    thresholds: str = Query("0.50:0.65:0.01"),
    metric: str = "expectancy",
    fees_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> Dict[str, Any]:
    try:
        t0, t1, step = [float(x) for x in thresholds.split(":")]
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Formato inválido de thresholds: {thresholds}. Esperado: '0.50:0.65:0.01'.",
        )

    thr_list: List[float] = list(np.arange(t0, t1 + 1e-9, step))

    try:
        return sweep_thresholds(symbol, tf, limit, thr_list, metric, fees_bps, slippage_bps)
    except Exception as exc:
        logger.exception("Erro em /ml/backtest/sweep")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/backtest/sweep.csv")
def sweep_csv_get(
    symbol: str,
    tf: str = "1d",
    limit: int = 300,
    thresholds: str = Query("0.50:0.65:0.01"),
    metric: str = "expectancy",
    fees_bps: float = 0.0,
    slippage_bps: float = 0.0,
):
    try:
        t0, t1, step = [float(x) for x in thresholds.split(":")]
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Formato inválido de thresholds: {thresholds}. Esperado: '0.50:0.65:0.01'.",
        )

    thr_list: List[float] = list(np.arange(t0, t1 + 1e-9, step))

    try:
        res = sweep_thresholds(symbol, tf, limit, thr_list, metric, fees_bps, slippage_bps)
    except Exception as exc:
        logger.exception("Erro em /ml/backtest/sweep.csv")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    df = pd.DataFrame(res["rows"])
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    return StreamingResponse(
        csv_buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="sweep_{symbol}_{tf}.csv"'},
    )


@router.get("/optimize")
def optimize_get(
    symbol: str,
    tf: str = "1d",
    limit: int = 300,
    thresholds: str = Query("0.50:0.65:0.01"),
    metric: str = "expectancy",
    fees_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> Dict[str, Any]:
    try:
        t0, t1, step = [float(x) for x in thresholds.split(":")]
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Formato inválido de thresholds: {thresholds}. Esperado: '0.50:0.65:0.01'.",
        )

    thr_list: List[float] = list(np.arange(t0, t1 + 1e-9, step))

    try:
        return optimize_threshold(symbol, tf, limit, thr_list, metric, fees_bps, slippage_bps)
    except Exception as exc:
        logger.exception("Erro em /ml/optimize")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/optimize.csv")
def optimize_csv_get(
    symbol: str,
    tf: str = "1d",
    limit: int = 300,
    thresholds: str = Query("0.50:0.65:0.01"),
    metric: str = "expectancy",
    fees_bps: float = 0.0,
    slippage_bps: float = 0.0,
):
    try:
        t0, t1, step = [float(x) for x in thresholds.split(":")]
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Formato inválido de thresholds: {thresholds}. Esperado: '0.50:0.65:0.01'.",
        )

    thr_list: List[float] = list(np.arange(t0, t1 + 1e-9, step))

    try:
        res = optimize_threshold(symbol, tf, limit, thr_list, metric, fees_bps, slippage_bps)
    except Exception as exc:
        logger.exception("Erro em /ml/optimize.csv")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    df = pd.DataFrame([res["best_row"]])
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    return StreamingResponse(
        csv_buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="opt_{symbol}_{tf}.csv"'},
    )
