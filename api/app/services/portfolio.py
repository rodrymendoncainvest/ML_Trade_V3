import os
import sqlite3
import time
import json
from typing import Dict, Any, List, Tuple, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# --- Config -----------------------------------------------------------------

DB_PATH = os.getenv("PAPER_DB_PATH", "/app/data/paper.db")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
STARTING_CASH = float(os.getenv("PAPER_STARTING_CASH", "0"))  # por default 0


# --- Helpers ----------------------------------------------------------------

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now_ts() -> int:
    return int(time.time())


def _ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    # tabela de posições (já deve existir, mas garantimos)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS positions(
            symbol TEXT PRIMARY KEY,
            qty REAL NOT NULL,
            avg_price REAL NOT NULL
        )
    """)
    # tabela de ordens (já existe; criamos só se faltar num ambiente limpo)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            exchange TEXT,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            type TEXT DEFAULT 'market',
            status TEXT NOT NULL,
            price REAL,
            limit_price REAL,
            stop_price REAL,
            value REAL,
            filled_qty REAL DEFAULT 0
        )
    """)
    # ledger de caixa (depósitos/levantamentos)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cash_ledger(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            kind TEXT NOT NULL,     -- 'deposit' | 'withdraw'
            amount REAL NOT NULL,
            note TEXT
        )
    """)
    conn.commit()


def _http_get_json(url: str) -> Any:
    try:
        with urlopen(url, timeout=8) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except HTTPError as e:
        raise RuntimeError(f"http {e.code} for {url}")
    except URLError as e:
        raise RuntimeError(f"http error for {url}: {e.reason}")


def _last_price(symbol: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Tenta 1h, depois 1d. Devolve (preco, tf_usada) ou (None, None) se não houver.
    Usa o nosso endpoint /dataset.
    """
    for tf in ("1h", "1d"):
        url = f"{BASE_URL}/dataset/?symbol={symbol}&tf={tf}&columns=time,close&limit=1"
        try:
            data = _http_get_json(url)
            rows = data.get("rows") or []
            if rows:
                return float(rows[-1]["close"]), tf
        except Exception:
            continue
    return None, None


# --- Leitura de dados -------------------------------------------------------

def list_positions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    res = cur.execute("SELECT symbol, qty, avg_price FROM positions WHERE ABS(qty) > 1e-12").fetchall()
    return [dict(r) for r in res]


def list_filled_orders(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    cur = conn.cursor()
    res = cur.execute("""
        SELECT id, ts, symbol, side, qty, price, value
        FROM orders
        WHERE status='filled'
        ORDER BY ts ASC, id ASC
    """).fetchall()
    return res


# --- Cálculos de PnL --------------------------------------------------------

def compute_realized_pnl_from_orders(conn: sqlite3.Connection) -> float:
    """
    Reconstrói o PnL realizado percorrendo ordens 'filled' por símbolo.
    Long-only (short está bloqueado pelo teu risk engine).
    """
    cur = conn.cursor()
    syms = cur.execute("SELECT DISTINCT symbol FROM orders WHERE status='filled'").fetchall()
    total = 0.0

    for row in syms:
        sym = row["symbol"]
        # posição virtual para reconstrução
        v_qty = 0.0
        v_avg = 0.0
        for o in cur.execute("""
            SELECT ts, id, side, qty, price
            FROM orders
            WHERE status='filled' AND symbol=?
            ORDER BY ts ASC, id ASC
        """, (sym,)):
            qty = float(o["qty"])
            price = float(o["price"])
            side = o["side"]
            if side == "buy":
                new_qty = v_qty + qty
                v_avg = (v_avg * v_qty + price * qty) / new_qty if new_qty else 0.0
                v_qty = new_qty
            else:  # sell
                close_qty = min(qty, v_qty)
                total += close_qty * (price - v_avg)
                v_qty -= close_qty
                # v_avg mantém-se para o remanescente
    return total


def mark_to_market(conn: sqlite3.Connection) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Calcula MTM por posição com última cotação (1h→1d).
    Retorna (unrealized_total, positions_com_mtm)
    """
    pos = list_positions(conn)
    unreal_total = 0.0
    out = []
    for p in pos:
        sym = p["symbol"]
        qty = float(p["qty"])
        avg = float(p["avg_price"])
        last, used_tf = _last_price(sym)
        if last is None:
            last = avg  # fallback neutro
            used_tf = None
            unreal = 0.0
        else:
            unreal = qty * (last - avg)
        unreal_total += unreal
        row = dict(p)
        row.update({"last_price": last, "mark_tf": used_tf, "unrealized_pnl": unreal})
        out.append(row)
    return unreal_total, out


# --- Caixa / Portfolio ------------------------------------------------------

def cash_balance(conn: sqlite3.Connection) -> float:
    _ensure_schema(conn)
    cur = conn.cursor()
    s = cur.execute("SELECT COALESCE(SUM(amount),0) as s FROM cash_ledger").fetchone()["s"]
    return float(STARTING_CASH + (s or 0.0))


def deposit(conn: sqlite3.Connection, amount: float, note: Optional[str] = None) -> float:
    if amount <= 0:
        raise ValueError("amount deve ser > 0")
    _ensure_schema(conn)
    cur = conn.cursor()
    cur.execute("INSERT INTO cash_ledger(ts, kind, amount, note) VALUES(?,?,?,?)",
                (_now_ts(), "deposit", float(amount), note))
    conn.commit()
    return cash_balance(conn)


def withdraw(conn: sqlite3.Connection, amount: float, note: Optional[str] = None) -> float:
    if amount <= 0:
        raise ValueError("amount deve ser > 0")
    _ensure_schema(conn)
    bal = cash_balance(conn)
    if amount > bal + 1e-9:
        raise RuntimeError(f"saldo insuficiente: {bal:.2f}")
    cur = conn.cursor()
    cur.execute("INSERT INTO cash_ledger(ts, kind, amount, note) VALUES(?,?,?,?)",
                (_now_ts(), "withdraw", -float(amount), note))
    conn.commit()
    return cash_balance(conn)


def build_portfolio(conn: sqlite3.Connection) -> Dict[str, Any]:
    _ensure_schema(conn)
    cash = cash_balance(conn)
    realized = compute_realized_pnl_from_orders(conn)
    unreal, pos_mtm = mark_to_market(conn)
    market_value = sum((p["last_price"] or 0.0) * float(p["qty"]) for p in pos_mtm)
    equity = cash + market_value
    return {
        "cash": cash,
        "market_value": market_value,
        "equity": equity,
        "realized_pnl": realized,
        "unrealized_pnl": unreal,
        "positions": pos_mtm,
    }


# --- Flatten helpers (via o endpoint existente de orders) -------------------

def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def flat_symbol(symbol: str, exchange: Optional[str] = None) -> Dict[str, Any]:
    """
    Usa o endpoint atual /paper/orders para fechar a posição a mercado (sem reinventar pricing).
    """
    with _conn() as conn:
        _ensure_schema(conn)
        cur = conn.cursor()
        row = cur.execute("SELECT qty FROM positions WHERE symbol=?", (symbol,)).fetchone()
        if not row:
            return {"symbol": symbol, "closed": False, "reason": "sem posição"}
        qty = float(row["qty"])
        if abs(qty) < 1e-12:
            return {"symbol": symbol, "closed": False, "reason": "qty=0"}
    side = "sell" if qty > 0 else "buy"
    body = {"symbol": symbol, "side": side, "qty": abs(qty)}
    if exchange:
        body["exchange"] = exchange
    url = f"{BASE_URL}/paper/orders"
    return _post_json(url, body)


def flat_all() -> Dict[str, Any]:
    with _conn() as conn:
        positions = list_positions(conn)
    results = []
    for p in positions:
        res = flat_symbol(p["symbol"])
        results.append({"symbol": p["symbol"], "result": res})
    return {"count": len(results), "results": results}
