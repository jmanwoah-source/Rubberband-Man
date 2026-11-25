"""
Simulated Diary & Daily Top-5 Recommendation Database (SQLite WAL Mode)
Provides persistent storage and institutional ledger tracking for:
1. Simulated Options Trades & Paper Diary (Charles Schwab Order Ticket format)
2. Daily Top-5 Sector Recommendation Snapshots & Automated Performance Auditing
3. 24/7 Workstation Daemon Handoff for ASUS GX10
"""

import os
import re
import json
import uuid
import sqlite3
import datetime
import threading
from contextlib import contextmanager
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional, Iterator

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "simulated_diary.db")

_INIT_LOCK = threading.Lock()
_DB_INITIALIZED_PATH: Optional[str] = None
_SCHEMA_VERSION = 2

_SYNC_LABELS = {
    0: "OFF",
    1: "NORMAL",
    2: "FULL",
    3: "EXTRA",
}


def _ny_today() -> datetime.date:
    try:
        return datetime.datetime.now(ZoneInfo("America/New_York")).date()
    except Exception:
        return datetime.date.today()


def _ny_now() -> datetime.datetime:
    try:
        return datetime.datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.datetime.now()


def _backup_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "backups")


def _is_vertical_spread(strategy: Any, strike: Any, short_strike: Any) -> bool:
    """Shared vertical-spread predicate used consistently on open, close, and portfolio valuation."""
    if short_strike is None:
        return False
    strat_u = str(strategy or "").strip().upper()
    if "SPREAD" not in strat_u:
        return False
    try:
        return abs(float(short_strike) - float(strike)) > 0.01
    except (TypeError, ValueError):
        return False


def _normalize_sector_safe(sector_name: str) -> str:
    """Normalizes legacy sector names via rbe3.normalize_sector_name with a safe fallback."""
    raw = str(sector_name or "").strip()
    if not raw:
        return "Semiconductors"
    try:
        import rubberband_engine_v3 as rbe3

        if hasattr(rbe3, "normalize_sector_name"):
            return rbe3.normalize_sector_name(raw)
    except Exception:
        pass
    legacy_map = {
        "Energy & Material Science": "Energy, Grid & Materials",
        "Nuclear & Next-Gen Energy": "Energy, Grid & Materials",
        "Nuclear Energy": "Energy, Grid & Materials",
        "Robotics & Automation": "Robotics & Autonomous",
        "Robotics": "Robotics & Autonomous",
        "Edge AI": "Edge AI & Next-Gen Compute",
    }
    return legacy_map.get(raw, raw)


def _format_trade_row(row_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures backwards-compatible aliases and defaults on every returned trade dict."""
    out = dict(row_dict)
    limit_px = float(out.get("limit_price") or 0.0)
    out["limit_price"] = limit_px
    out["entry_premium"] = limit_px
    out["time_in_force"] = str(out.get("time_in_force") or "DAY").upper()
    out["exit_commission_fee"] = float(out.get("exit_commission_fee") or 0.0)
    return out


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Yields a SQLite connection configured for full-durability WAL mode and always closes it."""
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA synchronous=FULL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA wal_autocheckpoint=100;")
        conn.execute("PRAGMA busy_timeout=30000;")
        yield conn
        if conn.in_transaction:
            conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


_get_connection = _connect


def init_diary_db() -> None:
    """Initializes database schema with WAL mode, migrations, and indices once per process/DB_PATH."""
    global _DB_INITIALIZED_PATH
    if _DB_INITIALIZED_PATH == DB_PATH and os.path.exists(DB_PATH):
        return
    with _INIT_LOCK:
        if _DB_INITIALIZED_PATH == DB_PATH and os.path.exists(DB_PATH):
            return
        with _connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            # Table 1: Simulated Options Trades & Practice Diary (Schwab Order Format)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS simulated_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schwab_order_id TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                strategy TEXT DEFAULT 'SINGLE_LEG',
                action TEXT NOT NULL,
                option_type TEXT NOT NULL,
                strike REAL NOT NULL,
                short_strike REAL,
                expiration_date TEXT NOT NULL,
                dte_at_entry INTEGER DEFAULT 35,
                order_type TEXT DEFAULT 'LIMIT',
                time_in_force TEXT DEFAULT 'DAY',
                quantity INTEGER NOT NULL DEFAULT 1,
                limit_price REAL NOT NULL,
                stock_price_at_entry REAL NOT NULL,
                total_cost REAL NOT NULL,
                commission_fee REAL DEFAULT 0.65,
                exit_commission_fee REAL DEFAULT 0.0,
                target_stock_price REAL,
                stop_stock_price REAL,
                target_premium REAL,
                stop_premium REAL,
                entry_timestamp TEXT NOT NULL,
                exit_timestamp TEXT,
                exit_premium REAL,
                exit_stock_price REAL,
                status TEXT DEFAULT 'OPEN',
                realized_pnl_dollar REAL DEFAULT 0.0,
                realized_pnl_pct REAL DEFAULT 0.0,
                conviction_score REAL DEFAULT 50.0,
                expected_basis_pct REAL DEFAULT 0.0,
                whale_badge TEXT DEFAULT '⚪ TWO-WAY FLOW',
                catalyst_tag TEXT,
                notes TEXT,
                implied_vol_at_entry REAL,
                deleted_at TEXT,
                created_at TEXT NOT NULL
            );
            """)

            # Table 2: Daily Top-5 Recommendation Snapshots
            conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,
                snapshot_time TEXT NOT NULL,
                sector TEXT NOT NULL,
                rank INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                company_name TEXT,
                action TEXT NOT NULL,
                composite_score REAL NOT NULL,
                price_at_snapshot REAL NOT NULL,
                vwma20_at_rec REAL,
                z_score_at_rec REAL,
                expected_basis_pct REAL,
                empirical_win_rate REAL,
                whale_badge TEXT,
                whale_score REAL,
                days_to_earnings INTEGER,
                earnings_date TEXT,
                recommended_strike REAL,
                target_price REAL,
                invalidation_price REAL,
                half_life REAL,
                raw_meta_json TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(snapshot_date, sector, rank)
            );
            """)

            # Idempotent schema migrations for existing databases
            cols = {r[1] for r in conn.execute("PRAGMA table_info(simulated_trades);").fetchall()}
            if "implied_vol_at_entry" not in cols:
                conn.execute("ALTER TABLE simulated_trades ADD COLUMN implied_vol_at_entry REAL;")
            if "short_strike" not in cols:
                conn.execute("ALTER TABLE simulated_trades ADD COLUMN short_strike REAL;")
            if "time_in_force" not in cols:
                conn.execute("ALTER TABLE simulated_trades ADD COLUMN time_in_force TEXT DEFAULT 'DAY';")
            if "exit_commission_fee" not in cols:
                conn.execute("ALTER TABLE simulated_trades ADD COLUMN exit_commission_fee REAL DEFAULT 0.0;")
            if "deleted_at" not in cols:
                conn.execute("ALTER TABLE simulated_trades ADD COLUMN deleted_at TEXT;")

            # Table 3: Daily OPRA ATM IV Snapshot Log (accumulates true IV percentile history)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS iv_history_log (
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                atm_iv REAL NOT NULL,
                PRIMARY KEY(symbol, trade_date)
            );
            """)

            # Performance Indices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON simulated_trades(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON simulated_trades(symbol);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recs_date_sec ON daily_recommendations(snapshot_date, sector);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recs_symbol ON daily_recommendations(symbol);")

            curr_ver = int(conn.execute("PRAGMA user_version;").fetchone()[0] or 0)
            if curr_ver < _SCHEMA_VERSION:
                conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION};")
        _DB_INITIALIZED_PATH = DB_PATH


# =========================================================================
# SECTION 1: SIMULATED OPTIONS TRADING & SCHWAB DIARY LEDGER
# =========================================================================

def generate_schwab_order_id(symbol: str) -> str:
    """Generates a unique Charles Schwab style order reference number."""
    now = _ny_now()
    rand_suffix = uuid.uuid4().hex[:6].upper()
    return f"SCHW-{symbol.upper()}-{now.strftime('%y%m%d')}-{rand_suffix}"


def create_simulated_trade(
    symbol: str,
    action: str,  # 'BUY_TO_OPEN', 'SELL_TO_OPEN'
    option_type: str,  # 'CALL', 'PUT'
    strike: float,
    expiration_date: str,
    quantity: int,
    limit_price: float,
    stock_price_at_entry: float,
    strategy: str = "SINGLE_LEG",
    order_type: str = "LIMIT",
    target_stock_price: Optional[float] = None,
    stop_stock_price: Optional[float] = None,
    target_premium: Optional[float] = None,
    stop_premium: Optional[float] = None,
    conviction_score: float = 50.0,
    expected_basis_pct: float = 0.0,
    whale_badge: str = "⚪ TWO-WAY FLOW",
    catalyst_tag: str = "",
    notes: str = "",
    dte: Optional[int] = None,
    short_strike: Optional[float] = None,
    implied_vol_at_entry: Optional[float] = None,
    time_in_force: str = "DAY",
) -> Dict[str, Any]:
    """
    Creates a simulated options trade formatted according to Charles Schwab order conventions.
    Retries order-ID generation up to 3x on IntegrityError and returns the full inserted row dict.
    """
    init_diary_db()
    now_iso = _ny_now().isoformat()
    sym_u = str(symbol or "").strip().upper()
    tif_u = str(time_in_force or "DAY").strip().upper() or "DAY"

    # Standard Schwab options calculation: Limit Price * 100 * Qty + Schwab contract fee ($0.65/contract per leg)
    is_spread = _is_vertical_spread(strategy, strike, short_strike)
    leg_mult = 2 if is_spread else 1
    contract_fee = round(quantity * 0.65 * leg_mult, 2)
    action_u = str(action).upper()
    if "SELL" in action_u:
        # Credit received (net of entry contract fee)
        total_cost = round(max(0.0, (quantity * limit_price * 100.0) - contract_fee), 2)
    else:
        total_cost = round((quantity * limit_price * 100.0) + contract_fee, 2)

    # Compute Days to Expiration (DTE)
    if dte is not None and int(dte) > 0:
        dte = int(dte)
    else:
        dte = 35
        try:
            m_dte = re.search(r"\((\d+)\s*DTE", str(expiration_date))
            if m_dte:
                dte = max(1, int(m_dte.group(1)))
            else:
                clean_exp = str(expiration_date).split("(")[0].strip()
                try:
                    exp_dt = datetime.datetime.strptime(clean_exp, "%b %d, %Y").date()
                    dte = max(1, (exp_dt - _ny_today()).days)
                except Exception:
                    exp_dt = datetime.date.fromisoformat(clean_exp[:10])
                    dte = max(1, (exp_dt - _ny_today()).days)
        except Exception:
            dte = 35

    short_strike_val = float(short_strike) if short_strike is not None else None
    iv_entry_val = float(implied_vol_at_entry) if implied_vol_at_entry is not None else None

    with _connect() as conn:
        trade_id = None
        order_id = ""
        for attempt in range(3):
            order_id = generate_schwab_order_id(sym_u)
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO simulated_trades (
                        schwab_order_id, symbol, strategy, action, option_type, strike, short_strike, expiration_date,
                        dte_at_entry, order_type, time_in_force, quantity, limit_price, stock_price_at_entry, total_cost,
                        commission_fee, exit_commission_fee, target_stock_price, stop_stock_price, target_premium, stop_premium,
                        entry_timestamp, status, conviction_score, expected_basis_pct, whale_badge,
                        catalyst_tag, notes, implied_vol_at_entry, created_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?
                    );
                    """,
                    (
                        order_id, sym_u, strategy, action, option_type.upper(), float(strike),
                        short_strike_val, expiration_date, dte, order_type, tif_u, int(quantity),
                        float(limit_price), float(stock_price_at_entry), total_cost, contract_fee,
                        target_stock_price, stop_stock_price, target_premium, stop_premium,
                        now_iso, conviction_score, expected_basis_pct, whale_badge,
                        catalyst_tag, notes, iv_entry_val, now_iso,
                    ),
                )
                trade_id = cursor.lastrowid
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM simulated_trades WHERE id = ?;", (trade_id,)
                ).fetchone()
                if row is not None:
                    return _format_trade_row(dict(row))
                break
            except sqlite3.IntegrityError:
                if conn.in_transaction:
                    conn.rollback()
                if attempt == 2:
                    raise

    return _format_trade_row({
        "id": trade_id,
        "schwab_order_id": order_id,
        "symbol": sym_u,
        "strategy": strategy,
        "action": action,
        "option_type": option_type.upper(),
        "strike": float(strike),
        "short_strike": short_strike_val,
        "expiration_date": expiration_date,
        "dte_at_entry": dte,
        "order_type": order_type,
        "time_in_force": tif_u,
        "quantity": int(quantity),
        "limit_price": float(limit_price),
        "stock_price_at_entry": float(stock_price_at_entry),
        "total_cost": total_cost,
        "commission_fee": contract_fee,
        "exit_commission_fee": 0.0,
        "target_stock_price": target_stock_price,
        "stop_stock_price": stop_stock_price,
        "target_premium": target_premium,
        "stop_premium": stop_premium,
        "entry_timestamp": now_iso,
        "status": "OPEN",
        "conviction_score": conviction_score,
        "expected_basis_pct": expected_basis_pct,
        "whale_badge": whale_badge,
        "catalyst_tag": catalyst_tag,
        "notes": notes,
        "implied_vol_at_entry": iv_entry_val,
        "deleted_at": None,
        "created_at": now_iso,
    })


def get_open_trades() -> List[Dict[str, Any]]:
    """Retrieves all currently active open simulated trades."""
    init_diary_db()
    with _connect() as conn:
        rows = conn.execute("""
            SELECT * FROM simulated_trades
            WHERE status = 'OPEN'
            ORDER BY id DESC;
        """).fetchall()
        return [_format_trade_row(dict(r)) for r in rows]


def get_closed_trades(limit: Optional[int] = 200) -> List[Dict[str, Any]]:
    """Retrieves closed or expired simulated trades for historical auditing (limit=0/None returns all)."""
    init_diary_db()
    with _connect() as conn:
        if limit is None or int(limit) <= 0:
            rows = conn.execute("""
                SELECT * FROM simulated_trades
                WHERE status IN ('CLOSED', 'EXPIRED')
                ORDER BY exit_timestamp DESC, id DESC;
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM simulated_trades
                WHERE status IN ('CLOSED', 'EXPIRED')
                ORDER BY exit_timestamp DESC, id DESC
                LIMIT ?;
            """, (int(limit),)).fetchall()
        return [_format_trade_row(dict(r)) for r in rows]


def update_simulated_trade(
    trade_id: int,
    target_stock_price: Optional[float] = None,
    stop_stock_price: Optional[float] = None,
    notes: Optional[str] = None,
    time_in_force: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Atomically updates non-None fields on an OPEN simulated trade under BEGIN IMMEDIATE.
    Returns the updated trade row dict, or None if the trade is not found / not OPEN.
    """
    init_diary_db()
    assignments: List[str] = []
    params: List[Any] = []

    if target_stock_price is not None:
        assignments.append("target_stock_price = ?")
        params.append(float(target_stock_price))
    if stop_stock_price is not None:
        assignments.append("stop_stock_price = ?")
        params.append(float(stop_stock_price))
    if notes is not None:
        assignments.append("notes = ?")
        params.append(str(notes))
    if time_in_force is not None:
        assignments.append("time_in_force = ?")
        params.append(str(time_in_force).strip().upper() or "DAY")

    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE;")
        existing = conn.execute(
            "SELECT * FROM simulated_trades WHERE id = ? AND status = 'OPEN';",
            (trade_id,),
        ).fetchone()
        if not existing:
            conn.rollback()
            return None

        if assignments:
            params.append(trade_id)
            conn.execute(
                f"UPDATE simulated_trades SET {', '.join(assignments)} WHERE id = ? AND status = 'OPEN';",
                params,
            )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM simulated_trades WHERE id = ?;", (trade_id,)
        ).fetchone()
        return _format_trade_row(dict(updated)) if updated is not None else None


def close_simulated_trade(
    trade_id: int,
    exit_premium: float,
    exit_stock_price: float,
    exit_notes: str = "",
) -> bool:
    """
    Closes an open simulated trade atomically inside BEGIN IMMEDIATE,
    calculating realized P&L accurately for both BUY_TO_OPEN and SELL_TO_OPEN.
    Waives exit commission when exit_premium <= 0.0 (worthless expiration) and
    persists exit_commission_fee + cumulative commission_fee.
    """
    init_diary_db()
    now_iso = _ny_now().isoformat()
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE;")
        row = conn.execute(
            "SELECT * FROM simulated_trades WHERE id = ? AND status = 'OPEN';",
            (trade_id,),
        ).fetchone()
        if not row:
            conn.rollback()
            return False

        trade = dict(row)
        qty = int(trade["quantity"])
        entry_cost = float(trade["total_cost"])
        entry_fee = float(trade.get("commission_fee") or 0.0)
        is_spread = _is_vertical_spread(
            trade.get("strategy"), trade.get("strike"), trade.get("short_strike")
        )
        leg_mult = 2 if is_spread else 1
        exit_prem = float(exit_premium)
        exit_fee = 0.0 if exit_prem <= 0.0 else round(qty * 0.65 * leg_mult, 2)
        total_commission_fee = round(entry_fee + exit_fee, 2)
        gross_exit = qty * exit_prem * 100.0

        if "SELL" in str(trade.get("action", "")).upper():
            # Short option / credit: received entry_cost credit, pay gross_exit + exit_fee to close
            close_debit = gross_exit + exit_fee
            realized_dollar = round(entry_cost - close_debit, 2)
            short_k = trade.get("short_strike")
            if is_spread and short_k is not None:
                max_risk = max(
                    1.0,
                    abs(float(short_k) - float(trade["strike"])) * 100.0 * qty - entry_cost,
                )
            else:
                max_risk = max(1.0, entry_cost)
            realized_pct = round((realized_dollar / max_risk) * 100.0, 1)
        else:
            # Long option / debit: paid entry_cost, receive gross_exit - exit_fee on close
            net_proceeds = gross_exit - exit_fee
            realized_dollar = round(net_proceeds - entry_cost, 2)
            realized_pct = round((realized_dollar / max(1.0, entry_cost)) * 100.0, 1)

        merged_notes = trade["notes"] or ""
        if exit_notes:
            merged_notes += f" [Exit Notes ({now_iso[:10]}): {exit_notes}]"

        cur = conn.execute(
            """
            UPDATE simulated_trades
            SET status = 'CLOSED',
                exit_timestamp = ?,
                exit_premium = ?,
                exit_stock_price = ?,
                exit_commission_fee = ?,
                commission_fee = ?,
                realized_pnl_dollar = ?,
                realized_pnl_pct = ?,
                notes = ?
            WHERE id = ? AND status = 'OPEN';
            """,
            (
                now_iso, exit_prem, float(exit_stock_price), exit_fee,
                total_commission_fee, realized_dollar, realized_pct,
                merged_notes, trade_id,
            ),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_simulated_trade(trade_id: int, hard: bool = False) -> bool:
    """
    Soft-deletes (voids) a trade by default so practice history is never silently lost.
    When hard=True, creates a pre-delete online backup before permanently removing the row.
    """
    init_diary_db()
    if hard:
        backup_diary_db(tag="pre_delete")
        with _connect() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            cur = conn.execute("DELETE FROM simulated_trades WHERE id = ?;", (trade_id,))
            conn.commit()
            return cur.rowcount > 0

    now_iso = _ny_now().isoformat()
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE;")
        cur = conn.execute(
            """
            UPDATE simulated_trades
            SET status = 'VOIDED',
                deleted_at = ?
            WHERE id = ? AND status != 'VOIDED';
            """,
            (now_iso, trade_id),
        )
        conn.commit()
        return cur.rowcount > 0


def get_diary_portfolio_summary(
    live_marks: Optional[List[Dict[str, Any]]] = None,
    *,
    open_trades_with_live_pnl: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Aggregates overall practice portfolio statistics (Realized + Unrealized P&L, Win Rate %, Trade Counts).
    Includes CLOSED and EXPIRED trades in realized metrics and computes spread collateral properly.
    """
    init_diary_db()
    with _connect() as conn:
        closed = conn.execute(
            "SELECT * FROM simulated_trades WHERE status IN ('CLOSED', 'EXPIRED');"
        ).fetchall()
        open_rows = conn.execute(
            "SELECT * FROM simulated_trades WHERE status = 'OPEN';"
        ).fetchall()

    closed_list = [dict(r) for r in closed]
    total_trades = len(closed_list)
    wins = [t for t in closed_list if float(t.get("realized_pnl_dollar") or 0.0) > 0]
    losses = [t for t in closed_list if float(t.get("realized_pnl_dollar") or 0.0) < 0]

    realized_pnl_dollars = sum(float(t.get("realized_pnl_dollar") or 0.0) for t in closed_list)
    win_rate_pct = round((len(wins) / total_trades) * 100.0, 1) if total_trades > 0 else 0.0

    total_win_dollars = sum(float(t.get("realized_pnl_dollar") or 0.0) for t in wins)
    total_loss_dollars = abs(sum(float(t.get("realized_pnl_dollar") or 0.0) for t in losses))
    if total_loss_dollars > 0:
        profit_factor = min(99.9, round(total_win_dollars / max(1.0, total_loss_dollars), 2))
    else:
        profit_factor = 99.9 if total_win_dollars > 0 else 1.0

    active_capital_deployed = 0.0
    for r in open_rows:
        t = dict(r)
        t_cost = float(t.get("total_cost") or 0.0)
        if "SELL" in str(t.get("action") or "").upper() and t.get("short_strike") is not None:
            strike_v = float(t.get("strike") or 0.0)
            short_k = float(t["short_strike"])
            qty_v = int(t.get("quantity") or 1)
            if abs(strike_v - short_k) > 0.01:
                active_capital_deployed += max(0.0, abs(strike_v - short_k) * 100.0 * qty_v - t_cost)
            else:
                active_capital_deployed += t_cost
        else:
            active_capital_deployed += t_cost

    unrealized_pnl_dollars = 0.0
    marks_list = live_marks if live_marks is not None else open_trades_with_live_pnl
    if marks_list:
        for t in marks_list:
            if not isinstance(t, dict):
                continue
            val = t.get("live_unrealized_pnl_dollar")
            if val is None:
                val = t.get("unrealized_pnl_dollar", 0.0)
            unrealized_pnl_dollars += float(val or 0.0)

    starting_paper_capital = 100_000.0
    current_portfolio_value = starting_paper_capital + realized_pnl_dollars + unrealized_pnl_dollars

    return {
        "starting_paper_capital": starting_paper_capital,
        "current_portfolio_value": round(current_portfolio_value, 2),
        "realized_pnl_dollars": round(realized_pnl_dollars, 2),
        "unrealized_pnl_dollars": round(unrealized_pnl_dollars, 2),
        "total_pnl_dollars": round(realized_pnl_dollars + unrealized_pnl_dollars, 2),
        "total_closed_trades": total_trades,
        "open_trades_count": len(open_rows),
        "winning_trades_count": len(wins),
        "losing_trades_count": len(losses),
        "win_rate_pct": win_rate_pct,
        "profit_factor": profit_factor,
        "active_capital_deployed": round(active_capital_deployed, 2),
        "best_trade_dollar": round(
            max([float(t.get("realized_pnl_dollar") or 0.0) for t in closed_list], default=0.0), 2
        ),
        "worst_trade_dollar": round(
            min([float(t.get("realized_pnl_dollar") or 0.0) for t in closed_list], default=0.0), 2
        ),
    }


# =========================================================================
# SECTION 1B: BACKUP, WAL CHECKPOINT, EXPORT & HEALTH TELEMETRY
# =========================================================================

def backup_diary_db(tag: str = "auto", keep: int = 14) -> Optional[str]:
    """
    Creates an online consistent SQLite backup into data/backups/simulated_diary_<YYYYMMDD_HHMMSS>_<tag>.db
    using SQLite's online backup API, atomically replacing temp output and pruning older backups.
    """
    init_diary_db()
    if not os.path.exists(DB_PATH):
        return None

    safe_tag = re.sub(r"[^A-Za-z0-9_-]+", "_", str(tag or "auto")).strip("_") or "auto"
    b_dir = _backup_dir()
    os.makedirs(b_dir, exist_ok=True)
    ts_str = _ny_now().strftime("%Y%m%d_%H%M%S")
    final_name = f"simulated_diary_{ts_str}_{safe_tag}.db"
    final_path = os.path.join(b_dir, final_name)
    tmp_path = os.path.join(b_dir, f".{final_name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")

    src: Optional[sqlite3.Connection] = None
    dst: Optional[sqlite3.Connection] = None
    try:
        src = sqlite3.connect(DB_PATH, timeout=30.0)
        src.execute("PRAGMA busy_timeout=30000;")
        dst = sqlite3.connect(tmp_path, timeout=30.0)
        src.backup(dst)
        dst.commit()
        dst.close()
        dst = None
        src.close()
        src = None
        os.replace(tmp_path, final_path)

        keep_n = max(1, int(keep))
        existing_backups = [
            os.path.join(b_dir, f)
            for f in os.listdir(b_dir)
            if f.startswith("simulated_diary_") and f.endswith(".db")
        ]
        existing_backups.sort(key=lambda p: (os.path.getmtime(p), os.path.basename(p)), reverse=True)
        for old_path in existing_backups[keep_n:]:
            try:
                os.remove(old_path)
            except OSError:
                pass
        return final_path
    except Exception as e:
        print(f"[diary_db] Backup failed ({safe_tag}): {e}")
        return None
    finally:
        if dst is not None:
            try:
                dst.close()
            except Exception:
                pass
        if src is not None:
            try:
                src.close()
            except Exception:
                pass
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def checkpoint_wal() -> None:
    """Flushes WAL frames into the main simulated_diary.db file and truncates the WAL."""
    if not os.path.exists(DB_PATH):
        return
    try:
        with _connect() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    except Exception as e:
        print(f"[diary_db] WAL checkpoint warning: {e}")


def export_diary_data() -> Dict[str, Any]:
    """Exports ALL simulated_trades (uncapped, including VOIDED/EXPIRED/CLOSED/OPEN) and portfolio summary."""
    init_diary_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM simulated_trades ORDER BY id DESC;"
        ).fetchall()
    trades = [_format_trade_row(dict(r)) for r in rows]
    return {
        "exported_at": _ny_now().isoformat(),
        "schema_version": _SCHEMA_VERSION,
        "total_trades": len(trades),
        "summary": get_diary_portfolio_summary(),
        "trades": trades,
    }


def get_diary_health() -> Dict[str, Any]:
    """Returns database integrity, durability PRAGMAs, trade counts, and backup inventory."""
    init_diary_db()
    with _connect() as conn:
        integrity_row = conn.execute("PRAGMA integrity_check;").fetchone()
        integrity = str(integrity_row[0]) if integrity_row else "unknown"
        jm_row = conn.execute("PRAGMA journal_mode;").fetchone()
        journal_mode = str(jm_row[0]).lower() if jm_row else "unknown"
        sync_row = conn.execute("PRAGMA synchronous;").fetchone()
        sync_num = int(sync_row[0]) if sync_row is not None else -1
        synchronous = _SYNC_LABELS.get(sync_num, str(sync_num))

        open_trades = int(
            conn.execute("SELECT COUNT(*) FROM simulated_trades WHERE status = 'OPEN';").fetchone()[0]
        )
        closed_trades = int(
            conn.execute(
                "SELECT COUNT(*) FROM simulated_trades WHERE status IN ('CLOSED', 'EXPIRED');"
            ).fetchone()[0]
        )
        total_trades = int(
            conn.execute("SELECT COUNT(*) FROM simulated_trades;").fetchone()[0]
        )

    b_dir = _backup_dir()
    backups: List[str] = []
    if os.path.isdir(b_dir):
        backups = [
            os.path.join(b_dir, f)
            for f in os.listdir(b_dir)
            if f.startswith("simulated_diary_") and f.endswith(".db")
        ]
        backups.sort(key=lambda p: (os.path.getmtime(p), os.path.basename(p)), reverse=True)

    return {
        "integrity": integrity,
        "journal_mode": journal_mode,
        "synchronous": synchronous,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "total_trades": total_trades,
        "backups_count": len(backups),
        "latest_backup": os.path.basename(backups[0]) if backups else None,
    }


# =========================================================================
# SECTION 2: DAILY TOP-5 RECOMMENDATION SNAPSHOT & 24/7 TRACKER
# =========================================================================

def has_snapshot_for_date(snapshot_date: str, sector_name: str) -> bool:
    """Checks whether today's snapshot for this sector is already archived."""
    init_diary_db()
    norm_sector = _normalize_sector_safe(sector_name)
    with _connect() as conn:
        count = conn.execute("""
            SELECT COUNT(*) FROM daily_recommendations
            WHERE snapshot_date = ? AND sector = ?;
        """, (snapshot_date, norm_sector)).fetchone()[0]
        return count >= 1


def save_top5_snapshot(
    sector_name: str,
    candidates: List[Dict[str, Any]],
    snapshot_date: Optional[str] = None,
) -> int:
    """
    Saves the top 5 vetted candidates for a sector into the SQLite diary.
    Guards against empty candidate lists BEFORE deleting existing rows, runs atomically
    under BEGIN IMMEDIATE, normalizes sector names, and persists v4 raw_meta_json fields.
    """
    if not candidates:
        return 0

    init_diary_db()
    norm_sector = _normalize_sector_safe(sector_name)
    now = _ny_now()
    s_date = snapshot_date or now.strftime("%Y-%m-%d")
    s_time = now.strftime("%H:%M:%S")
    created_at = now.isoformat()

    saved_count = 0
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute(
            "DELETE FROM daily_recommendations WHERE snapshot_date = ? AND sector = ?;",
            (s_date, norm_sector),
        )
        for idx, c in enumerate(candidates[:5], start=1):
            sym = c["symbol"]
            m = c.get("metrics", {}) or {}
            bp = c.get("blueprint", {}) or {}
            ot = c.get("options_telemetry") or m.get("options_telemetry") or {}
            near_opt = m.get("near_live_option") if isinstance(m.get("near_live_option"), dict) else {}

            conv_200 = c.get("conviction_score_200")
            if conv_200 is None:
                conv_200 = bp.get("conviction_score_200", m.get("conviction_score_200"))

            rec_dte = c.get("recommended_dte") or bp.get("recommended_dte") or m.get("recommended_dte") or 35
            dte_rat = c.get("dte_rationale") or bp.get("dte_rationale") or m.get("dte_rationale") or ""

            iv_raw = ot.get("iv_pct")
            if iv_raw is None:
                iv_raw = m.get("iv_pct")
            if iv_raw is None:
                iv_raw = near_opt.get("iv")
            iv_pct: Optional[float] = None
            if iv_raw is not None:
                try:
                    iv_f = float(iv_raw)
                    if 0.0 < iv_f <= 3.5:
                        iv_f *= 100.0
                    if iv_f > 0.0:
                        iv_pct = round(iv_f, 1)
                except (TypeError, ValueError):
                    iv_pct = None

            raw_meta = {
                "sector": norm_sector,
                "rank": idx,
                "symbol": sym,
                "action": m.get("action", "BUY CALL"),
                "composite_score": bp.get("composite_score", 50.0),
                "conviction_score_200": conv_200,
                "recommended_dte": int(rec_dte) if rec_dte is not None else 35,
                "dte_rationale": str(dte_rat),
                "iv_pct": iv_pct,
                "price": m.get("price", 100.0),
                "expected_basis_pct": m.get("expected_basis_pct", 0.0),
                "whale_badge": m.get("whale_badge", "⚪ TWO-WAY FLOW"),
                "whale_score": m.get("whale_score", 0.0),
                "strike": m.get("recommended_strike", 100.0),
                "target_price": m.get("target_price", 100.0),
                "invalidation_price": m.get("invalidation_price", 95.0),
                "days_to_earnings": m.get("days_to_earnings", 45),
                "earnings_date": m.get("earnings_date", "Clear"),
            }

            conn.execute(
                """
                INSERT OR REPLACE INTO daily_recommendations (
                    snapshot_date, snapshot_time, sector, rank, symbol, company_name,
                    action, composite_score, price_at_snapshot, vwma20_at_rec, z_score_at_rec,
                    expected_basis_pct, empirical_win_rate, whale_badge, whale_score,
                    days_to_earnings, earnings_date, recommended_strike, target_price,
                    invalidation_price, half_life, raw_meta_json, created_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                );
                """,
                (
                    s_date, s_time, norm_sector, idx, sym, c.get("company_name", sym),
                    m.get("action", "BUY CALL"), float(bp.get("composite_score", 50.0)),
                    float(m.get("price", 0.0)), float(m.get("vwma20", m.get("price", 0.0))),
                    float(m.get("z_score_5d", 0.0)), float(m.get("expected_basis_pct", 0.0)),
                    float(m.get("empirical_win_rate_pct", 55.0)), str(m.get("whale_badge", "⚪ TWO-WAY FLOW")),
                    float(m.get("whale_score", 0.0)), int(m.get("days_to_earnings", 45)),
                    str(m.get("earnings_date", "Clear")), float(m.get("recommended_strike", m.get("price", 0.0))),
                    float(m.get("target_price", m.get("price", 0.0))),
                    float(m.get("invalidation_price", m.get("price", 0.0) * 0.95)),
                    float(m.get("ou_half_life", 5.0)), json.dumps(raw_meta), created_at,
                ),
            )
            saved_count += 1
        conn.commit()

    return saved_count


def get_all_snapshot_dates() -> List[str]:
    """Returns sorted list of distinct snapshot dates in descending order."""
    init_diary_db()
    with _connect() as conn:
        rows = conn.execute("""
            SELECT DISTINCT snapshot_date FROM daily_recommendations
            ORDER BY snapshot_date DESC;
        """).fetchall()
        return [r[0] for r in rows]


def get_historical_snapshots(
    snapshot_date: Optional[str] = None,
    sector_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetches historical Top-5 recommendation records matching optional filters."""
    init_diary_db()
    query = "SELECT * FROM daily_recommendations WHERE 1=1"
    params: List[Any] = []

    if snapshot_date:
        query += " AND snapshot_date = ?"
        params.append(snapshot_date)
    if sector_name and sector_name != "All Sectors":
        query += " AND sector = ?"
        params.append(sector_name)

    query += " ORDER BY snapshot_date DESC, sector ASC, rank ASC;"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def record_daily_iv_snapshot(symbol: str, atm_iv: float, trade_date: Optional[str] = None) -> None:
    """Persists one daily OPRA ATM IV reading (%) per ticker to accumulate true IV rank history."""
    sym = (symbol or "").strip().upper()
    if not sym or atm_iv is None:
        return
    try:
        iv_val = float(atm_iv)
        if iv_val <= 3.5:
            iv_val *= 100.0
        if not (3.0 <= iv_val <= 350.0):
            return
    except Exception:
        return
    init_diary_db()
    t_date = trade_date or _ny_today().isoformat()
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO iv_history_log (symbol, trade_date, atm_iv) VALUES (?, ?, ?);",
                (sym, t_date, round(iv_val, 2)),
            )
            conn.commit()
    except Exception:
        pass


def get_iv_percentile_stats(symbol: str, current_iv: float, fallback_hv_rank: float = 50.0) -> Dict[str, Any]:
    """
    Computes historical OPRA IV percentile from accumulated snapshots, smoothly blending
    with the 1-year realized volatility rank when fewer than 30 days of OPRA IV logs exist.
    """
    sym = (symbol or "").strip().upper()
    iv_cur = float(current_iv or 0.0)
    if 0.0 < iv_cur <= 3.5:
        iv_cur *= 100.0
    hv_fb = max(0.0, min(100.0, float(fallback_hv_rank or 50.0)))
    if not sym or iv_cur <= 0:
        return {"iv_rank_blended": round(hv_fb, 1), "opra_iv_days": 0, "opra_iv_pct_rank": None}

    init_diary_db()
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT atm_iv FROM iv_history_log WHERE symbol = ? ORDER BY trade_date DESC LIMIT 252;",
                (sym,),
            ).fetchall()
        vals = [float(r[0]) for r in rows if r and r[0] is not None]
        n = len(vals)
        if n >= 5:
            below = sum(1 for v in vals if v <= iv_cur)
            opra_pct = (below / float(n)) * 100.0
            weight_opra = min(1.0, n / 30.0)
            blended = (weight_opra * opra_pct) + ((1.0 - weight_opra) * hv_fb)
            return {
                "iv_rank_blended": round(max(0.0, min(100.0, blended)), 1),
                "opra_iv_days": n,
                "opra_iv_pct_rank": round(opra_pct, 1),
            }
        return {"iv_rank_blended": round(hv_fb, 1), "opra_iv_days": n, "opra_iv_pct_rank": None}
    except Exception:
        return {"iv_rank_blended": round(hv_fb, 1), "opra_iv_days": 0, "opra_iv_pct_rank": None}
