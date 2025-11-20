# app/services/resolver.py
from __future__ import annotations
from typing import Optional, Tuple

# Mapeamentos de exchange -> sufixos (Yahoo/EODHD) e sintaxe (TwelveData)
_YAHOO_SUFFIX = {
    "XAMS": ".AS", "ENXTAM": ".AS",
    "XPAR": ".PA", "ENXTPA": ".PA",
    "XMIL": ".MI", "XMTA": ".MI", "BIT": ".MI",
    "XLON": ".L",
    "XETR": ".DE",
    "XNAS": "", "XNYS": "",
}
_TD_EXCHANGE = {
    "XAMS": "XAMS", "ENXTAM": "XAMS",
    "XPAR": "XPAR", "ENXTPA": "XPAR",
    "XMIL": "XMIL", "XMTA": "XMIL", "BIT": "XMIL",
    "XLON": "LSE",
    "XETR": "XETR",
    "XNAS": "XNAS", "XNYS": "XNYS",
}

def _norm_exchange(ex: Optional[str]) -> Optional[str]:
    if not ex:
        return None
    exu = ex.strip().upper()
    aliases = {
        "AMS": "XAMS", "PAR": "XPAR", "MIL": "XMIL", "MTA": "XMTA",
        "NAS": "XNAS", "NMS": "XNAS", "NYS": "XNYS", "NYSE": "XNYS",
        "PARIS": "XPAR", "AMSTERDAM": "XAMS",
        "EURONEXT PARIS": "XPAR", "EURONEXT AMSTERDAM": "XAMS",
    }
    return aliases.get(exu, exu)

def _already_qualified(symbol: str) -> bool:
    return (":" in symbol) or ("." in symbol)

def qualify_for_provider(symbol: str, exchange: Optional[str], provider: str) -> str:
    """
    Devolve ticker no formato certo para o provider.
    Respeita símbolos já qualificados (ASML.AS / ASML:XAMS / etc.).
    """
    symbol = symbol.strip()
    if _already_qualified(symbol):
        return symbol

    ex = _norm_exchange(exchange)
    p = (provider or "").strip().lower()

    if p in ("yahoo", "eodhd"):
        if not ex:
            return symbol
        suf = _YAHOO_SUFFIX.get(ex, "")
        return f"{symbol}{suf}"
    elif p == "twelvedata":
        if not ex:
            return symbol
        td_ex = _TD_EXCHANGE.get(ex)
        return f"{symbol}:{td_ex}" if td_ex else symbol
    else:
        return symbol

def prefer_qualified(symbol: str, exchange: Optional[str], preferred: str = "yahoo") -> str:
    """Qualificação 'amigável' (Yahoo) quando não fixamos provider."""
    return qualify_for_provider(symbol, exchange, preferred)

def qualify_scan_item(item: str) -> Tuple[str, Optional[str]]:
    """
    Suporta 'SYMBOL|EXCHANGE' em scans; caso contrário devolve (symbol, None).
    """
    raw = item.strip()
    if "|" in raw:
        sym, ex = raw.split("|", 1)
        return sym.strip(), _norm_exchange(ex)
    return raw, None
