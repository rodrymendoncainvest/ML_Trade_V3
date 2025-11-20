import os
import time
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import requests

DB_PATH = os.getenv("PAPER_DB_PATH", "/app/data/paper.db")
INTERNAL_BASE_URL = os.getenv("INTERNAL_BASE_URL", "http://localhost:8000")
STARTING_CASH = float(os.getenv("PAPER_STARTING_CASH", "100000"))  # cash inicial

# ----------------------------
# DB helpers
# ----------------------------

def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn

def _ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # positions
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS positions (
            symbol TEXT PRIMARY KEY,
            qty REAL NOT NULL,
            avg_price REAL NOT NULL
        )
        """
    )

    # orders alvo
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('buy','sell')),
            qty REAL NOT NULL,
            type TEXT NOT NULL DEFAULT 'market' CHECK(type IN ('market','limit','stop')),
            status TEXT NOT NULL CHECK(status IN ('open','filled','cancelled','rejected')),
            price REAL,
            limit_price REAL,
            stop_price REAL,
            value REAL,
            filled_qty REAL NOT NULL DEFAULT 0.0,
            exchange TEXT,
            realized_pnl REAL
        )
        """
    )

    # colunas novas em bases antigas
    cols = {r["name"] for r in cur.execute("PRAGMA table_info(orders)").fetchall()}
    if "type" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN type TEXT NOT NULL DEFAULT 'market'")
    if "status" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN status TEXT NOT NULL DEFAULT 'filled'")
    if "limit_price" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN limit_price REAL")
    if "stop_price" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN stop_price REAL")
    if "filled_qty" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN filled_qty REAL NOT NULL DEFAULT 0.0")
    if "exchange" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN exchange TEXT")
    if "realized_pnl" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN realized_pnl REAL")

    # MIGRAÇÃO: remover NOT NULL de price, se existir
    info = cur.execute("PRAGMA table_info(orders)").fetchall()
    colinfo = {row["name"]: row for row in info}
    if "price" in colinfo and colinfo["price"]["notnull"] == 1:
        _migrate_orders_nullable_price(conn)

    # portfolio: caixa + realized
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY CHECK(id=1),
            starting_cash REAL NOT NULL,
            cash REAL NOT NULL,
            realized_pnl REAL NOT NULL
        )
        """
    )
    row = cur.execute("SELECT id FROM portfolio WHERE id=1").fetchone()
    if not row:
        cur.execute(
            "INSERT INTO portfolio(id, starting_cash, cash, realized_pnl) VALUES(1, ?, ?, 0.0)",
            (STARTING_CASH, STARTING_CASH),
        )

def _migrate_orders_nullable_price(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('buy','sell')),
            qty REAL NOT NULL,
            type TEXT NOT NULL DEFAULT 'market' CHECK(type IN ('market','limit','stop')),
            status TEXT NOT NULL CHECK(status IN ('open','filled','cancelled','rejected')),
            price REAL,
            limit_price REAL,
            stop_price REAL,
            value REAL,
            filled_qty REAL NOT NULL DEFAULT 0.0,
            exchange TEXT,
            realized_pnl REAL
        )
        """
    )

    cur_cols = [r["name"] for r in cur.execute("PRAGMA table_info(orders)").fetchall()]
    colset = set(cur_cols)

    def sel(col: str, default_sql: str) -> str:
        return col if col in colset else f"{default_sql} AS {col}"

    select_sql = f"""
        SELECT
          {sel('id', 'NULL')},
          {sel('ts', 'CAST(strftime("%s","now") AS INTEGER)')},
          {sel('symbol', "''")},
          {sel('side', "CASE WHEN 1=1 THEN 'buy' END")},
          {sel('qty', '0.0')},
          {sel('type', "'market'")},
          {sel('status', "CASE WHEN price IS NULL THEN 'open' ELSE 'filled' END")},
          {sel('price', 'NULL')},
          {sel('limit_price', 'NULL')},
          {sel('stop_price', 'NULL')},
          {sel('value', 'NULL')},
          {sel('filled_qty', "CASE WHEN price IS NULL THEN 0.0 ELSE qty END")},
          {sel('exchange', 'NULL')},
          {sel('realized_pnl', 'NULL')}
        FROM orders
        ORDER BY id
    """
    conn.execute("BEGIN")
    try:
        cur.execute(f"INSERT INTO orders_new SELECT * FROM ({select_sql})")
        cur.execute("DROP TABLE orders")
        cur.execute("ALTER TABLE orders_new RENAME TO orders")
        conn.commit()
    except Exception:
        conn.rollback()
        raise

def reset_all() -> None:
    # Só se DEBUG=1
    if not (os.getenv("DEBUG") in ("1", "true", "True")):
        raise PermissionError("reset requires DEBUG=1")
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM orders")
        cur.execute("DELETE FROM positions")
        cur.execute(
            "UPDATE portfolio SET cash=?, realized_pnl=0.0 WHERE id=1",
            (STARTING_CASH,),
        )

# ----------------------------
# Pricing via o próprio /dataset
# ----------------------------

def _last_close(symbol: str, tf: str) -> Optional[float]:
    try:
        url = f"{INTERNAL_BASE_URL}/dataset/?symbol={symbol}&tf={tf}&columns=time,close&limit=1&dropna=true"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        rows = data.get("rows") or []
        if not rows:
            return None
        return float(rows[-1]["close"])
    except Exception:
        return None

def get_last_price(symbol: str) -> Tuple[Optional[float], Optional[str]]:
    price = _last_close(symbol, "1h")
    if price is not None:
        return price, "1h"
    price = _last_close(symbol, "1d")
    if price is not None:
        return price, "1d"
    return None, None

# ----------------------------
# Portfolio helpers
# ----------------------------

def _get_portfolio(conn: sqlite3.Connection) -> sqlite3.Row:
    return conn.execute("SELECT * FROM portfolio WHERE id=1").fetchone()

def _update_cash_and_realized(conn: sqlite3.Connection, side: str, qty: float, exec_price: float, realized: float) -> None:
    cur = conn.cursor()
    p = _get_portfolio(conn)
    cash = float(p["cash"])
    if side == "buy":
        cash -= qty * exec_price
    else:
        cash += qty * exec_price
    realized_total = float(p["realized_pnl"]) + float(realized)
    cur.execute("UPDATE portfolio SET cash=?, realized_pnl=? WHERE id=1", (cash, realized_total))

# ----------------------------
# Positions
# ----------------------------

def _load_position(conn: sqlite3.Connection, symbol: str) -> Optional[sqlite3.Row]:
    cur = conn.cursor()
    return cur.execute(
        "SELECT symbol, qty, avg_price FROM positions WHERE symbol=?",
        (symbol,),
    ).fetchone()

def _save_position(conn: sqlite3.Connection, symbol: str, qty: float, avg_price: float) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO positions(symbol, qty, avg_price)
        VALUES(?,?,?)
        ON CONFLICT(symbol) DO UPDATE SET
          qty=excluded.qty,
          avg_price=excluded.avg_price
        """,
        (symbol, qty, avg_price),
    )

def list_positions(mark_to_market: bool = False) -> Dict[str, Any]:
    with _conn() as conn:
        cur = conn.cursor()
        rows = cur.execute("SELECT symbol, qty, avg_price FROM positions ORDER BY symbol").fetchall()

    positions = []
    total_unreal = 0.0
    for r in rows:
        item = {"symbol": r["symbol"], "qty": float(r["qty"]), "avg_price": float(r["avg_price"])}
        if mark_to_market:
            last, tf = get_last_price(r["symbol"])
            if last is not None:
                item["last_price"] = last
                item["mark_tf"] = tf
                unreal = (last - item["avg_price"]) * item["qty"]
                item["unrealized_pnl"] = unreal
                total_unreal += unreal
        positions.append(item)

    if mark_to_market:
        return {"positions": positions, "unrealized_pnl_total": total_unreal}
    return {"positions": positions}

# ----------------------------
# Orders core
# ----------------------------

def _insert_order(conn: sqlite3.Connection, order: Dict[str, Any]) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders(ts, symbol, side, qty, type, status, price, limit_price, stop_price, value, filled_qty, exchange, realized_pnl)
        VALUES(:ts, :symbol, :side, :qty, :type, :status, :price, :limit_price, :stop_price, :value, :filled_qty, :exchange, :realized_pnl)
        """,
        order,
    )
    return cur.lastrowid

def _fill_position_math(pos: Optional[sqlite3.Row], side: str, qty: float, price: float) -> Tuple[float, float, float]:
    """
    Retorna: new_qty, new_avg, realized_pnl_delta
    """
    if pos is None:
        if side == "buy":
            return qty, price, 0.0
        return -qty, price, 0.0  # permite short em paper

    cur_qty = float(pos["qty"])
    cur_avg = float(pos["avg_price"])

    if side == "buy":
        if cur_qty >= 0:
            new_qty = cur_qty + qty
            new_avg = (cur_avg * cur_qty + price * qty) / new_qty
            return new_qty, new_avg, 0.0
        else:
            realize = min(qty, -cur_qty)
            realized_pnl = (cur_avg - price) * realize  # short lucra se preço cai
            new_qty = cur_qty + qty
            new_avg = cur_avg if new_qty != 0 else cur_avg
            return new_qty, new_avg, realized_pnl
    else:
        if cur_qty <= 0:
            new_qty = cur_qty - qty
            new_avg = (cur_avg * (-cur_qty) + price * qty) / (-new_qty) if new_qty < 0 else price
            return new_qty, new_avg, 0.0
        else:
            realize = min(qty, cur_qty)
            realized_pnl = (price - cur_avg) * realize
            new_qty = cur_qty - qty
            new_avg = cur_avg if new_qty != 0 else cur_avg
            return new_qty, new_avg, realized_pnl

def _apply_fill(conn: sqlite3.Connection, order_id: int, exec_price: float) -> float:
    cur = conn.cursor()
    o = cur.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not o or o["status"] != "open":
        return 0.0

    pos = _load_position(conn, o["symbol"])
    qty = float(o["qty"])
    side = o["side"]
    new_qty, new_avg, realized = _fill_position_math(pos, side, qty, exec_price)
    _save_position(conn, o["symbol"], new_qty, new_avg)

    value = qty * exec_price
    cur.execute(
        "UPDATE orders SET status='filled', price=?, value=?, filled_qty=qty, realized_pnl=? WHERE id=?",
        (exec_price, value, realized, order_id),
    )

    _update_cash_and_realized(conn, side, qty, exec_price, realized)
    return realized

def _should_fill_now(side: str, otype: str, last: float, limit_price: Optional[float], stop_price: Optional[float]) -> bool:
    if otype == "limit":
        if side == "buy":
            return last <= float(limit_price)
        return last >= float(limit_price)
    if otype == "stop":
        if side == "buy":
            return last >= float(stop_price)
        return last <= float(stop_price)
    return True  # market

def place_order(
    *,
    symbol: str,
    exchange: Optional[str],
    side: str,
    qty: float,
    otype: str = "market",
    price: Optional[float] = None,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> Dict[str, Any]:
    ts = int(time.time())
    with _conn() as conn:
        if otype == "market":
            # Preço de execução antes de inserir
            exec_price = price
            priced_from_tf = None
            if exec_price is None:
                exec_price, priced_from_tf = get_last_price(symbol)
                if exec_price is None:
                    raise ValueError("no market price")

            # Atualiza posição
            pos = _load_position(conn, symbol)
            new_qty, new_avg, realized = _fill_position_math(pos, side, float(qty), float(exec_price))
            _save_position(conn, symbol, new_qty, new_avg)

            # Atualiza caixa/realized
            _update_cash_and_realized(conn, side, float(qty), float(exec_price), float(realized))

            order = {
                "ts": ts,
                "symbol": symbol,
                "side": side,
                "qty": float(qty),
                "type": "market",
                "status": "filled",
                "price": float(exec_price),
                "limit_price": None,
                "stop_price": None,
                "value": float(qty) * float(exec_price),
                "filled_qty": float(qty),
                "exchange": exchange,
                "realized_pnl": float(realized),
            }
            oid = _insert_order(conn, order)
            o = get_order_by_id(oid)
            resp = {"order": o, "position": get_position(symbol), "realized_pnl": realized}
            if priced_from_tf:
                resp["priced_from_tf"] = priced_from_tf
            return resp

        # LIMIT / STOP -> open, possível fill imediato se já cruzou
        order = {
            "ts": ts,
            "symbol": symbol,
            "side": side,
            "qty": float(qty),
            "type": otype,
            "status": "open",
            "price": None,
            "limit_price": float(limit_price) if limit_price is not None else (float(price) if otype == "limit" and price is not None else None),
            "stop_price": float(stop_price) if stop_price is not None else (float(price) if otype == "stop" and price is not None else None),
            "value": None,
            "filled_qty": 0.0,
            "exchange": exchange,
            "realized_pnl": None,
        }

        if otype == "limit" and order["limit_price"] is None:
            raise ValueError("limit order requires limit_price")
        if otype == "stop" and order["stop_price"] is None:
            raise ValueError("stop order requires stop_price")

        oid = _insert_order(conn, order)

        last, _tf = get_last_price(symbol)
        if last is not None and _should_fill_now(side, otype, float(last), order["limit_price"], order["stop_price"]):
            _apply_fill(conn, oid, float(last))

        o = get_order_by_id(oid)
        return {"order": o, "position": get_position(symbol), "realized_pnl": 0.0}

def trigger_open_orders() -> Dict[str, Any]:
    filled: List[int] = []
    with _conn() as conn:
        cur = conn.cursor()
        open_orders = cur.execute("SELECT * FROM orders WHERE status='open' ORDER BY id").fetchall()
        by_symbol: Dict[str, List[sqlite3.Row]] = {}
        for o in open_orders:
            by_symbol.setdefault(o["symbol"], []).append(o)

        for sym, items in by_symbol.items():
            last, _tf = get_last_price(sym)
            if last is None:
                continue
            for o in items:
                if _should_fill_now(o["side"], o["type"], float(last), o["limit_price"], o["stop_price"]):
                    _apply_fill(conn, int(o["id"]), float(last))
                    filled.append(int(o["id"]))

    return {"filled": filled, "count": len(filled)}

def cancel_order(order_id: int) -> Dict[str, Any]:
    with _conn() as conn:
        cur = conn.cursor()
        o = cur.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not o:
            return {"ok": False, "reason": "not-found"}
        if o["status"] != "open":
            return {"ok": False, "reason": "not-open"}
        cur.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
        return {"ok": True}

def list_orders(status: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    with _conn() as conn:
        cur = conn.cursor()
        if status:
            rows = cur.execute(
                "SELECT * FROM orders WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, int(limit)),
            ).fetchall()
        else:
            rows = cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
    return {"orders": [_row_to_dict(r) for r in rows]}

def get_order_by_id(order_id: int) -> Dict[str, Any]:
    with _conn() as conn:
        cur = conn.cursor()
        r = cur.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not r:
            raise KeyError("order not found")
        return _row_to_dict(r)

def get_position(symbol: str) -> Optional[Dict[str, Any]]:
    with _conn() as conn:
        r = _load_position(conn, symbol)
        if r is None:
            return None
        return {"symbol": r["symbol"], "qty": float(r["qty"]), "avg_price": float(r["avg_price"])}

def _row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": int(r["id"]),
        "ts": int(r["ts"]),
        "symbol": r["symbol"],
        "side": r["side"],
        "qty": float(r["qty"]),
        "type": r["type"],
        "status": r["status"],
        "price": None if r["price"] is None else float(r["price"]),
        "limit_price": None if r["limit_price"] is None else float(r["limit_price"]),
        "stop_price": None if r["stop_price"] is None else float(r["stop_price"]),
        "value": None if r["value"] is None else float(r["value"]),
        "filled_qty": float(r["filled_qty"]),
        "exchange": r["exchange"],
        "realized_pnl": None if r["realized_pnl"] is None else float(r["realized_pnl"]),
    }

# ----------------------------
# Portfolio view
# ----------------------------

def portfolio(mark_to_market: bool = True) -> Dict[str, Any]:
    with _conn() as conn:
        p = _get_portfolio(conn)
        cash = float(p["cash"])
        starting_cash = float(p["starting_cash"])
        realized_total = float(p["realized_pnl"])

    if mark_to_market:
        pos = list_positions(mark_to_market=True)
        positions = pos["positions"]
        positions_value = sum((it.get("last_price", it["avg_price"])) * it["qty"] for it in positions)
        unreal_total = float(pos.get("unrealized_pnl_total", 0.0))
    else:
        lp = list_positions(mark_to_market=False)
        positions = lp["positions"]
        positions_value = sum(it["avg_price"] * it["qty"] for it in positions)
        unreal_total = 0.0

    equity = cash + positions_value
    return {
        "starting_cash": starting_cash,
        "cash": cash,
        "equity": equity,
        "positions_value": positions_value,
        "realized_pnl_total": realized_total,
        "unrealized_pnl_total": unreal_total,
        "positions": positions,
        "mark_to_market": mark_to_market,
    }
