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
import sqlite3
import datetime
from typing import List, Dict, Any, Optional, Tuple

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "simulated_diary.db")


def _get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured for concurrent WAL mode."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_diary_db() -> None:
    """Initializes database schema with WAL mode and indices."""
    with _get_connection() as conn:
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
            expiration_date TEXT NOT NULL,
            dte_at_entry INTEGER DEFAULT 35,
            order_type TEXT DEFAULT 'LIMIT',
            quantity INTEGER NOT NULL DEFAULT 1,
            limit_price REAL NOT NULL,
            stock_price_at_entry REAL NOT NULL,
            total_cost REAL NOT NULL,
            commission_fee REAL DEFAULT 0.65,
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

        # Migrations: ensure implied_vol_at_entry and short_strike exist on simulated_trades
        try:
            conn.execute("ALTER TABLE simulated_trades ADD COLUMN implied_vol_at_entry REAL;")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE simulated_trades ADD COLUMN short_strike REAL;")
        except Exception:
            pass

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
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_recs_date_sec_rank ON daily_recommendations(snapshot_date, sector, rank);")
        conn.commit()


# =========================================================================
# SECTION 1: SIMULATED OPTIONS TRADING & SCHWAB DIARY LEDGER
# =========================================================================

def generate_schwab_order_id(symbol: str) -> str:
    """Generates an authentic Charles Schwab style order reference number."""
    now = datetime.datetime.now()
    rand_suffix = (int(now.timestamp() * 1000) % 90000) + 10000
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
) -> Dict[str, Any]:
    """
    Creates a simulated options trade formatted according to Charles Schwab order conventions.
    Saves the trade into SQLite and returns the confirmed trade payload.
    """
    init_diary_db()
    order_id = generate_schwab_order_id(symbol)
    now_iso = datetime.datetime.now().isoformat()
    
    # Standard Schwab options calculation: Limit Price * 100 * Qty + Schwab contract fee ($0.65/contract)
    contract_fee = round(quantity * 0.65, 2)
    total_cost = round((quantity * limit_price * 100.0) + contract_fee, 2)

    # Compute Days to Expiration (DTE)
    if dte is not None and int(dte) > 0:
        dte = int(dte)
    else:
        dte = 35
        try:
            # Check if DTE is explicitly in the label like '(29 DTE'
            m_dte = re.search(r"\((\d+)\s*DTE", str(expiration_date))
            if m_dte:
                dte = max(1, int(m_dte.group(1)))
            else:
                clean_exp = str(expiration_date).split("(")[0].strip()
                try:
                    exp_dt = datetime.datetime.strptime(clean_exp, "%b %d, %Y").date()
                    dte = max(1, (exp_dt - datetime.date.today()).days)
                except Exception:
                    exp_dt = datetime.date.fromisoformat(clean_exp[:10])
                    dte = max(1, (exp_dt - datetime.date.today()).days)
        except Exception:
            dte = 35

    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO simulated_trades (
            schwab_order_id, symbol, strategy, action, option_type, strike, short_strike, expiration_date,
            dte_at_entry, order_type, quantity, limit_price, stock_price_at_entry, total_cost,
            commission_fee, target_stock_price, stop_stock_price, target_premium, stop_premium,
            entry_timestamp, status, conviction_score, expected_basis_pct, whale_badge,
            catalyst_tag, notes, implied_vol_at_entry, created_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?
        );
        """, (
            order_id, symbol.upper(), strategy, action, option_type.upper(), strike,
            float(short_strike) if short_strike is not None else None,
            expiration_date, dte, order_type, quantity, limit_price, stock_price_at_entry,
            total_cost, contract_fee, target_stock_price, stop_stock_price, target_premium,
            stop_premium, now_iso, conviction_score, expected_basis_pct, whale_badge,
            catalyst_tag, notes,
            float(implied_vol_at_entry) if implied_vol_at_entry is not None else None,
            now_iso
        ))
        trade_id = cursor.lastrowid
        conn.commit()

    return {
        "id": trade_id,
        "schwab_order_id": order_id,
        "symbol": symbol.upper(),
        "strategy": strategy,
        "action": action,
        "option_type": option_type.upper(),
        "strike": strike,
        "short_strike": float(short_strike) if short_strike is not None else None,
        "expiration_date": expiration_date,
        "dte_at_entry": dte,
        "order_type": order_type,
        "quantity": quantity,
        "limit_price": limit_price,
        "stock_price_at_entry": stock_price_at_entry,
        "total_cost": total_cost,
        "commission_fee": contract_fee,
        "target_stock_price": target_stock_price,
        "stop_stock_price": stop_stock_price,
        "status": "OPEN",
        "entry_timestamp": now_iso,
        "notes": notes
    }


def get_open_trades() -> List[Dict[str, Any]]:
    """Retrieves all currently active open simulated trades."""
    init_diary_db()
    with _get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM simulated_trades
            WHERE status = 'OPEN'
            ORDER BY id DESC;
        """).fetchall()
        return [dict(r) for r in rows]


def get_closed_trades(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves closed or expired simulated trades for historical auditing."""
    init_diary_db()
    with _get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM simulated_trades
            WHERE status IN ('CLOSED', 'EXPIRED')
            ORDER BY exit_timestamp DESC
            LIMIT ?;
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def close_simulated_trade(
    trade_id: int,
    exit_premium: float,
    exit_stock_price: float,
    exit_notes: str = ""
) -> bool:
    """
    Closes an open simulated trade, calculating realized P&L and recording exit notes.
    """
    init_diary_db()
    now_iso = datetime.datetime.now().isoformat()
    with _get_connection() as conn:
        row = conn.execute("SELECT * FROM simulated_trades WHERE id = ?;", (trade_id,)).fetchone()
        if not row:
            return False
        
        trade = dict(row)
        qty = trade["quantity"]
        entry_prem = trade["limit_price"]
        entry_cost = trade["total_cost"]
        
        # Realized P&L
        gross_proceeds = qty * exit_premium * 100.0
        exit_fee = qty * 0.65
        net_proceeds = gross_proceeds - exit_fee
        realized_dollar = round(net_proceeds - entry_cost, 2)
        realized_pct = round((realized_dollar / max(1.0, entry_cost)) * 100.0, 1)

        merged_notes = trade["notes"] or ""
        if exit_notes:
            merged_notes += f" [Exit Notes ({now_iso[:10]}): {exit_notes}]"

        conn.execute("""
        UPDATE simulated_trades
        SET status = 'CLOSED',
            exit_timestamp = ?,
            exit_premium = ?,
            exit_stock_price = ?,
            realized_pnl_dollar = ?,
            realized_pnl_pct = ?,
            notes = ?
        WHERE id = ?;
        """, (now_iso, exit_premium, exit_stock_price, realized_dollar, realized_pct, merged_notes, trade_id))
        conn.commit()
        return True


def delete_simulated_trade(trade_id: int) -> bool:
    """Deletes a trade record from the database."""
    init_diary_db()
    with _get_connection() as conn:
        conn.execute("DELETE FROM simulated_trades WHERE id = ?;", (trade_id,))
        conn.commit()
        return True


def get_diary_portfolio_summary(open_trades_with_live_pnl: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Aggregates overall practice portfolio statistics (Realized + Unrealized P&L, Win Rate %, Trade Counts).
    """
    init_diary_db()
    with _get_connection() as conn:
        closed = conn.execute("SELECT * FROM simulated_trades WHERE status = 'CLOSED';").fetchall()
        open_rows = conn.execute("SELECT * FROM simulated_trades WHERE status = 'OPEN';").fetchall()

    closed_list = [dict(r) for r in closed]
    total_trades = len(closed_list)
    wins = [t for t in closed_list if t["realized_pnl_dollar"] > 0]
    losses = [t for t in closed_list if t["realized_pnl_dollar"] < 0]
    
    realized_pnl_dollars = sum(t["realized_pnl_dollar"] for t in closed_list)
    win_rate_pct = round((len(wins) / total_trades) * 100.0, 1) if total_trades > 0 else 0.0

    total_win_dollars = sum(t["realized_pnl_dollar"] for t in wins)
    total_loss_dollars = abs(sum(t["realized_pnl_dollar"] for t in losses))
    profit_factor = round(total_win_dollars / max(1.0, total_loss_dollars), 2) if total_loss_dollars > 0 else (round(total_win_dollars, 1) if total_win_dollars > 0 else 1.0)

    unrealized_pnl_dollars = 0.0
    active_capital_deployed = sum(dict(r)["total_cost"] for r in open_rows)
    
    if open_trades_with_live_pnl:
        unrealized_pnl_dollars = sum(t.get("live_unrealized_pnl_dollar", 0.0) for t in open_trades_with_live_pnl)

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
        "best_trade_dollar": round(max([t["realized_pnl_dollar"] for t in closed_list], default=0.0), 2),
        "worst_trade_dollar": round(min([t["realized_pnl_dollar"] for t in closed_list], default=0.0), 2)
    }


# =========================================================================
# SECTION 2: DAILY TOP-5 RECOMMENDATION SNAPSHOT & 24/7 TRACKER
# =========================================================================

def has_snapshot_for_date(snapshot_date: str, sector_name: str) -> bool:
    """Checks whether today's snapshot for this sector is already archived."""
    init_diary_db()
    with _get_connection() as conn:
        count = conn.execute("""
            SELECT COUNT(*) FROM daily_recommendations
            WHERE snapshot_date = ? AND sector = ?;
        """, (snapshot_date, sector_name)).fetchone()[0]
        return count >= 5


def save_top5_snapshot(
    sector_name: str,
    candidates: List[Dict[str, Any]],
    snapshot_date: Optional[str] = None
) -> int:
    """
    Saves the top 5 vetted candidates for a sector into the SQLite diary.
    Guarantees idempotency via INSERT OR REPLACE.
    """
    init_diary_db()
    now = datetime.datetime.now()
    s_date = snapshot_date or now.strftime("%Y-%m-%d")
    s_time = now.strftime("%H:%M:%S")
    created_at = now.isoformat()

    saved_count = 0
    with _get_connection() as conn:
        # Atomic idempotency: clear existing snapshot rows for this sector & date before re-inserting
        conn.execute("DELETE FROM daily_recommendations WHERE snapshot_date = ? AND sector = ?;", (s_date, sector_name))
        for idx, c in enumerate(candidates[:5], start=1):
            sym = c["symbol"]
            m = c.get("metrics", {})
            bp = c.get("blueprint", {})
            
            raw_meta = {
                "sector": sector_name,
                "rank": idx,
                "symbol": sym,
                "action": m.get("action", "BUY CALL"),
                "composite_score": bp.get("composite_score", 50.0),
                "price": m.get("price", 100.0),
                "expected_basis_pct": m.get("expected_basis_pct", 0.0),
                "whale_badge": m.get("whale_badge", "⚪ TWO-WAY FLOW"),
                "whale_score": m.get("whale_score", 0.0),
                "strike": m.get("recommended_strike", 100.0),
                "target_price": m.get("target_price", 100.0),
                "invalidation_price": m.get("invalidation_price", 95.0),
                "days_to_earnings": m.get("days_to_earnings", 45),
                "earnings_date": m.get("earnings_date", "Clear")
            }

            conn.execute("""
            INSERT OR REPLACE INTO daily_recommendations (
                snapshot_date, snapshot_time, sector, rank, symbol, company_name,
                action, composite_score, price_at_snapshot, vwma20_at_rec, z_score_at_rec,
                expected_basis_pct, empirical_win_rate, whale_badge, whale_score,
                days_to_earnings, earnings_date, recommended_strike, target_price,
                invalidation_price, half_life, raw_meta_json, created_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            );
            """, (
                s_date, s_time, sector_name, idx, sym, c.get("company_name", sym),
                m.get("action", "BUY CALL"), float(bp.get("composite_score", 50.0)),
                float(m.get("price", 0.0)), float(m.get("vwma20", m.get("price", 0.0))),
                float(m.get("z_score_5d", 0.0)), float(m.get("expected_basis_pct", 0.0)),
                float(m.get("empirical_win_rate_pct", 55.0)), str(m.get("whale_badge", "⚪ TWO-WAY FLOW")),
                float(m.get("whale_score", 0.0)), int(m.get("days_to_earnings", 45)),
                str(m.get("earnings_date", "Clear")), float(m.get("recommended_strike", m.get("price", 0.0))),
                float(m.get("target_price", m.get("price", 0.0))), float(m.get("invalidation_price", m.get("price", 0.0) * 0.95)),
                float(m.get("ou_half_life", 5.0)), json.dumps(raw_meta), created_at
            ))
            saved_count += 1
        conn.commit()

    return saved_count


def get_all_snapshot_dates() -> List[str]:
    """Returns sorted list of distinct snapshot dates in descending order."""
    init_diary_db()
    with _get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT snapshot_date FROM daily_recommendations
            ORDER BY snapshot_date DESC;
        """).fetchall()
        return [r[0] for r in rows]


def get_historical_snapshots(
    snapshot_date: Optional[str] = None,
    sector_name: Optional[str] = None
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

    with _get_connection() as conn:
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
    t_date = trade_date or datetime.date.today().isoformat()
    try:
        with _get_connection() as conn:
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
        with _get_connection() as conn:
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
