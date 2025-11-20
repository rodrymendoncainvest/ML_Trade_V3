# app/services/symbols.py
from __future__ import annotations
from typing import Dict, List, Optional

_YAHOO_SUFFIX = {
    "XAMS": ".AS",
    "XPAR": ".PA",
    "XMIL": ".MI",
    "XLON": ".L",
    "XETR": ".DE",
    "XBRU": ".BR",
    "XLIS": ".LS",
}

def _yahoo_candidates(symbol: str, exchange: Optional[str]) -> List[str]:
    cands: List[str] = []
    if exchange and exchange in _YAHOO_SUFFIX:
        cands.append(f"{symbol}{_YAHOO_SUFFIX[exchange]}")
    cands.append(symbol)  # fallback US
    return cands

def _eodhd_candidates(symbol: str, exchange: Optional[str]) -> List[str]:
    return _yahoo_candidates(symbol, exchange)

def _twelvedata_candidates(symbol: str, exchange: Optional[str]) -> List[str]:
    cands: List[str] = []
    if exchange:
        cands.append(f"{symbol}:{exchange}")
    cands.append(symbol)
    return cands

def map_for_provider(symbol: str, exchange: Optional[str] = None) -> Dict[str, List[str]]:
    return {
        "yahoo": _yahoo_candidates(symbol, exchange),
        "twelvedata": _twelvedata_candidates(symbol, exchange),
        "eodhd": _eodhd_candidates(symbol, exchange),
    }

def resolve_for_provider(symbol: str, exchange: Optional[str], provider: Optional[str]) -> str:
    prov = (provider or "yahoo").lower()
    return map_for_provider(symbol, exchange).get(prov, [symbol])[0]

def resolve_symbol(symbol: str, exchange: Optional[str] = None, provider: Optional[str] = None) -> str:
    return resolve_for_provider(symbol, exchange, provider)
