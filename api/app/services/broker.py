# api/app/services/broker.py
import os
import sqlite3
import time
import uuid
import json
from typing import Optional, Dict, Any, List, Tuple
from urllib import request, parse

# --- Config ---
DB_PATH = os.environ.get("BROKER_DB_PATH", "/data/paper.db")
DEFAULT_BASEURL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
DEFAULT_PROVIDER = os.environ.get("DEFAULT_PROVIDER", "yahoo")
DEFAULT_TF = os.environ.get("BROKER_DEFAULT_TF", "1h")
DEFAULT_CASH = float(os.environ.get("BROKER_STARTING_CASH", "100000"))


def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _now_ts() -> int:
    return int(time.time())


def _gen_id() -> str:
    return uuid.uuid4().hex[:12]


def _http_get_json(url: str) -> Dict[str, Any]:
    with request.urlopen(url, timeout=10) as resp:
        data = resp.read()
        return json.loads(data.decode("utf-8"))


def _fetch_last_bar(symbol: str, tf: str = DEFAULT_TF) -> Optional[Dict[str, Any]]:
    """
    Pede ao endpoint /dataset a última barra (time, open, high, low, close).
    Se não houver dados, devolve None.
    """
    qs = parse.urlencode({
        "symbol": symbol,
        "tf": tf,
        "columns": "time,open,high,low,close",
        "limit": 1,
        "dropna": "true"
    })
    url = f"{DEFAULT_BASEURL}/dataset/?{qs}"
    data = _http_get_json(url)
    rows = data.get("rows") or []
    if not rows:
        return None
    # os campos vêm como dict com ints/floats
    return rows[-1]


def _resolve_symbol(symbol: str, exchange: Optional[str], provider: str = DEFAULT_PROVIDER) -> str:
    """
    Tenta resolver via serviço interno; se falhar, devolve o original.
    """
    try:
        # evita import circular: importa aqui
        from app.services.symbols import resolve_symbol as _svc_resolve
        resolved = _svc_resolve(symbol=symbol, exchange=exchange, provider=provider)
        return resolved or symbol
    except Exception:
        # fallback via HTTP (não crítico) — se falhar, usa original
        try:
            qs = parse.urlencode({"symbol": symbol, "exchange": exchange or "", "provider": provider})
            data = _http_get_json(f"{DEFAULT_BASEURL}/symbols/resolve?{qs}")
            return data.get("resolved") or symbol
        except Exception:
            return symbol


class BrokerService:
    def __init__(self, db_path: str = DB_PATH):
        _ensure_dir(db_path)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    # ---------- schema ----------
    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts(
            id INTEGER PRIMARY KEY CHECK (id=1),
            cash REAL NOT NULL,
            created_at INTEGER NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL CHECK (side IN ('buy','sell')),
            qty REAL NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('market','limit')),
            limit_price REAL,
            status TEXT NOT NULL CHECK (status IN ('open','filled','canceled','rejected')),
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS fills(
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            qty REAL NOT NULL,
            time INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS positions(
            symbol TEXT PRIMARY KEY,
            qty REAL NOT NULL,
            avg_price REAL NOT NULL
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS ledger(
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL, -- 'trade'
            amount REAL NOT NULL,
            time INTEGER NOT NULL,
            ref TEXT
        )""")
        self.conn.commit()
        self._ensure_account()

    def _ensure_account(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM accounts WHERE id=1")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO accounts(id,cash,created_at) VALUES(1, ?, ?)", (DEFAULT_CASH, _now_ts()))
            self.conn.commit()

    # ---------- helpers ----------
    def _get_cash(self) -> float:
        cur = self.conn.cursor()
        cur.execute("SELECT cash FROM accounts WHERE id=1")
        v = cur.fetchone()
        return float(v[0]) if v else DEFAULT_CASH

    def _set_cash(self, value: float):
        cur = self.conn.cursor()
        cur.execute("UPDATE accounts SET cash=? WHERE id=1", (float(value),))
        self.conn.commit()

    def _update_position(self, symbol: str, delta_qty: float, fill_price: float):
        cur = self.conn.cursor()
        cur.execute("SELECT qty, avg_price FROM positions WHERE symbol=?", (symbol,))
        row = cur.fetchone()
        if row is None:
            if delta_qty < 0:
                raise ValueError("sell without position")
            cur.execute("INSERT INTO positions(symbol,qty,avg_price) VALUES(?,?,?)",
                        (symbol, delta_qty, fill_price))
        else:
            qty, avg = float(row[0]), float(row[1])
            new_qty = qty + delta_qty
            if new_qty < -1e-9:
                raise ValueError("resulting negative position not allowed")
            if new_qty < 1e-9:
                # flat — remove posição
                cur.execute("DELETE FROM positions WHERE symbol=?", (symbol,))
            else:
                if delta_qty > 0:
                    new_avg = (qty * avg + delta_qty * fill_price) / new_qty
                else:
                    new_avg = avg  # vender não altera avg do restante
                cur.execute("UPDATE positions SET qty=?, avg_price=? WHERE symbol=?", (new_qty, new_avg, symbol))
        self.conn.commit()

    def _add_fill_and_ledger(self, order_id: str, symbol: str, price: float, qty: float, ts: int):
        fill_id = _gen_id()
        cur = self.conn.cursor()
        cur.execute("INSERT INTO fills(id,order_id,symbol,price,qty,time) VALUES(?,?,?,?,?,?)",
                    (fill_id, order_id, symbol, price, qty, ts))
        # ledger: cash sai na compra, entra na venda
        amount = -price * qty
        cur.execute("INSERT INTO ledger(id,kind,amount,time,ref) VALUES(?,?,?,?,?)",
                    (_gen_id(), "trade", amount, ts, order_id))
        self.conn.commit()
        # ajustar cash
        self._set_cash(self._get_cash() + amount)

    def _mark_order(self, order_id: str, status: str):
        cur = self.conn.cursor()
        cur.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (status, _now_ts(), order_id))
        self.conn.commit()

    # ---------- public API ----------
    def place_order(self, *, symbol: str, exchange: Optional[str], side: str,
                    qty: float, type_: str, limit_price: Optional[float], tf: str = DEFAULT_TF) -> Dict[str, Any]:
        resolved = _resolve_symbol(symbol, exchange, DEFAULT_PROVIDER)
        oid = _gen_id()
        ts = _now_ts()
        cur = self.conn.cursor()
        cur.execute("""INSERT INTO orders(id,symbol,side,qty,type,limit_price,status,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?, ?, ?)""",
                    (oid, resolved, side, float(qty), type_, float(limit_price) if limit_price else None,
                     "open", ts, ts))
        self.conn.commit()

        # tentar preencher no momento
        bar = _fetch_last_bar(resolved, tf=tf)
        if bar is None:
            # fica open (sem dados)
            return self.get_order(oid)

        high = float(bar["high"])
        low = float(bar["low"])
        close = float(bar["close"])
        fillable = False
        fill_price = close

        if type_ == "market":
            fillable = True
            fill_price = close
        elif type_ == "limit":
            if limit_price is None:
                raise ValueError("limit order without price")
            lp = float(limit_price)
            if side == "buy":
                # compra preenche se o low tocou o limite
                fillable = (low <= lp)
                fill_price = lp
            else:
                # venda preenche se o high tocou o limite
                fillable = (high >= lp)
                fill_price = lp
        else:
            raise ValueError("unknown order type")

        if not fillable:
            return self.get_order(oid)  # fica 'open'

        # validar posição/cash simples (long-only)
        cash = self._get_cash()
        if side == "buy":
            cost = fill_price * qty
            if cash + 1e-9 < cost:
                self._mark_order(oid, "rejected")
                raise ValueError("insufficient cash")
            self._update_position(resolved, delta_qty=qty, fill_price=fill_price)
            self._add_fill_and_ledger(oid, resolved, fill_price, qty, ts)
        else:
            # sell
            cur.execute("SELECT qty FROM positions WHERE symbol=?", (resolved,))
            row = cur.fetchone()
            have = float(row[0]) if row else 0.0
            if qty > have + 1e-9:
                self._mark_order(oid, "rejected")
                raise ValueError("insufficient position")
            self._update_position(resolved, delta_qty=-qty, fill_price=fill_price)
            # venda entra cash (amount negativo na ledger é compra; aqui é positivo)
            # _add_fill_and_ledger usa amount=-price*qty; para venda queremos +price*qty.
            # então lançamos com qty negativo para inverter o sinal na ledger.
            self._add_fill_and_ledger(oid, resolved, fill_price, -qty, ts)

        self._mark_order(oid, "filled")
        return self.get_order(oid)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT status FROM orders WHERE id=?", (order_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("order not found")
        if row[0] != "open":
            return self.get_order(order_id)
        self._mark_order(order_id, "canceled")
        return self.get_order(order_id)

    def list_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""SELECT id,symbol,side,qty,type,limit_price,status,created_at,updated_at
                       FROM orders ORDER BY created_at DESC LIMIT ?""", (int(limit),))
        rows = cur.fetchall()
        return [self._order_row_to_dict(r) for r in rows]

    def get_order(self, order_id: str) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("""SELECT id,symbol,side,qty,type,limit_price,status,created_at,updated_at
                       FROM orders WHERE id=?""", (order_id,))
        r = cur.fetchone()
        if not r:
            raise ValueError("order not found")
        return self._order_row_to_dict(r)

    def get_positions(self) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT symbol, qty, avg_price FROM positions ORDER BY symbol")
        rows = cur.fetchall()
        positions = [{"symbol": r[0], "qty": float(r[1]), "avg_price": float(r[2])} for r in rows]
        return {"positions": positions}

    def get_account(self) -> Dict[str, Any]:
        # equity = cash + soma( qty * last_close )
        cash = self._get_cash()
        cur = self.conn.cursor()
        cur.execute("SELECT symbol, qty FROM positions")
        rows = cur.fetchall()
        equity = cash
        quotes = []
        for sym, qty in rows:
            bar = _fetch_last_bar(sym, tf=DEFAULT_TF)
            px = float(bar["close"]) if bar else 0.0
            equity += float(qty) * px
            quotes.append({"symbol": sym, "price": px})
        return {"cash": cash, "equity": equity, "quotes": quotes}

    @staticmethod
    def _order_row_to_dict(r: Tuple[Any, ...]) -> Dict[str, Any]:
        return {
            "id": r[0],
            "symbol": r[1],
            "side": r[2],
            "qty": float(r[3]),
            "type": r[4],
            "limit_price": float(r[5]) if r[5] is not None else None,
            "status": r[6],
            "created_at": int(r[7]),
            "updated_at": int(r[8]),
        }


# singleton simples
_broker_singleton: Optional[BrokerService] = None


def get_broker() -> BrokerService:
    global _broker_singleton
    if _broker_singleton is None:
        _broker_singleton = BrokerService(DB_PATH)
    return _broker_singleton
