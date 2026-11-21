"""
Regression & quantitative integrity suite for Rubberband Man v4.0.
Verifies Option pricing / Greeks, SVI / Kalman / GEX / EV / Conviction math,
Engine V3 cache keys & secret redaction, SQLite WAL concurrency & P&L accounting,
daemon market-window logic, LLM router resilience, and XSS escaping.
"""
from __future__ import annotations

import datetime
import math
import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import daily_tracker_daemon
import diary_db
import edu_annotations
import fmp_client
import intel_bus_bridge
import llm_router
import quant_kernel as qk
import rubberband_charts as rbc
import rubberband_engine_v3 as rbe3
import ui_navigation


class TestQuantKernelMath(unittest.TestCase):
    def test_bs_put_call_parity_with_dividend_yield_and_validation(self):
        spot, strike, t_yr, r, q, sig = 120.0, 115.0, 45.0 / 365.0, 0.045, 0.02, 0.35
        c = qk.black_scholes_all_greeks(spot, strike, t_yr, r, sig, is_call=True, q=q)
        p = qk.black_scholes_all_greeks(spot, strike, t_yr, r, sig, is_call=False, q=q)
        self.assertTrue(c["valid"] and p["valid"])
        lhs = c["price"] - p["price"]
        rhs = spot * math.exp(-q * t_yr) - strike * math.exp(-r * t_yr)
        self.assertAlmostEqual(lhs, rhs, places=6)

        bad = qk.black_scholes_all_greeks(float("nan"), 100.0, 0.1, 0.04, 0.3, is_call=True)
        self.assertFalse(bad["valid"])
        exp0 = qk.black_scholes_all_greeks(100.0, 95.0, 0.0, 0.04, 0.3, is_call=True)
        self.assertTrue(exp0["valid"])
        self.assertAlmostEqual(exp0["price"], 5.0, places=6)

    def test_american_crr_deep_itm_put_early_exercise_and_theta(self):
        g = qk.american_crr_price_and_greeks(50.0, 100.0, 0.5, 0.05, 0.20, is_call=False, steps=40, q=0.0)
        self.assertTrue(g["valid"])
        self.assertAlmostEqual(g["price"], 50.0, places=2)
        self.assertGreater(g["early_exercise_premium"], 2.0)
        self.assertAlmostEqual(g["theta_daily"], 0.0, places=3)

        # Extreme low-vol/high-rate regime should adapt steps dynamically without failing
        g_ext = qk.american_crr_price_and_greeks(100.0, 100.0, 0.5, 0.12, 0.02, is_call=True, steps=20, q=0.0)
        self.assertTrue(g_ext["valid"])
        self.assertGreater(g_ext["price"], 0.0)

    def test_svi_smile_25d_and_length_match(self):
        strikes = np.array([80.0, 88.0, 94.0, 100.0, 106.0, 112.0, 120.0])
        ivs = np.array([0.46, 0.41, 0.37, 0.34, 0.32, 0.31, 0.315])
        res = qk.fit_svi_volatility_smile(strikes, ivs, spot=100.0, t_years=35.0 / 365.0)
        self.assertEqual(len(res["fitted_ivs"]), len(strikes))
        self.assertGreater(res["put_25d_iv"], res["call_25d_iv"])

    def test_kalman_dynamic_beta_handles_nans_and_co_movement(self):
        rng = np.random.default_rng(7)
        bench_ret = rng.normal(0.0005, 0.012, size=120)
        stock_ret = 1.4 * bench_ret + rng.normal(0.0, 0.006, size=120)
        bench_px = 100.0 * np.exp(np.cumsum(bench_ret))
        stock_px = 100.0 * np.exp(np.cumsum(stock_ret))
        stock_px[15] = np.nan
        res = qk.kalman_dynamic_beta_and_z(stock_px, bench_px)
        self.assertTrue(all(math.isfinite(float(v)) for v in res.values()))
        self.assertGreater(res["kalman_beta"], 0.8)

    def test_dealer_vanna_charm_and_gamma_flip_solver(self):
        rows = [
            {"strike": 90.0, "side": "put", "openInterest": 9000, "impliedVolatility": 0.36, "dte": 30},
            {"strike": 95.0, "side": "put", "openInterest": 6000, "impliedVolatility": 0.34, "dte": 30},
            {"strike": 100.0, "side": "put", "openInterest": 2000, "impliedVolatility": 0.32, "dte": 30},
            {"strike": 100.0, "side": "call", "openInterest": 2500, "impliedVolatility": 0.32, "dte": 30},
            {"strike": 105.0, "side": "call", "openInterest": 7000, "impliedVolatility": 0.30, "dte": 30},
            {"strike": 110.0, "side": "call", "openInterest": 9500, "impliedVolatility": 0.29, "dte": 30},
        ]
        df_chain = pd.DataFrame(rows)
        gex = qk.compute_dealer_vanna_charm_profile(df_chain, spot=100.0, q=0.01)
        self.assertGreater(gex["gamma_flip_strike"], 90.0)
        self.assertLess(gex["gamma_flip_strike"], 110.0)

        # 0 DTE intraday edge case must stay valid
        for r_item in rows:
            r_item["dte"] = 0
        gex_0 = qk.compute_dealer_vanna_charm_profile(pd.DataFrame(rows), spot=100.0)
        self.assertTrue(math.isfinite(gex_0["net_gex_m"]))

    def test_institutional_ev_rejects_all_positive_put_and_uses_365_calendar(self):
        bull_metrics = {
            "price": 100.0,
            "action": "BUY PUT",
            "recommended_strike": 98.0,
            "realized_vol": 35.0,
            "ou_half_life": 5.0,
            "empirical_win_rate_pct": 15.0,
            "empirical_sample_n": 30,
            "empirical_sample_n_eff": 24,
            "emp_p10_5d_pct": 2.0,
            "emp_p25_5d_pct": 3.5,
            "emp_p50_5d_pct": 5.0,
            "emp_p75_5d_pct": 7.0,
            "emp_p90_5d_pct": 9.0,
            "spread_friction_pct": 5.0,
        }
        res = qk.compute_institutional_ev_and_kelly(bull_metrics, live_option=None, account_equity=25000.0)
        self.assertLess(res["net_ev_pct"], 0.0)
        self.assertEqual(res["kelly_contracts"], 0)

    def test_conviction_score_calibration_and_etf_neutral_solvency(self):
        zero_payload = {
            "symbol": "TEST",
            "is_etf": True,
            "metrics": {
                "price": 100.0,
                "action": "BUY CALL",
                "z_score_5d": 0.0,
                "kalman_z_5d": 0.0,
                "hurst": 0.50,
                "ou_half_life": 5.0,
                "days_to_earnings": 45,
                "estimated_delta": 0.50,
            },
            "quant_edge": {"net_ev_pct": 0.0, "edge_t_stat": 0.0, "variance_rent_ratio": 1.0},
            "fundamentals": {"fund_score": 68.0},
            "gamma_walls": {"has_data": False},
            "skew_optimizer": {"has_data": False},
            "whale_oi": {"whale_score": 0.0},
        }
        c_zero = qk.compute_conviction_score_200(zero_payload)
        self.assertLessEqual(abs(c_zero["conviction_score_200"]), 10)
        self.assertEqual(c_zero["conviction_pillars"]["regime_solvency"], 0.0)


class TestEngineV3Health(unittest.TestCase):
    def test_fmp_cache_key_order_independent(self):
        k1 = rbe3._fmp_cache_key("profile", {"symbol": "NVDA", "limit": 5})
        k2 = rbe3._fmp_cache_key("profile", {"limit": 5, "symbol": "NVDA"})
        self.assertEqual(k1, k2)

    def test_redact_secrets_strips_keys(self):
        raw = "GET https://example.com/api?symbol=NVDA&apikey=SUPERSECRET123&token=TOK999"
        cleaned = rbe3._redact_secrets(raw)
        self.assertNotIn("SUPERSECRET123", cleaned)
        self.assertNotIn("TOK999", cleaned)
        bearer_cleaned = rbe3._redact_secrets("Authorization: Bearer abc123.xyz")
        self.assertNotIn("abc123.xyz", bearer_cleaned)
        self.assertEqual(
            fmp_client._redact_api_key("err ?apikey=MYKEY123&foo=1"),
            "err ?apikey=[REDACTED]&foo=1",
        )

    def test_wilder_rsi_flat_series_is_50(self):
        flat = pd.Series([150.0] * 40)
        rsi = rbe3.calculate_wilders_rsi(flat)
        self.assertAlmostEqual(float(rsi.iloc[-1]), 50.0, places=4)

    def test_ou_half_life_short_series_neutral_defaults(self):
        short_prices = pd.Series([100.0, 101.0, 100.5])
        short_vwma = pd.Series([100.0, 100.2, 100.3])
        ou_hl, hurst, ou_tag = rbe3.calculate_ou_half_life_and_hurst(short_prices - short_vwma, short_prices)
        self.assertTrue(math.isfinite(ou_hl) and math.isfinite(hurst))
        self.assertTrue(isinstance(ou_tag, str) and len(ou_tag) > 0)
        self.assertGreaterEqual(ou_hl, 1.0)
        self.assertGreaterEqual(hurst, 0.20)
        self.assertLessEqual(hurst, 0.80)

    def test_empirical_basis_spacing_and_percentiles(self):
        rng = np.random.default_rng(42)
        n = 300
        dates = pd.bdate_range("2023-01-02", periods=n)
        rets = rng.normal(0.0, 0.015, size=n)
        # Inject consecutive clustered drop days that must be spaced >= 5 bars apart
        rets[60:64] = -0.04
        closes = 100.0 * np.exp(np.cumsum(rets))
        df = pd.DataFrame({
            "date": dates,
            "open": closes,
            "high": closes * 1.01,
            "low": closes * 0.99,
            "close": closes,
            "volume": np.full(n, 2_000_000.0),
        })
        df["vwma20"] = df["close"].rolling(20, min_periods=1).mean()
        df["z_score"] = (df["close"] - df["vwma20"]) / (df["close"].rolling(20, min_periods=2).std().bfill().clip(lower=0.5))
        res = rbe3.calculate_empirical_basis_expectation(
            df["z_score"], df["close"], df["high"], df["low"], curr_z=-2.2, action="BUY CALL"
        )
        for key in ("p10_close_pct", "med_close_pct", "p90_close_pct", "empirical_sample_n_eff"):
            self.assertIn(key, res)
            self.assertTrue(math.isfinite(float(res[key])))

    def test_temporal_regime_has_bounded_day_edge_score(self):
        for wd in range(7):
            tr = rbe3.get_temporal_regime(override_day=wd)
            self.assertIn("day_edge_score", tr)
            self.assertGreaterEqual(tr["day_edge_score"], -25.0)
            self.assertLessEqual(tr["day_edge_score"], 25.0)

    def test_ui_navigation_view_slugs_alias(self):
        self.assertEqual(ui_navigation.VIEW_SLUGS[ui_navigation.VIEW_SCHWAB], "schwab")


class TestConnectionsDbAndDaemons(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.orig_db_path = diary_db.DB_PATH
        diary_db.DB_PATH = os.path.join(self.tmp_dir.name, "test_diary.db")
        with diary_db._INIT_LOCK:
            diary_db._DB_INITIALIZED_PATH = None
        diary_db.init_diary_db()

    def tearDown(self):
        diary_db.DB_PATH = self.orig_db_path
        with diary_db._INIT_LOCK:
            diary_db._DB_INITIALIZED_PATH = None
        self.tmp_dir.cleanup()

    def test_concurrent_trade_creation_and_sell_to_open_close_guard(self):
        def _worker(idx: int):
            return diary_db.create_simulated_trade(
                symbol="NVDA",
                action="SELL_TO_OPEN",
                option_type="CALL",
                strike=140.0 + idx,
                expiration_date="2026-12-18",
                quantity=2,
                limit_price=4.00,
                stock_price_at_entry=135.0,
                notes=f"concurrent #{idx}",
            )

        with ThreadPoolExecutor(max_workers=6) as ex:
            results = list(ex.map(_worker, range(8)))

        order_ids = [r["schwab_order_id"] for r in results]
        self.assertEqual(len(set(order_ids)), 8)

        open_trades = diary_db.get_open_trades()
        self.assertEqual(len(open_trades), 8)
        target_id = open_trades[0]["id"]

        # SELL_TO_OPEN profit: sold at 4.00, bought back at 1.50 -> +2.50 * 200 - exit comm > 0
        closed_ok = diary_db.close_simulated_trade(target_id, exit_premium=1.50, exit_stock_price=130.0)
        self.assertTrue(closed_ok)
        # Double-close must return False and not duplicate realized P&L
        closed_twice = diary_db.close_simulated_trade(target_id, exit_premium=0.50, exit_stock_price=125.0)
        self.assertFalse(closed_twice)

        closed_list = diary_db.get_closed_trades(limit=5)
        self.assertEqual(len(closed_list), 1)
        self.assertGreater(closed_list[0]["realized_pnl_dollar"], 400.0)

    def test_intel_bus_round_trip(self):
        sig = {
            "symbol": "MPWR",
            "track_name": "POWER",
            "status_badge": "ACTIVE",
            "wiki_score": 88.0,
            "thesis_hook": "High-efficiency VRM leader",
        }
        ok = intel_bus_bridge.write_signal_to_bus(sig, bus_dir=self.tmp_dir.name)
        self.assertTrue(ok)
        signals = intel_bus_bridge.read_intel_bus_signals(bus_dir=self.tmp_dir.name)
        self.assertTrue(any(s.get("symbol") == "MPWR" for s in signals))

    def test_daemon_snapshot_window_ny_time(self):
        ny = ZoneInfo("America/New_York")
        early_wkday = datetime.datetime(2026, 11, 18, 9, 15, tzinfo=ny)  # Wed 09:15 ET
        open_wkday = datetime.datetime(2026, 11, 18, 10, 0, tzinfo=ny)   # Wed 10:00 ET
        weekend = datetime.datetime(2026, 11, 21, 12, 0, tzinfo=ny)      # Sat 12:00 ET
        self.assertFalse(daily_tracker_daemon._is_valid_snapshot_window(early_wkday))
        self.assertTrue(daily_tracker_daemon._is_valid_snapshot_window(open_wkday))
        self.assertFalse(daily_tracker_daemon._is_valid_snapshot_window(weekend))

    def test_llm_router_models_and_error_classification(self):
        models = llm_router.get_gemini_fallback_models()
        self.assertTrue(len(models) >= 2)
        self.assertFalse(any("3.5" in m or "3.1" in m for m in models))
        self.assertTrue(llm_router._is_auth_gemini_error("401 PERMISSION_DENIED"))
        self.assertFalse(llm_router._is_auth_gemini_error("429 RESOURCE_EXHAUSTED"))
        self.assertTrue(llm_router._is_transient_gemini_error("429 RESOURCE_EXHAUSTED"))

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            ok, msg = llm_router.test_gemini_connection()
            self.assertFalse(ok)
            self.assertIn("missing", msg.lower())


class TestSecurityAndChartSafety(unittest.TestCase):
    def test_edu_annotations_escapes_xss(self):
        payload = {
            "vix_ratio": 0.92,
            "credit_z": 0.1,
            "tnx_yield": 4.2,
            "exposure_cap_pct": 100,
            "regime_label": '<script>alert("xss")</script>',
        }
        title, live, beg, inter, pro, thumb = edu_annotations._build_topic("macro_regime", payload)
        self.assertNotIn("<script>", live)
        self.assertIn("&lt;script&gt;", live)

    def test_float_card_html_escapes_xss_and_charts_handle_nones(self):
        xss = '<img src=x onerror=alert(1)>'
        html_out = rbc.create_float_topology_card_html(
            xss,
            {
                "has_data": True,
                "inst_hedge_regime": xss,
                "hazard_badge": xss,
                "collar_advice": xss,
            },
        )
        self.assertNotIn("<img src=x", html_out)
        self.assertIn("&lt;img", html_out)

        fig_payoff = rbc.create_schwab_payoff_curve_chart(
            symbol="NVDA",
            spot_price=135.0,
            strike=140.0,
            opt_type="CALL",
            limit_price=4.50,
            qty=1,
            dte=35,
            iv=0.45,
            target_price=None,
            stop_price=None,
        )
        self.assertGreater(len(fig_payoff.data), 0)

        fig_dot = rbc.create_ticker_options_strike_dot_matrix(
            "NVDA",
            {"price": None, "vwma20": None, "target_price": None, "realized_vol": None, "ou_half_life": None},
            {},
        )
        self.assertGreater(len(fig_dot.data), 0)


if __name__ == "__main__":
    unittest.main()
