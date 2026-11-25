import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient

import api_server
import diary_db
import diary_views
import edu_annotations


class TestEduApiAndServer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.orig_db_path = diary_db.DB_PATH
        diary_db.DB_PATH = os.path.join(self.tmp_dir.name, "api_test_diary.db")
        with diary_db._INIT_LOCK:
            diary_db._DB_INITIALIZED_PATH = None
        diary_db.init_diary_db()
        self.client = TestClient(api_server.app)

    def tearDown(self):
        diary_db.DB_PATH = self.orig_db_path
        with diary_db._INIT_LOCK:
            diary_db._DB_INITIALIZED_PATH = None
        self.tmp_dir.cleanup()

    def test_edu_get_topic_strips_formatting_markup(self):
        topic = edu_annotations.get_edu_topic(
            "macro_regime",
            {"vix_ratio": 0.91, "credit_z": 0.1, "tnx_yield": 4.2, "exposure_cap_pct": 100, "regime_label": "CALM"},
        )
        self.assertIsNotNone(topic)
        self.assertEqual(topic["key"], "macro_regime")
        self.assertNotIn("<b>", topic["l1"])
        self.assertIn("VIX", topic["live"])

    def test_spa_path_traversal_never_leaks_env(self):
        for bad_path in (
            "/%2e%2e/%2e%2e/.env",
            "/..%2f..%2f.env",
            "/..%5c..%5c.env",
            "/../../data/simulated_diary.db",
        ):
            res = self.client.get(bad_path)
            self.assertNotIn("FMP_API_KEY=", res.text)
            self.assertNotIn("GEMINI_API_KEY=", res.text)
            self.assertIn(res.status_code, (400, 404, 200))
            if res.status_code == 200:
                self.assertIn("<!doctype html>", res.text.lower())

    def test_health_and_diary_zero_loss_lifecycle(self):
        res_h = self.client.get("/api/health")
        self.assertEqual(res_h.status_code, 200)
        body_h = res_h.json()
        self.assertTrue(body_h["ok"])
        self.assertIn("Semiconductors", body_h["sectors"])
        self.assertEqual(body_h["db_health"]["integrity"], "ok")
        self.assertIsInstance(body_h["api_keys"]["fmp"], bool)

        # Spread validation: equal short_strike must fail with HTTP 422
        bad_spread = {
            "symbol": "NVDA",
            "action": "BUY_TO_OPEN",
            "option_type": "CALL",
            "strike": 140.0,
            "short_strike": 140.0,
            "expiration_date": "2027-01-15",
            "quantity": 1,
            "limit_price": 4.50,
            "stock_price_at_entry": 136.0,
            "strategy": "VERTICAL_DEBIT_SPREAD",
            "order_type": "LIMIT",
        }
        self.assertEqual(self.client.post("/api/diary/trades", json=bad_spread).status_code, 422)

        create_payload = {
            "symbol": "NVDA",
            "action": "BUY_TO_OPEN",
            "option_type": "CALL",
            "strike": 140.5,
            "expiration_date": "2027-01-15",
            "quantity": 1,
            "limit_price": 4.50,
            "stock_price_at_entry": 136.0,
            "strategy": "SINGLE_LEG",
            "order_type": "LIMIT",
            "time_in_force": "GTC",
            "target_stock_price": 152.0,
            "stop_stock_price": 128.0,
            "implied_vol_at_entry": 44.0,
            "conviction_score": 120.0,
            "notes": "API zero-loss test",
            "dte": 35,
        }
        res_post = self.client.post("/api/diary/trades", json=create_payload)
        self.assertEqual(res_post.status_code, 200)
        created = res_post.json()["trade"]
        trade_id = created["id"]
        self.assertEqual(created["limit_price"], 4.50)
        self.assertEqual(created["entry_premium"], 4.50)
        self.assertEqual(created["time_in_force"], "GTC")

        with mock.patch("api_server.rbe3.fmp_batch_quotes", return_value={"NVDA": {"price": 141.0}}):
            res_d1 = self.client.get("/api/diary")
        self.assertEqual(res_d1.status_code, 200)
        open_list = res_d1.json()["open_trades"]
        self.assertEqual(len(open_list), 1)
        self.assertEqual(open_list[0]["limit_price"], 4.50)
        self.assertEqual(open_list[0]["entry_premium"], 4.50)
        self.assertEqual(open_list[0]["target_stock_price"], 152.0)

        # Inline PATCH edit preserves data cleanly
        res_patch = self.client.patch(
            f"/api/diary/trades/{trade_id}",
            json={"target_stock_price": 155.0, "stop_stock_price": 130.0, "notes": "Updated target", "time_in_force": "DAY"},
        )
        self.assertEqual(res_patch.status_code, 200)
        self.assertEqual(res_patch.json()["trade"]["target_stock_price"], 155.0)
        self.assertEqual(res_patch.json()["trade"]["notes"], "Updated target")

        # Online SQLite backup endpoint creates valid readable DB file
        res_bak = self.client.post("/api/diary/backup")
        self.assertEqual(res_bak.status_code, 200)
        bak_path = res_bak.json()["backup_path"]
        self.assertTrue(os.path.exists(bak_path))
        conn = sqlite3.connect(bak_path)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        conn.close()

        # Close at worthless expiration (exit_premium == 0.0) must waive exit commission
        res_close = self.client.post(
            f"/api/diary/trades/{trade_id}/close",
            json={"exit_premium": 0.0, "exit_stock_price": 125.0, "exit_notes": "expired worthless"},
        )
        self.assertEqual(res_close.status_code, 200)

        # Second trade soft-voided via DELETE remains in uncapped JSON/CSV export
        res_post2 = self.client.post("/api/diary/trades", json={**create_payload, "symbol": "AVGO"})
        trade_id2 = res_post2.json()["trade"]["id"]
        res_del = self.client.delete(f"/api/diary/trades/{trade_id2}")
        self.assertEqual(res_del.status_code, 200)

        res_exp_json = self.client.get("/api/diary/export?format=json")
        self.assertEqual(res_exp_json.status_code, 200)
        exported_trades = res_exp_json.json()["trades"]
        self.assertEqual(len(exported_trades), 2)
        statuses = {t["symbol"]: t["status"] for t in exported_trades}
        self.assertEqual(statuses["AVGO"], "VOIDED")
        nvda_row = next(t for t in exported_trades if t["symbol"] == "NVDA")
        self.assertEqual(nvda_row["exit_commission_fee"], 0.0)

        res_exp_csv = self.client.get("/api/diary/export?format=csv")
        self.assertEqual(res_exp_csv.status_code, 200)
        self.assertIn("NVDA", res_exp_csv.text)
        self.assertIn("AVGO", res_exp_csv.text)

    def test_empty_snapshot_does_not_wipe_and_sell_unrealized_sign(self):
        sample = [{"symbol": "NVDA", "metrics": {"price": 135.0, "action": "BUY CALL"}, "conviction_score_200": 115, "recommended_dte": 35}]
        inserted = diary_db.save_top5_snapshot("Semiconductors", sample, snapshot_date="2026-11-24")
        self.assertEqual(inserted, 1)
        # Empty candidate list must NOT delete existing snapshot rows
        wiped = diary_db.save_top5_snapshot("Semiconductors", [], snapshot_date="2026-11-24")
        self.assertEqual(wiped, 0)
        rows = diary_db.get_historical_snapshots("2026-11-24", "Semiconductors")
        self.assertEqual(len(rows), 1)

        # SELL_TO_OPEN profit when option value drops below credit received
        short_trade = {
            "symbol": "NVDA",
            "action": "SELL_TO_OPEN",
            "option_type": "CALL",
            "strategy": "SINGLE_LEG",
            "strike": 140.0,
            "expiration_date": "2027-01-15",
            "quantity": 1,
            "limit_price": 6.00,
            "total_cost": 599.35,
            "stock_price_at_entry": 138.0,
            "implied_vol_at_entry": 40.0,
        }
        with mock.patch("diary_views.marketdata_client.get_option_chain_native", return_value=None):
            mark = diary_views.estimate_live_option_mark(short_trade, current_spot=115.0)
        self.assertGreater(mark["unrealized_dollar"], 0.0)

    def test_ledger_endpoint_empty_safe(self):
        res_l = self.client.get("/api/ledger")
        self.assertEqual(res_l.status_code, 200)
        self.assertEqual(res_l.json()["snapshots"], [])


if __name__ == "__main__":
    unittest.main()
