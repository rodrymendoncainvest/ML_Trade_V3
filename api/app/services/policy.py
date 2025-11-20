import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from app.services.paper_db import get_last_price, get_position


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "y", "on")


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    try:
        return float(v)
    except Exception:
        return default


@dataclass
class RiskConfig:
    allow_short: bool
    max_order_value: float
    max_symbol_qty: float
    max_position_value: float

    @staticmethod
    def load() -> "RiskConfig":
        return RiskConfig(
            allow_short=_env_bool("PAPER_ALLOW_SHORT", False),
            max_order_value=_env_float("PAPER_MAX_ORDER_VALUE", 1e12),
            max_symbol_qty=_env_float("PAPER_MAX_SYMBOL_QTY", 1e12),
            max_position_value=_env_float("PAPER_MAX_POSITION_VALUE", 1e12),
        )

    def as_dict(self) -> Dict:
        return {
            "allow_short": self.allow_short,
            "max_order_value": self.max_order_value,
            "max_symbol_qty": self.max_symbol_qty,
            "max_position_value": self.max_position_value,
        }


def _price_for_check(
    otype: str,
    ref_price: Optional[float],
    limit_price: Optional[float],
    stop_price: Optional[float],
    symbol: str,
) -> Tuple[Optional[float], Optional[str]]:
    """
    Preço de referência para validar risco:
      - market:   ref_price (ou último close 1h -> 1d)
      - limit:    limit_price
      - stop:     stop_price
    """
    if otype == "market":
        if ref_price is not None:
            return float(ref_price), None
        last, tf = get_last_price(symbol)
        return (float(last), tf) if last is not None else (None, None)
    if otype == "limit":
        return (None if limit_price is None else float(limit_price), None)
    if otype == "stop":
        return (None if stop_price is None else float(stop_price), None)
    return None, None


def _resulting_qty(current_qty: float, side: str, qty: float) -> float:
    return current_qty + qty if side == "buy" else current_qty - qty


def check_new_order(
    *,
    symbol: str,
    side: str,
    qty: float,
    otype: str,
    ref_price: Optional[float] = None,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    cfg: Optional[RiskConfig] = None,
) -> Dict:
    """
    Retorna: {"ok": bool, "rule": <str>|None, "message": <str>|None, "checked_price": <float>|None}
    """
    cfg = cfg or RiskConfig.load()

    # 1) preço de referência para as validações de valor
    price_for_check, _tf = _price_for_check(otype, ref_price, limit_price, stop_price, symbol)
    # Para limites como max_symbol_qty podemos não precisar do preço; para valores sim.
    # Se não houver preço e for regra de valor que precise, falha educadamente.
    # (ordem limit/stop sem preço definido não deve acontecer – validamos no router também)

    # 2) posição atual
    pos = get_position(symbol)
    cur_qty = float(pos["qty"]) if pos else 0.0

    # 3) SHORT permitido?
    new_qty = _resulting_qty(cur_qty, side, float(qty))
    if not cfg.allow_short and new_qty < 0:
        return {
            "ok": False,
            "rule": "allow_short",
            "message": f"Short não permitido. Qty atual {cur_qty}, ordem {side} {qty} => ficaria {new_qty} < 0.",
            "checked_price": price_for_check,
        }

    # 4) max_symbol_qty (limite sobre a quantidade resultante absoluta)
    if abs(new_qty) > cfg.max_symbol_qty:
        return {
            "ok": False,
            "rule": "max_symbol_qty",
            "message": f"Limite de quantidade por símbolo excedido. abs({new_qty}) > {cfg.max_symbol_qty}.",
            "checked_price": price_for_check,
        }

    # 5) max_order_value (limite sobre o valor da ordem)
    if price_for_check is None:
        # Se é market e não temos preço, bloquear — não sabemos avaliar risco
        if otype == "market":
            return {
                "ok": False,
                "rule": "price_missing",
                "message": "Sem preço de mercado para validar a ordem.",
                "checked_price": None,
            }
        # Para limit/stop deveria existir limit_price/stop_price
        if otype == "limit" and limit_price is None:
            return {
                "ok": False,
                "rule": "limit_price_missing",
                "message": "limit_price ausente.",
                "checked_price": None,
            }
        if otype == "stop" and stop_price is None:
            return {
                "ok": False,
                "rule": "stop_price_missing",
                "message": "stop_price ausente.",
                "checked_price": None,
            }

    if price_for_check is not None:
        order_value = float(qty) * float(price_for_check)
        if order_value > cfg.max_order_value:
            return {
                "ok": False,
                "rule": "max_order_value",
                "message": f"Valor da ordem {order_value:.2f} excede o máximo {cfg.max_order_value:.2f}.",
                "checked_price": price_for_check,
            }

    # 6) max_position_value (limite sobre o valor absoluto da posição resultante)
    if price_for_check is not None:
        result_pos_value = abs(new_qty) * float(price_for_check)
        if result_pos_value > cfg.max_position_value:
            return {
                "ok": False,
                "rule": "max_position_value",
                "message": f"Valor da posição resultante {result_pos_value:.2f} excede o máximo {cfg.max_position_value:.2f}.",
                "checked_price": price_for_check,
            }

    return {"ok": True, "rule": None, "message": None, "checked_price": price_for_check}


def current_policy() -> Dict:
    return RiskConfig.load().as_dict()
