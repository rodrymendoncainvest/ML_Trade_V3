# api/app/routers/orders.py
from typing import Optional, Any, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, condecimal
from app.services.broker import get_broker, DEFAULT_TF

router = APIRouter(prefix="", tags=["orders"])

class OrderRequest(BaseModel):
    symbol: str
    exchange: Optional[str] = None
    side: str = Field(pattern="^(buy|sell)$")
    qty: float = Field(gt=0)
    type: str = Field(pattern="^(market|limit)$")
    limit_price: Optional[float] = None
    tf: Optional[str] = DEFAULT_TF

class OrderResponse(BaseModel):
    id: str
    symbol: str
    side: str
    qty: float
    type: str
    limit_price: Optional[float]
    status: str
    created_at: int
    updated_at: int

@router.post("/orders", response_model=OrderResponse)
def create_order(req: OrderRequest):
    try:
        broker = get_broker()
        o = broker.place_order(
            symbol=req.symbol,
            exchange=req.exchange,
            side=req.side,
            qty=req.qty,
            type_=req.type,
            limit_price=req.limit_price,
            tf=req.tf or DEFAULT_TF,
        )
        return o
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="internal-error")

@router.get("/orders", response_model=List[OrderResponse])
def list_orders(limit: int = 100):
    broker = get_broker()
    return broker.list_orders(limit=limit)

@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: str):
    try:
        broker = get_broker()
        return broker.cancel_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/positions")
def positions():
    broker = get_broker()
    return broker.get_positions()

@router.get("/account")
def account():
    broker = get_broker()
    return broker.get_account()
