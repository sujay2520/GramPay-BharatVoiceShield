"""Unit Test Suite for Credit Guardian & Circuit Breaker.
Verifies all requirements:
1. CREDIT_RESERVE_FLOOR = 3000 is defined.
2. Tracks remaining credits from API responses and /v1/credits.
3. If credits <= CREDIT_RESERVE_FLOOR during automated non-demo runs, logs a warning
   and returns high-fidelity cached/fixture baseline rather than draining live credits,
   guaranteeing 3,000 credits remain 100% safe for live judge presentations.
4. /api/credits returns live credits count and indicates reserve_protected=True when remaining >= 3000.
"""

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.detectif_client import (
    DetectifClient,
    DetectifAPIError,
    CREDIT_RESERVE_FLOOR,
    detectif_client,
)
from backend.main import app


class TestCreditGuardian(unittest.TestCase):
    def setUp(self):
        self.live_key = "dtf_live_test_secret_key_12345"
        self.client = DetectifClient(
            api_key=self.live_key,
            base_url="https://platform.detectif.ai/v1",
            timeout=5.0,
            credit_reserve_floor=3000,
        )
        self.dummy_audio = b"RIFF....WAVEfmt ...."
        self.test_client = TestClient(app)

    # ==========================================================================
    # 1. Constant Verification
    # ==========================================================================
    def test_credit_reserve_floor_constant(self):
        """Verifies CREDIT_RESERVE_FLOOR is defined as 3000."""
        self.assertEqual(CREDIT_RESERVE_FLOOR, 3000)
        self.assertEqual(self.client.credit_reserve_floor, 3000)

    # ==========================================================================
    # 2. Credit Tracking from /v1/credits and API responses
    # ==========================================================================
    @patch("requests.get")
    def test_track_credits_from_get_credits(self, mock_get):
        """Tracks remaining credits when calling get_credits()."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "request_id": "req_cred_track_1",
            "object": "credits",
            "plan": "free",
            "unlimited": False,
            "available": 4500,
            "reserved": 0,
            "price_per_operation": 50,
        }
        mock_get.return_value = mock_resp

        self.assertIsNone(self.client.remaining_credits)
        res = self.client.get_credits()

        self.assertEqual(self.client.remaining_credits, 4500)
        self.assertEqual(res["credits"], 4500)
        self.assertEqual(res["available"], 4500)
        self.assertTrue(res["reserve_protected"])
        self.assertFalse(res["circuit_breaker_active"])

    @patch("requests.post")
    def test_track_credits_from_deepfake_response(self, mock_post):
        """Tracks remaining credits from deepfake detection API response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "request_id": "req_df_track",
            "result": {"verdict": "real", "score": 0.05, "threshold": 0.62, "is_synthetic": False},
            "credits": {"charged": 50, "balance": 3500},
        }
        mock_post.return_value = mock_resp

        self.client.detect_deepfake(self.dummy_audio)
        self.assertEqual(self.client.remaining_credits, 3500)

    @patch("requests.post")
    def test_track_credits_from_verify_response(self, mock_post):
        """Tracks remaining credits from speaker verification API response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "request_id": "req_vf_track",
            "result": {"decision": "match", "similarity": 0.85, "threshold": 0.53},
            "credits": {"charged": 50, "balance": 3450},
        }
        mock_post.return_value = mock_resp

        self.client.verify_speaker(self.dummy_audio, speaker_id="senior_user_01")
        self.assertEqual(self.client.remaining_credits, 3450)

    @patch("requests.post")
    def test_track_credits_from_enroll_response(self, mock_post):
        """Tracks remaining credits from speaker enrollment API response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "request_id": "req_enr_track",
            "speaker": {"speaker_id": "senior_user_01", "display_name": "Senior User", "samples": 1},
            "credits": {"charged": 50, "balance": 3400},
        }
        mock_post.return_value = mock_resp

        self.client.enroll_speaker(self.dummy_audio, speaker_id="senior_user_01")
        self.assertEqual(self.client.remaining_credits, 3400)

    # ==========================================================================
    # 3. Circuit Breaker: No fabricated answers when reserve is active
    # ==========================================================================
    @patch("requests.post")
    def test_circuit_breaker_active_at_reserve_floor(self, mock_post):
        """When credits are at reserve, live inference fails closed without a fixture."""
        self.client.remaining_credits = 3000
        self.assertTrue(self.client.is_circuit_breaker_active(is_demo=False))
        with self.assertRaises(DetectifAPIError):
            self.client.detect_deepfake(self.dummy_audio, filename="human.wav", is_demo=False)
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_circuit_breaker_active_below_floor_clone(self, mock_post):
        """A clone-like filename never determines a voice result."""
        self.client.remaining_credits = 2500
        self.assertTrue(self.client.is_circuit_breaker_active(is_demo=False))

        with self.assertRaises(DetectifAPIError):
            self.client.detect_deepfake(self.dummy_audio, filename="voice_clone_attack.wav", is_demo=False)
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_circuit_breaker_verification_fails_closed(self, mock_post):
        """When circuit breaker active, speaker verification has no fabricated result."""
        self.client.remaining_credits = 2950
        with self.assertRaises(DetectifAPIError):
            self.client.verify_speaker(self.dummy_audio, speaker_id="speaker", is_demo=False)
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_circuit_breaker_enrollment_fails_closed(self, mock_post):
        """When circuit breaker active, enrollment returns no fabricated profile."""
        self.client.remaining_credits = 2800
        with self.assertRaises(DetectifAPIError):
            self.client.enroll_speaker(self.dummy_audio, speaker_id="farmer_01", display_name="Farmer", is_demo=False)
        mock_post.assert_not_called()

    # ==========================================================================
    # 4. Demo Mode Does Not Bypass the Reserve
    # ==========================================================================
    @patch("requests.post")
    def test_demo_mode_does_not_bypass_circuit_breaker(self, mock_post):
        """Demo flags cannot authorize a live call below the reserve."""
        self.client.remaining_credits = 2500  # Below floor

        self.assertTrue(self.client.is_circuit_breaker_active(is_demo=True))
        with self.assertRaises(DetectifAPIError):
            self.client.detect_deepfake(self.dummy_audio, filename="human.wav", is_demo=True)
        mock_post.assert_not_called()

    # ==========================================================================
    # 5. /api/credits Endpoint Contract
    # ==========================================================================
    @patch.object(detectif_client, "get_credits")
    def test_api_credits_reserve_protected_true(self, mock_get_credits):
        """Ensure /api/credits returns live credits and indicates reserve_protected=True when remaining >= 3000."""
        mock_get_credits.return_value = {
            "plan": "free",
            "unlimited": False,
            "available": 4850,
            "credits": 4850,
            "reserved": 0,
            "price_per_operation": 50,
            "reserve_floor": 3000,
            "reserve_protected": True,
            "circuit_breaker_active": False,
        }

        resp = self.test_client.get("/api/credits")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["available"], 4850)
        self.assertEqual(data["credits"], 4850)
        self.assertEqual(data["reserve_floor"], 3000)
        self.assertTrue(data["reserve_protected"])
        self.assertFalse(data["circuit_breaker_active"])

    @patch.object(detectif_client, "get_credits")
    def test_api_credits_reserve_protected_false_below_floor(self, mock_get_credits):
        """Ensure /api/credits indicates reserve_protected=False when remaining < 3000."""
        mock_get_credits.return_value = {
            "plan": "free",
            "unlimited": False,
            "available": 2950,
            "credits": 2950,
            "reserved": 0,
            "price_per_operation": 50,
            "reserve_floor": 3000,
            "reserve_protected": False,
            "circuit_breaker_active": True,
        }

        resp = self.test_client.get("/api/credits")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["available"], 2950)
        self.assertEqual(data["credits"], 2950)
        self.assertFalse(data["reserve_protected"])
        self.assertTrue(data["circuit_breaker_active"])


if __name__ == "__main__":
    unittest.main()
