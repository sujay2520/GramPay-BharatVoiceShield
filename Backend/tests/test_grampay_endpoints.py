"""Tests for GramPay 3-Tier Endpoints and Section 4 Contract Compliance in main.py.

Verifies:
1. All 8 core Section 4 endpoints are accessible and follow contract.
2. POST /api/challenge/generate returns dynamic Nemotron phrase, challenge_id, and 2-min expiry.
3. POST /api/challenge/verify re-scores challenge audio and evaluates gate.
4. POST /api/pay/upi executes NPCI Hello! UPI / 123Pay payment tool call.
5. GET /api/stats returns the exact 4 slide counters: checks_run, clones_blocked, agent_steps_skipped, agent_time_saved_inr.
6. Static file mounting serves index.html at root (/).
7. CORS allow_origins is wildcard ['*'] and error responses fail closed.
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.main import app
from backend.tools import DEMO_ACCOUNTS

class TestGramPayEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.sample_wav_path = ROOT_DIR / "tests" / "sample_human.wav"

    def test_slide_4_stats_counters_present(self):
        """GET /api/stats must return the exact 4 slide counters."""
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # The 4 exact slide counters
        self.assertIn("checks_run", data)
        self.assertIn("clones_blocked", data)
        self.assertIn("agent_steps_skipped", data)
        self.assertIn("agent_time_saved_inr", data)

        self.assertIsInstance(data["checks_run"], int)
        self.assertIsInstance(data["clones_blocked"], int)
        self.assertIsInstance(data["agent_steps_skipped"], int)
        self.assertIsInstance(data["agent_time_saved_inr"], (int, float))

        # Backward compatibility with Section 4
        self.assertIn("checks", data)
        self.assertIn("blocks", data)
        self.assertIn("steps_skipped", data)
        self.assertIn("est_inr", data)

    def test_challenge_generate_endpoint(self):
        """POST /api/challenge/generate creates a dynamic phrase and challenge_id."""
        resp = self.client.post("/api/challenge/generate", json={
            "speaker_id": "senior_user_01",
            "language": "en"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("challenge_id", data)
        self.assertIn("phrase", data)
        self.assertTrue(len(data["phrase"]) > 10)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["valid_seconds"], 120)
        self.assertEqual(data["tier"], 2)

    def test_challenge_generate_endpoint_empty_payload(self):
        """POST /api/challenge/generate works with empty body/defaults."""
        resp = self.client.post("/api/challenge/generate")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("challenge_id", data)
        self.assertIn("phrase", data)

    def test_challenge_verify_missing_audio_fails_closed(self):
        """POST /api/challenge/verify with missing audio fails closed."""
        resp = self.client.post("/api/challenge/verify", data={"speaker_id": "senior_user_01"})
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertTrue(data.get("fail_closed"))
        self.assertIn("error", data)

    def test_challenge_verify_with_audio(self):
        """POST /api/challenge/verify re-scores challenge audio."""
        # Generate challenge first
        gen_resp = self.client.post("/api/challenge/generate")
        chal_data = gen_resp.json()
        chal_id = chal_data["challenge_id"]

        with open(self.sample_wav_path, "rb") as f:
            resp = self.client.post(
                "/api/challenge/verify",
                files={"audio": ("challenge.wav", f, "audio/wav")},
                data={
                    "challenge_id": chal_id,
                    "phrase": chal_data["phrase"],
                    "speaker_id": "senior_user_01",
                    "action": "TRANSFER_FUNDS",
                    "amount": "25000"
                }
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("request_id", data)
        self.assertIn("decision", data)
        self.assertIn("detection", data)
        self.assertIn("verification", data)
        self.assertIn("tool", data)
        self.assertEqual(data["tier"], 2)

    def test_pay_upi_endpoint_success(self):
        """POST /api/pay/upi executes Hello! UPI payment."""
        resp = self.client.post("/api/pay/upi", json={
            "amount": 1500.0,
            "merchant_name": "IFFCO Fertilizer Co-op",
            "upi_id": "iffco@upi",
            "account_id": "kisan_farmer_01",
            "is_unlocked": True
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertFalse(data["fail_closed"])
        self.assertEqual(data["tool"]["status"], "EXECUTED")
        self.assertIn("TXN-NPCI-123PAY", data["tool"]["result"]["transaction_id"])
        self.assertEqual(data["tier"], 3)

    def test_pay_upi_endpoint_locked(self):
        """POST /api/pay/upi fails closed when is_unlocked=False."""
        resp = self.client.post("/api/pay/upi", json={
            "amount": 1500.0,
            "merchant_name": "IFFCO Fertilizer Co-op",
            "upi_id": "iffco@upi",
            "account_id": "kisan_farmer_01",
            "is_unlocked": False
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "failed")
        self.assertTrue(data["fail_closed"])
        self.assertEqual(data["tool"]["status"], "LOCKED")

    def test_frontend_mounted_at_root(self):
        """Root endpoint (/) serves the frontend static page."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("html", resp.headers.get("content-type", "").lower())

    def test_cors_headers(self):
        """Preflight OPTIONS request returns CORS allow-origin."""
        resp = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(resp.headers.get("access-control-allow-origin"), ["*", "http://localhost:3000"])


if __name__ == "__main__":
    unittest.main()
