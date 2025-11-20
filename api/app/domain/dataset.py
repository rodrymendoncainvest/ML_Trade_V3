from typing import List, Dict, Any
from pydantic import BaseModel

# Base + features mais comuns (dinâmicos como sma20/rsi14 são aceites no router)
ALLOWED_COLUMNS = {
    "time","open","high","low","close","volume",
    "hlc3",
    "sma5","sma10","sma20","sma50","sma100","sma200",
    "ema12","ema20","ema50",
    "rsi7","rsi14"
}

class DatasetResponse(BaseModel):
    symbol: str
    tf: str
    columns: List[str]
    rows: List[Dict[str, Any]]
