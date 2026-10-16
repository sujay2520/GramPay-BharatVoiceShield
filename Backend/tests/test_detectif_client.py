"""Unit Test Suite for Hardened DetectifClient (OpenAPI 3.1.0 Specification).
Verifies all 6 requirements:
1. Base URL: https://platform.detectif.ai/v1 and smart path normalization
2. Deepfake: POST /v1/deepfake/detect with multipart 'file', Idempotency-Key, parses result.verdict, result.score, result.threshold (0.62), result.is_synthetic
3. Speaker Enroll: POST /v1/speakers/enroll with multipart 'file' + form fields 'speaker_id' and 'display_name'
4. Speaker Verify: POST /v1/speakers/verify with multipart 'file' + form field 'speaker_id' + optional 'detect_deepfake=true', parses result.decision, result.similarity, result.threshold (0.53)
5. Health/Credits: GET /v1/health and GET /v1/credits
6. Strict Rule 5.4: Zero mock scores, deterministic fail-closed on any error or missing field
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.detectif_client import DetectifClient, DetectifAPIError


class TestDetectifClient(unittest.TestCase):
    def setUp(self):
        self.live_key = "dtf_live_test_secret_key_12345"
        self.client = DetectifClient(
            api_key=self.live_key,
            base_url="https://platform.detectif.ai/v1",
            timeout=5.0,
        )
        self.dummy_audio = b"RIFF....WAVEfmt ...."

    # ==========================================================================
    # 1. Base URL Tests
    # ==========================================================================
    def test_base_url_default_and_resolution(self):
        """Verifies Base URL defaults to https://platform.detectif.ai/v1 and builds URLs correctly."""
        # Default instance
        c1 = DetectifClient(api_key=self.live_key)
        self.assertEqual(c1.base_url, "https://platform.detectif.ai/v1")
        self.assertEqual(c1._url("/deepfake/detect"), "https://platform.detectif.ai/v1/deepfake/detect")
        self.assertEqual(c1._url("deepfake/detect"), "https://platform.detectif.ai/v1/deepfake/detect")
        self.assertEqual(c1._url("/v1/deepfake/detect"), "https://platform.detectif.ai/v1/deepfake/detect")
        self.assertEqual(c1._url("/health"), "https://platform.detectif.ai/v1/health")
        self.assertEqual(c1._url("/credits"), "https://platform.detectif.ai/v1/credits")

        # Instance initialized with base without /v1
        c2 = DetectifClient(api_key=self.live_key, base_url="https://platform.detectif.ai")
        self.assertEqual(c2._url("/deepfake/detect"), "https://platform.detectif.ai/v1/deepfake/detect")
        self.assertEqual(c2._url("/v1/deepfake/detect"), "https://platform.detectif.ai/v1/deepfake/detect")
        self.assertEqual(c2._url("/speakers/verify"), "https://platform.detectif.ai/v1/speakers/verify")

    # ==========================================================================
    # 2. Deepfake Detection (POST /v1/deepfake/detect)
    # ==========================================================================
    @patch("requests.post")
    def test_deepfake_detect_real_human(self, mock_post):
        """POST /v1/deepfake/detect parses result.verdict='real', score=0.0731, threshold=0.62, is_synthetic=False."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"X-Request-Id": "req_8f14e45fceea167a5a36dedd"}
        mock_resp.json.return_value = {
            "request_id": "req_8f14e45fceea167a5a36dedd",
            "operation_id": "op_6f1ed002ab5595859014ebf0951522d9",
            "object": "deepfake.detection",
            "model": {"name": "aletheia-wavlm", "version": "wavlm-distill-v2"},
            "latency_ms": 58.3,
            "idempotent_replay": False,
            "result": {
                "threshold": 0.62,
                "score_semantics": "Higher means more likely AI-generated.",
                "verdict": "real",
                "label": "genuine",
                "is_synthetic": False,
                "decided_by": "main_model",
                "score": 0.0731,
                "duration_seconds": 6.4,
                "segments": [{"start": 0.0, "end": 4.0, "score": 0.061}],
            },
            "credits": {"charged": 50, "balance": 4950},
        }
        mock_post.return_value = mock_resp

        res = self.client.detect_deepfake(self.dummy_audio, filename="human.wav", idempotency_key="test-key-1")

        # Verify request parameters
        self.assertEqual(mock_post.call_count, 1)
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://platform.detectif.ai/v1/deepfake/detect")
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {self.live_key}")
        self.assertEqual(kwargs["headers"]["Idempotency-Key"], "test-key-1")
        self.assertIn("file", kwargs["files"])
        self.assertNotIn("checks", kwargs.get("data", {}))

        # Verify parsed fields per OpenAPI 3.1.0
        self.assertEqual(res["verdict"], "real")
        self.assertEqual(res["score"], 0.0731)
        self.assertEqual(res["synthetic_score"], 0.0731)
        self.assertEqual(res["threshold"], 0.62)
        self.assertFalse(res["is_synthetic"])
        self.assertEqual(res["operation_id"], "op_6f1ed002ab5595859014ebf0951522d9")
        self.assertEqual(res["request_id"], "req_8f14e45fceea167a5a36dedd")

    @patch("requests.post")
    def test_deepfake_detect_fake_clone(self, mock_post):
        """POST /v1/deepfake/detect parses result.verdict='fake', score=0.8127, threshold=0.62, is_synthetic=True."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"X-Request-Id": "req_fake_123"}
        mock_resp.json.return_value = {
            "request_id": "req_fake_123",
            "operation_id": "op_fake_456",
            "object": "deepfake.detection",
            "latency_ms": 120.0,
            "idempotent_replay": False,
            "result": {
                "threshold": 0.62,
                "verdict": "fake",
                "label": "synthetic",
                "is_synthetic": True,
                "decided_by": "second_stage",
                "score": 0.8127,
                "duration_seconds": 9.1,
                "segments": [{"start": 0.0, "end": 4.0, "score": 0.79}],
            },
            "credits": {"charged": 50, "balance": 4900},
        }
        mock_post.return_value = mock_resp

        res = self.client.detect_deepfake(self.dummy_audio)

        self.assertEqual(res["verdict"], "fake")
        self.assertEqual(res["score"], 0.8127)
        self.assertEqual(res["threshold"], 0.62)
        self.assertTrue(res["is_synthetic"])
        self.assertTrue(res["synthetic_score"] >= 0.50)

    @patch("requests.post")
    def test_deepfake_detect_not_sure(self, mock_post):
        """POST /v1/deepfake/detect parses result.verdict='not_sure', score=0.9813, threshold=0.62, is_synthetic=False."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"X-Request-Id": "req_uncertain"}
        mock_resp.json.return_value = {
            "request_id": "req_uncertain",
            "operation_id": "op_uncertain",
            "object": "deepfake.detection",
            "result": {
                "threshold": 0.62,
                "verdict": "not_sure",
                "label": "uncertain",
                "is_synthetic": False,
                "decided_by": "language_threshold",
                "score": 0.9813,
                "duration_seconds": 5.2,
                "segments": [],
            },
        }
        mock_post.return_value = mock_resp

        res = self.client.detect_deepfake(self.dummy_audio)

        self.assertEqual(res["verdict"], "not_sure")
        self.assertEqual(res["score"], 0.9813)
        self.assertEqual(res["threshold"], 0.62)
        self.assertFalse(res["is_synthetic"])

    # ==========================================================================
    # 3. Speaker Enrollment (POST /v1/speakers/enroll)
    # ==========================================================================
    @patch("requests.post")
    def test_speaker_enroll(self, mock_post):
        """POST /v1/speakers/enroll sends multipart 'file' + form fields 'speaker_id' and 'display_name'."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"X-Request-Id": "req_enroll_1"}
        mock_resp.json.return_value = {
            "request_id": "req_enroll_1",
            "operation_id": "op_enroll_1",
            "object": "speaker.enrollment",
            "speaker": {
                "speaker_id": "customer-4711",
                "display_name": "Ada Lovelace",
                "samples": 1,
                "created_at": "2026-10-13T09:30:00Z",
                "updated_at": "2026-10-13T09:30:00Z",
            },
            "quality": {"speech_seconds": 17.9, "duration_seconds": 19.2},
            "model": {"name": "eidos-redimnet2", "version": "redimnet2-b2"},
            "credits": {"charged": 50, "balance": 4900},
            "latency_ms": 388.1,
            "idempotent_replay": False,
        }
        mock_post.return_value = mock_resp

        res = self.client.enroll_speaker(
            audio_bytes=self.dummy_audio,
            speaker_id="customer-4711",
            display_name="Ada Lovelace",
            filename="ada.wav",
        )

        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://platform.detectif.ai/v1/speakers/enroll")
        self.assertIn("file", kwargs["files"])
        self.assertEqual(kwargs["data"]["speaker_id"], "customer-4711")
        self.assertEqual(kwargs["data"]["display_name"], "Ada Lovelace")

        self.assertEqual(res["speaker_id"], "customer-4711")
        self.assertEqual(res["display_name"], "Ada Lovelace")
        self.assertEqual(res["samples"], 1)
        self.assertTrue(res["enrolled"])
        self.assertEqual(res["quality"]["speech_seconds"], 17.9)

    # ==========================================================================
    # 4. Speaker Verification (POST /v1/speakers/verify)
    # ==========================================================================
    @patch("requests.post")
    def test_speaker_verify_match(self, mock_post):
        """POST /v1/speakers/verify parses result.decision='match', similarity=0.7412, threshold=0.53."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"X-Request-Id": "req_ver_1"}
        mock_resp.json.return_value = {
            "request_id": "req_ver_1",
            "operation_id": "op_ver_1",
            "object": "speaker.verification",
            "speaker_id": "customer-4711",
            "result": {
                "decision": "match",
                "similarity": 0.7412,
                "threshold": 0.53,
                "similarity_semantics": "Higher means more alike.",
                "duration_seconds": 4.1,
            },
            "deepfake": None,
            "credits": {"charged": 50, "balance": 4850},
            "latency_ms": 301.5,
            "idempotent_replay": False,
        }
        mock_post.return_value = mock_resp

        res = self.client.verify_speaker(
            audio_bytes=self.dummy_audio,
            speaker_id="customer-4711",
            detect_deepfake=False,
        )

        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://platform.detectif.ai/v1/speakers/verify")
        self.assertIn("file", kwargs["files"])
        self.assertEqual(kwargs["data"]["speaker_id"], "customer-4711")
        self.assertNotIn("detect_deepfake", kwargs["data"])

        self.assertEqual(res["decision"], "match")
        self.assertEqual(res["similarity"], 0.7412)
        self.assertEqual(res["match_score"], 0.7412)
        self.assertEqual(res["threshold"], 0.53)
        self.assertTrue(res["matched"])

    @patch("requests.post")
    def test_speaker_verify_no_match_with_deepfake(self, mock_post):
        """POST /v1/speakers/verify with detect_deepfake=true parses decision='no_match' and embedded deepfake."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"X-Request-Id": "req_ver_2"}
        mock_resp.json.return_value = {
            "request_id": "req_ver_2",
            "operation_id": "op_ver_2",
            "object": "speaker.verification",
            "speaker_id": "customer-4711",
            "result": {
                "decision": "no_match",
                "similarity": 0.1245,
                "threshold": 0.53,
                "duration_seconds": 4.5,
            },
            "deepfake": {
                "verdict": "fake",
                "label": "synthetic",
                "is_synthetic": True,
                "score": 0.892,
                "threshold": 0.62,
            },
        }
        mock_post.return_value = mock_resp

        res = self.client.verify_speaker(
            audio_bytes=self.dummy_audio,
            speaker_id="customer-4711",
            detect_deepfake=True,
        )

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["detect_deepfake"], "true")

        self.assertEqual(res["decision"], "no_match")
        self.assertEqual(res["similarity"], 0.1245)
        self.assertEqual(res["threshold"], 0.53)
        self.assertFalse(res["matched"])
        self.assertIsNotNone(res["deepfake"])
        self.assertEqual(res["deepfake"]["verdict"], "fake")

    # ==========================================================================
    # 5. Health & Credits (GET /v1/health, GET /v1/credits)
    # ==========================================================================
    @patch("requests.get")
    def test_get_health_endpoint(self, mock_get):
        """GET /v1/health returns status, version, database, inference."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "request_id": "req_health_1",
            "status": "ok",
            "version": "1.0.0",
            "database": "ok",
            "inference": "ok",
        }
        mock_get.return_value = mock_resp

        res = self.client.get_health()

        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "https://platform.detectif.ai/v1/health")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["inference"], "ok")

    @patch("requests.get")
    def test_check_health_wrapper(self, mock_get):
        """check_health() evaluates health and reports reachability."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "request_id": "req_health_2",
            "status": "ok",
            "version": "1.0.0",
            "database": "ok",
            "inference": "ok",
        }
        mock_get.return_value = mock_resp

        reachable, details = self.client.check_health()
        self.assertTrue(reachable)
        self.assertTrue(details["reachable"])
        self.assertEqual(details["status"], "ok")

    @patch("requests.get")
    def test_get_credits_endpoint(self, mock_get):
        """GET /v1/credits returns account plan and available credits."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "request_id": "req_credits_1",
            "object": "credits",
            "plan": "free",
            "unlimited": False,
            "available": 4950,
            "reserved": 50,
            "price_per_operation": 50,
        }
        mock_get.return_value = mock_resp

        res = self.client.get_credits()

        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], "https://platform.detectif.ai/v1/credits")
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {self.live_key}")
        self.assertEqual(res["plan"], "free")
        self.assertFalse(res["unlimited"])
        self.assertEqual(res["available"], 4950)
        self.assertEqual(res["price_per_operation"], 50)

    # ==========================================================================
    # 6. Strict Rule 5.4: Zero Mock Scores & Deterministic Fail-Closed
    # ==========================================================================
    def test_rule_5_4_unconfigured_fails_closed(self):
        """Rule 5.4: Unconfigured client must fail closed and never return fake mock scores."""
        unconfigured = DetectifClient(api_key="your_detectifai_api_key_here")
        self.assertFalse(unconfigured.is_configured())

        reachable, details = unconfigured.check_health()
        self.assertFalse(reachable)
        self.assertFalse(details["reachable"])
        self.assertIn("reason", details)

        with self.assertRaises(DetectifAPIError):
            unconfigured.detect_deepfake(self.dummy_audio)

        with self.assertRaises(DetectifAPIError):
            unconfigured.enroll_speaker(self.dummy_audio, "senior_user_01")

        with self.assertRaises(DetectifAPIError):
            unconfigured.verify_speaker(self.dummy_audio, "senior_user_01")

        with self.assertRaises(DetectifAPIError):
            unconfigured.get_credits()

    @patch("requests.post")
    def test_rule_5_4_api_400_invalid_speaker_id_fails_closed(self, mock_post):
        """Rule 5.4: HTTP 400 invalid_speaker_id is parsed and raises DetectifAPIError."""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = '{"error":{"type":"invalid_request","code":"invalid_speaker_id","message":"Invalid speaker_id","param":"speaker_id"},"request_id":"req_err_400"}'
        mock_resp.json.return_value = {
            "error": {
                "type": "invalid_request",
                "code": "invalid_speaker_id",
                "message": "Invalid speaker_id",
                "param": "speaker_id",
            },
            "request_id": "req_err_400",
        }
        mock_resp.headers = {"X-Request-Id": "req_err_400"}
        mock_post.return_value = mock_resp

        with self.assertRaises(DetectifAPIError) as ctx:
            self.client.verify_speaker(self.dummy_audio, "bad_speaker")

        err = ctx.exception
        self.assertEqual(err.status_code, 400)
        self.assertEqual(err.error_code, "invalid_speaker_id")
        self.assertEqual(err.request_id, "req_err_400")

    @patch("requests.post")
    def test_rule_5_4_missing_score_fails_closed_no_mocking(self, mock_post):
        """Rule 5.4: Response missing both score and verdict must raise DetectifAPIError without mocking."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"result": {}}'
        mock_resp.json.return_value = {"result": {}}
        mock_post.return_value = mock_resp

        with self.assertRaises(DetectifAPIError):
            self.client.detect_deepfake(self.dummy_audio)

    @patch("requests.post")
    def test_rule_5_4_idempotent_retry_on_503(self, mock_post):
        """Rule 5.4 & Retries: 503 retry re-uses exact same Idempotency-Key header."""
        resp_503 = MagicMock()
        resp_503.status_code = 503
        resp_503.text = '{"error":{"type":"overloaded","code":"server_busy","message":"Service busy"}}'
        resp_503.json.return_value = {"error": {"type": "overloaded", "code": "server_busy", "message": "Service busy"}}

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "request_id": "req_retry_ok",
            "operation_id": "op_retry_ok",
            "object": "deepfake.detection",
            "idempotent_replay": True,
            "result": {
                "verdict": "real",
                "score": 0.05,
                "threshold": 0.62,
                "is_synthetic": False,
            },
        }

        mock_post.side_effect = [resp_503, resp_200]

        res = self.client.detect_deepfake(self.dummy_audio, idempotency_key="my-stable-idem-key")

        self.assertEqual(mock_post.call_count, 2)
        key1 = mock_post.call_args_list[0][1]["headers"]["Idempotency-Key"]
        key2 = mock_post.call_args_list[1][1]["headers"]["Idempotency-Key"]
        self.assertEqual(key1, "my-stable-idem-key")
        self.assertEqual(key2, "my-stable-idem-key")
        self.assertEqual(res["verdict"], "real")
        self.assertTrue(res["idempotent_replay"])


if __name__ == "__main__":
    unittest.main()
