import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, validator

from app.services.symbols import resolve_symbol
from app.services.paper_db import (
    cancel_order,
    get_order_by_id,
    get_position,
    get_last_price,
    list_orders,
    list_positions,
    place_order,
    portfolio,
    reset_all,
    trigger_open_orders,
)
from app.services.policy import check_new_order, current_policy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/paper", tags=["paper"])

# --------- Models ---------

class NewOrder(BaseModel):
    symbol: str
    exchange: Optional[str] = Field(default=None, description="Ex: XAMS")
    side: str
    qty: float
    type: str = "market"  # market | limit | stop
    price: Optional[float] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    provider: Optional[str] = "yahoo"

    @validator("side")
    def _side_ok(cls, v):
        if v not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        return v

    @validator("type")
    def _type_ok(cls, v):
        if v not in ("market", "limit", "stop"):
            raise ValueError("type must be market|limit|stop")
        return v

    @validator("qty")
    def _qty_pos(cls, v):
        if v <= 0:
            raise ValueError("qty must be > 0")
        return v


class CancelResponse(BaseModel):
    ok: bool
    reason: Optional[str] = None


# --------- Endpoints ---------

@router.post("/orders")
def create_order(body: NewOrder) -> Dict[str, Any]:
    """
    - market: executa já (usa price ou último close 1h→1d)
    - limit:  'open' até last <= limit (buy) / last >= limit (sell)
    - stop:   'open' até last >= stop (buy)  / last <= stop  (sell)
    Aplica política de risco ANTES da criação.
    """
    try:
        # resolve símbolo
        resolved = resolve_symbol(body.symbol, body.exchange, body.provider or "yahoo")

        # preço de referência para a política
        if body.type == "market":
            ref_price = body.price
            if ref_price is None:
                ref_price, _tf = get_last_price(resolved)
        elif body.type == "limit":
            ref_price = body.limit_price
        else:  # stop
            ref_price = body.stop_price

        # valida política
        pr = check_new_order(
            symbol=resolved,
            side=body.side,
            qty=body.qty,
            otype=body.type,
            ref_price=ref_price,
            limit_price=body.limit_price,
            stop_price=body.stop_price,
        )
        if not pr["ok"]:
            raise HTTPException(status_code=422, detail={"error": "risk", "rule": pr["rule"], "message": pr["message"]})

        # cria ordem (paper_db trata de execução/imediata ou open)
        resp = place_order(
            symbol=resolved,
            exchange=body.exchange,
            side=body.side,
            qty=body.qty,
            otype=body.type,
            price=body.price,
            limit_price=body.limit_price,
            stop_price=body.stop_price,
        )
        # anexa meta de risco útil
        if pr.get("checked_price") is not None:
            resp["risk_checked_price"] = pr["checked_price"]
        return resp

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=422, detail={"error": "invalid", "message": str(ve)})
    except Exception as ex:
        logger.exception("order-failed")
        raise HTTPException(status_code=500, detail={"error": "internal", "message": str(ex)})


@router.get("/orders")
def get_orders(status: Optional[str] = Query(default=None), limit: int = 50):
    if status and status not in ("open", "filled", "cancelled"):
        raise HTTPException(status_code=422, detail={"error": "invalid", "message": "status must be open|filled|cancelled"})
    return list_orders(status=status, limit=limit)


@router.get("/orders/{order_id}")
def get_order(order_id: int) -> Dict[str, Any]:
    try:
        return {"order": get_order_by_id(order_id)}
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": "not-found"})


@router.delete("/orders/{order_id}")
def delete_order(order_id: int) -> CancelResponse:
    res = cancel_order(order_id)
    return CancelResponse(**res)


@router.post("/trigger")
def trigger() -> Dict[str, Any]:
    try:
        return trigger_open_orders()
    except Exception as ex:
        logger.exception("trigger-failed")
        raise HTTPException(status_code=500, detail={"error": "internal", "message": str(ex)})


@router.get("/positions")
def positions(mark_to_market: bool = False) -> Dict[str, Any]:
    return list_positions(mark_to_market=mark_to_market)


@router.get("/portfolio")
def portfolio_view(mark_to_market: bool = True) -> Dict[str, Any]:
    return portfolio(mark_to_market=mark_to_market)


@router.get("/policy")
def policy_view() -> Dict[str, Any]:
    """Ver política atual (deriva do ambiente)."""
    return {"policy": current_policy()}


@router.delete("/reset")
def paper_reset() -> Dict[str, Any]:
    if not (os.getenv("DEBUG") in ("1", "true", "True")):
        raise HTTPException(status_code=405, detail="Method Not Allowed")
    reset_all()
    return {"ok": True}


logger.info("Router carregado: app.routers.paper")
