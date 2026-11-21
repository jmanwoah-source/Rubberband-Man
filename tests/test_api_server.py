import os
import tempfile
import unittest

from fastapi.testclient import TestClient

import api_server
import diary_db
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

    def test_health_and_diary_crud_round_trip(self):
        res_h = self.client.get("/api/health")
        self.assertEqual(res_h.status_code, 200)
        body_h = res_h.json()
        self.assertTrue(body_h["ok"])
        self.assertIn("Semiconductors", body_h["sectors"])

        res_d0 = self.client.get("/api/diary")
        self.assertEqual(res_d0.status_code, 200)
        self.assertEqual(len(res_d0.json()["open_trades"]), 0)

        create_payload = {
            "symbol": "NVDA",
            "action": "BUY_TO_OPEN",
            "option_type": "CALL",
            "strike": 140.0,
            "expiration_date": "2026-12-18",
            "quantity": 1,
            "limit_price": 4.50,
            "stock_price_at_entry": 136.0,
            "strategy": "SINGLE_LEG",
            "order_type": "LIMIT",
            "conviction_score": 120.0,
            "notes": "API unit test",
            "dte": 35,
        }
        res_post = self.client.post("/api/diary/trades", json=create_payload)
        self.assertEqual(res_post.status_code, 200)
        trade_id = res_post.json()["trade"]["id"]

        res_d1 = self.client.get("/api/diary")
        self.assertEqual(len(res_d1.json()["open_trades"]), 1)

        res_close = self.client.post(
            f"/api/diary/trades/{trade_id}/close",
            json={"exit_premium": 6.20, "exit_stock_price": 143.0, "exit_notes": "target hit"},
        )
        self.assertEqual(res_close.status_code, 200)
        self.assertTrue(res_close.json()["ok"])

        res_d2 = self.client.get("/api/diary")
        self.assertEqual(len(res_d2.json()["open_trades"]), 0)
        self.assertEqual(len(res_d2.json()["closed_trades"]), 1)

    def test_ledger_endpoint_empty_safe(self):
        res_l = self.client.get("/api/ledger")
        self.assertEqual(res_l.status_code, 200)
        self.assertEqual(res_l.json()["snapshots"], [])


if __name__ == "__main__":
    unittest.main()
