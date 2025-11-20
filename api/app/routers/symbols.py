from typing import Optional, Dict, Any
from fastapi import APIRouter, Query
from app.services.symbols import map_for_provider

router = APIRouter(prefix="/symbols", tags=["symbols"])

@router.get("/map")
def symbols_map(
    symbol: str = Query(..., description="Ticker base, e.g., ASML, STM, MC"),
    exchange: Optional[str] = Query(None, description="Exchange MIC, e.g., XAMS, XPAR, XMIL"),
) -> Dict[str, Any]:
    mapping = map_for_provider(symbol, exchange)
    return {
        "input": {"symbol": symbol, "exchange": exchange},
        "providers": mapping,
    }
