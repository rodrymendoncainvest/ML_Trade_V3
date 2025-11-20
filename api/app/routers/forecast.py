from fastapi import APIRouter

router = APIRouter()

@router.get("/{symbol}")
def get_forecast(symbol: str, week: str | None = None) -> dict:
    # Stub — T7/T8 produzem previsões, T9 expõe via WS
    return {"symbol": symbol, "y_hat": None, "conf_int": None, "updated_at": None}
