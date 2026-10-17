"""Unit tests for the Day 2 Multilingual Contract (GramPay / BharatVoice Shield).

Verifies the 7 Day 2 Contract Requirements:
1. Test GET /api/health -> returns ok and detectif_reachable.
2. Test POST /api/enroll with lang='kn' -> returns speaker_id, lang, latency_ms.
3. Test POST /api/check with kn, hi, en:
   - Validates response shape matches CONTRACT: event_id, device, source, lang, decision, reason_key,
     detection, verification, gate_overhead_ms, challenge, transcript, intent, tool, cost, credits_remaining, badge.
4. Test Fix 1: When check returns EXTRA_CHECK, challenge_id is stored with initial audio, and
   POST /api/challenge/submit verifies challenge and executes intent for the initial audio!
5. Test POST /api/assumptions -> returns updated cost model.
6. Test GET /api/latest-state -> returns events and stats.
7. Test Fail-Closed: API error or corrupted audio returns decision in ('BLOCK', 'EXTRA_CHECK'), never PAY.

Executed using Python 3.12 unittest.
"""

import io
import os
import sys
import time
import struct
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.main import app, GLOBAL_ASSUMED_RS_PER_MIN, GLOBAL_ASSUMED_MINUTES
from backend.detectif_client import detectif_client, DetectifAPIError
from backend.multilingual_config import (
    MULTILINGUAL_CONFIG,
    normalize_lang,
    generate_challenge_words,
    get_localized_reason,
    save_pending_challenge,
    get_pending_challenge,
    remove_pending_challenge,
)
from backend.audit import (
    get_contract_stats,
    get_events_since,
    record_contract_event,
    reset_audit_logs,
)


def create_mock_wav_bytes(duration_sec: float = 5.0, sample_rate: int = 16000) -> bytes:
    """Generates valid 16-bit mono PCM WAV bytes conforming to DetectifAI requirements (>4s duration)."""
    num_samples = int(duration_sec * sample_rate)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = num_samples * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE",
        b"fmt ", 16, 1, num_channels, sample_rate,
        byte_rate, block_align, bits_per_sample,
        b"data", data_size
    )
    raw_samples = bytearray(data_size)
    return header + bytes(raw_samples)


class TestMultilingualContract(unittest.TestCase):
    """Test suite validating the 7 Day 2 API Contract requirements."""

    def setUp(self):
        self.client = TestClient(app)
        self.sample_wav = create_mock_wav_bytes(duration_sec=5.0, sample_rate=16000)
        
        # Reset cost assumptions to known baseline
        import backend.main as main_module
        main_module.GLOBAL_ASSUMED_RS_PER_MIN = 10.0
        main_module.GLOBAL_ASSUMED_MINUTES = 2.0

    # ==========================================================================
    # 1. Test GET /api/health -> returns ok and detectif_reachable
    # ==========================================================================
    def test_01_get_health_returns_ok_and_detectif_reachable(self):
        """1. Test GET /api/health -> returns ok and detectif_reachable."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Core Contract assertions
        self.assertIn("ok", data, "Health response must contain 'ok'")
        self.assertIn("detectif_reachable", data, "Health response must contain 'detectif_reachable'")
        self.assertIsInstance(data["ok"], bool, "'ok' must be a boolean")
        self.assertIsInstance(data["detectif_reachable"], bool, "'detectif_reachable' must be a boolean")
        
        # Metadata contract assertions
        self.assertIn("request_id", data)
        self.assertIn("ts", data)
        self.assertIn("detectif_details", data)
        self.assertIn("nemotron_configured", data)

    # ==========================================================================
    # 2. Test POST /api/enroll with lang='kn' -> returns speaker_id, lang, latency_ms
    # ==========================================================================
    def test_02_post_enroll_with_kannada_lang(self):
        """2. Test POST /api/enroll with lang='kn' -> returns speaker_id, lang, latency_ms."""
        mock_enroll_result = {
            "speaker_id": "kisan_farmer_01",
            "speaker_name": "kisan_farmer_01",
            "status": "enrolled",
            "latency_ms": 135
        }

        with patch.object(detectif_client, "enroll_speaker", return_value=mock_enroll_result):
            resp = self.client.post(
                "/api/enroll",
                files={"audio": ("farmer_enroll.wav", self.sample_wav, "audio/wav")},
                data={
                    "speaker_id": "kisan_farmer_01",
                    "lang": "kn"
                }
            )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Specific contract assertions
        self.assertEqual(data.get("speaker_id"), "kisan_farmer_01", "Must return exact speaker_id")
        self.assertEqual(data.get("lang"), "kn", "Must return normalized lang='kn'")
        self.assertIn("latency_ms", data, "Must return latency_ms")
        self.assertEqual(data.get("latency_ms"), 135)
        self.assertIn("credits_remaining", data)
        self.assertIn("request_id", data)

    # ==========================================================================
    # 3. Test POST /api/check with kn, hi, en -> validates response shape
    # ==========================================================================
    def test_03_post_check_contract_shapes_multilingual(self):
        """3. Test POST /api/check with kn, hi, en:
        Validates response shape matches CONTRACT:
        event_id, device, source, lang, decision, reason_key, detection, verification,
        gate_overhead_ms, challenge, transcript, intent, tool, cost, credits_remaining, badge.
        """
        languages = ["kn", "hi", "en"]
        expected_contract_keys = [
            "event_id",
            "device",
            "source",
            "lang",
            "decision",
            "reason_key",
            "detection",
            "verification",
            "gate_overhead_ms",
            "challenge",
            "transcript",
            "intent",
            "tool",
            "cost",
            "credits_remaining",
            "badge"
        ]

        for lang in languages:
            with self.subTest(language=lang):
                mock_detect = {
                    "status": "ok",
                    "verdict": "real",
                    "score": 0.06,
                    "synthetic_score": 0.06,
                    "is_synthetic": False,
                    "latency_ms": 110,
                    "raw": {"model": "Aletheia-2.0"}
                }
                mock_verify = {
                    "status": "ok",
                    "matched": True,
                    "match_score": 0.94,
                    "similarity": 0.94,
                    "latency_ms": 115,
                    "raw": {"model": "Eidos-1.0"}
                }

                with patch.object(detectif_client, "detect_deepfake", return_value=mock_detect), \
                     patch.object(detectif_client, "verify_speaker", return_value=mock_verify):

                    resp = self.client.post(
                        "/api/check",
                        files={"audio": (f"genuine_{lang}.wav", self.sample_wav, "audio/wav")},
                        data={
                            "speaker_id": f"farmer_{lang}_01",
                            "action": "TRANSFER_FUNDS",
                            "amount": 1000.0,
                            "lang": lang,
                            "device": "phone1",
                            "source": "live_mic"
                        }
                    )

                self.assertEqual(resp.status_code, 200)
                data = resp.json()

                # 1. Assert all 16 required CONTRACT keys exist
                for key in expected_contract_keys:
                    self.assertIn(key, data, f"Missing required Day 2 contract key '{key}' for lang='{lang}'")

                # 2. Validate field types and values
                self.assertTrue(isinstance(data["event_id"], str) and len(data["event_id"]) > 0)
                self.assertEqual(data["device"], "phone1")
                self.assertEqual(data["source"], "live_mic")
                self.assertEqual(data["lang"], lang)
                self.assertEqual(data["decision"], "PAY")
                self.assertEqual(data["reason_key"], "approved")

                # Nested detection dictionary
                self.assertIn("synthetic_score", data["detection"])
                self.assertIn("latency_ms", data["detection"])
                self.assertIn("raw", data["detection"])
                self.assertEqual(data["detection"]["synthetic_score"], 0.06)

                # Nested verification dictionary
                self.assertIn("match_score", data["verification"])
                self.assertIn("latency_ms", data["verification"])
                self.assertIn("raw", data["verification"])
                self.assertEqual(data["verification"]["match_score"], 0.94)

                # Gate overhead latency (isolated from network latency)
                self.assertIsInstance(data["gate_overhead_ms"], (int, float))
                self.assertGreaterEqual(data["gate_overhead_ms"], 0.0)

                # Intent & Transcript (populated on PAY)
                self.assertIsNotNone(data["transcript"])
                self.assertIn("text", data["transcript"])
                self.assertIn("english", data["transcript"])
                self.assertIsNotNone(data["intent"])
                self.assertEqual(data["intent"]["amount"], 1000.0)
                self.assertEqual(data["intent"]["payee"], "IFFCO Fertilizer Co-op")

                # Tool state
                self.assertEqual(data["tool"]["name"], "pay_upi")
                self.assertEqual(data["tool"]["status"], "EXECUTED")

                # Cost model
                self.assertEqual(data["cost"]["steps_skipped"], 0)
                self.assertEqual(data["cost"]["est_inr"], 0.0)
                self.assertIn("assumption", data["cost"])

                # Badge
                self.assertEqual(data["badge"], "VERIFIED_AGENT")

    # ==========================================================================
    # 4. Test Fix 1: EXTRA_CHECK saves initial audio, /api/challenge/submit executes it!
    # ==========================================================================
    def test_04_fix_1_extra_check_flow_and_challenge_submit_executes_initial_audio(self):
        """4. Test Fix 1: When check returns EXTRA_CHECK, challenge_id is stored with initial audio,
        and POST /api/challenge/submit verifies challenge and executes intent for the initial audio!
        """
        # Step 4A: Spoken payment command in Kannada
        initial_kannada_audio = self.sample_wav

        # Mock borderline/uncertain scores to trigger EXTRA_CHECK
        # synth = 0.54 (in [0.50, 0.62)), match = 0.88 -> Tier 2 EXTRA_CHECK
        mock_detect_borderline = {
            "status": "ok",
            "verdict": "not_sure",
            "score": 0.54,
            "synthetic_score": 0.54,
            "is_synthetic": False,
            "latency_ms": 112,
            "raw": {"status": "uncertain"}
        }
        mock_verify_matched = {
            "status": "ok",
            "matched": True,
            "match_score": 0.88,
            "similarity": 0.88,
            "latency_ms": 120,
            "raw": {"status": "matched"}
        }

        with patch.object(detectif_client, "detect_deepfake", return_value=mock_detect_borderline), \
             patch.object(detectif_client, "verify_speaker", return_value=mock_verify_matched):

            check_resp = self.client.post(
                "/api/check",
                files={"audio": ("kannada_payment.wav", initial_kannada_audio, "audio/wav")},
                data={
                    "speaker_id": "farmer_ramesh_01",
                    "action": "TRANSFER_FUNDS",
                    "amount": 1000.0,
                    "lang": "kn",
                    "device": "phone1",
                    "source": "live_mic"
                }
            )

        self.assertEqual(check_resp.status_code, 200)
        check_data = check_resp.json()

        # Decision MUST be EXTRA_CHECK
        self.assertEqual(check_data["decision"], "EXTRA_CHECK")
        self.assertEqual(check_data["reason_key"], "uncertain_challenge")
        self.assertEqual(check_data["tool"]["status"], "LOCKED")
        self.assertIsNone(check_data["transcript"], "Transcript must NOT run before challenge passes")
        self.assertIsNone(check_data["intent"], "Intent must NOT run before challenge passes")

        # Challenge payload must be returned
        challenge_block = check_data["challenge"]
        self.assertIsNotNone(challenge_block)
        challenge_id = challenge_block["challenge_id"]
        self.assertTrue(challenge_id.startswith("ch_"))
        self.assertEqual(len(challenge_block["words"]), 4)
        self.assertEqual(challenge_block["lang"], "kn")

        # CRITICAL FIX 1 ASSERTION: Verify first audio is persisted in pending challenges
        pending_record = get_pending_challenge(challenge_id)
        self.assertIsNotNone(pending_record, f"Challenge ID '{challenge_id}' must be cached in pending challenges!")
        self.assertEqual(pending_record["challenge_id"], challenge_id)
        self.assertEqual(pending_record["speaker_id"], "farmer_ramesh_01")
        self.assertEqual(pending_record["lang"], "kn")
        self.assertEqual(pending_record["audio_bytes"], initial_kannada_audio)

        # Step 4B: Farmer submits vocal response to challenge
        # Spoken challenge audio passes verification (synth=0.04, match=0.92)
        mock_detect_challenge_pass = {
            "status": "ok",
            "verdict": "real",
            "score": 0.04,
            "synthetic_score": 0.04,
            "is_synthetic": False,
            "latency_ms": 95,
            "raw": {"status": "real"}
        }
        mock_verify_challenge_pass = {
            "status": "ok",
            "matched": True,
            "match_score": 0.92,
            "similarity": 0.92,
            "latency_ms": 105,
            "raw": {"status": "verified"}
        }

        challenge_spoken_audio = create_mock_wav_bytes(duration_sec=4.5)

        with patch.object(detectif_client, "detect_deepfake", return_value=mock_detect_challenge_pass), \
             patch.object(detectif_client, "verify_speaker", return_value=mock_verify_challenge_pass):

            submit_resp = self.client.post(
                "/api/challenge/submit",
                files={"audio": ("challenge_response.wav", challenge_spoken_audio, "audio/wav")},
                data={
                    "challenge_id": challenge_id,
                    "speaker_id": "farmer_ramesh_01",
                    "response_delay_ms": 520.0
                }
            )

        self.assertEqual(submit_resp.status_code, 200)
        submit_data = submit_resp.json()

        # Decision MUST now be PAY
        self.assertEqual(submit_data["decision"], "PAY")
        self.assertEqual(submit_data["reason_key"], "approved")
        self.assertEqual(submit_data["badge"], "VERIFIED_AGENT")
        self.assertEqual(submit_data["tool"]["status"], "EXECUTED")
        self.assertEqual(submit_data["response_delay_ms"], 520.0)

        # CRITICAL FIX 1 ASSERTION: The initial payment command audio was transcribed and executed!
        self.assertIsNotNone(submit_data["transcript"])
        self.assertIn("ಇಫ್ಕೊ", submit_data["transcript"]["text"], "Must transcribe original payment command, not challenge words!")
        self.assertIn("IFFCO", submit_data["transcript"]["english"])
        self.assertIsNotNone(submit_data["intent"])
        self.assertEqual(submit_data["intent"]["amount"], 1000.0)
        self.assertEqual(submit_data["intent"]["payee"], "IFFCO Fertilizer Co-op")

        # Verify cached challenge was cleaned up after execution
        self.assertIsNone(get_pending_challenge(challenge_id), "Pending challenge cache must be cleaned up after submit!")

    # ==========================================================================
    # 5. Test POST /api/assumptions -> returns updated cost model
    # ==========================================================================
    def test_05_post_assumptions_updates_cost_model(self):
        """5. Test POST /api/assumptions -> returns updated cost model."""
        # 1. Update to custom baseline (e.g., Rs 15.0 per min, 3.0 minutes)
        resp = self.client.post(
            "/api/assumptions",
            json={
                "rs_per_min": 15.0,
                "minutes": 3.0
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("cost", data)
        self.assertEqual(data["cost"]["rs_per_min"], 15.0)
        self.assertEqual(data["cost"]["minutes"], 3.0)
        self.assertIn("est_inr", data["cost"])
        self.assertIsInstance(data["cost"]["est_inr"], (int, float))

        # 2. Verify subsequent /api/latest-state reflects this assumption
        state_resp = self.client.get("/api/latest-state")
        self.assertEqual(state_resp.status_code, 200)
        state_data = state_resp.json()
        self.assertIn("stats", state_data)

        # 3. Reset back to baseline Rs 10/min, 2 min
        reset_resp = self.client.post("/api/assumptions", json={"rs_per_min": 10.0, "minutes": 2.0})
        self.assertEqual(reset_resp.status_code, 200)
        reset_data = reset_resp.json()
        self.assertEqual(reset_data["cost"]["rs_per_min"], 10.0)
        self.assertEqual(reset_data["cost"]["minutes"], 2.0)

    # ==========================================================================
    # 6. Test GET /api/latest-state -> returns events and stats
    # ==========================================================================
    def test_06_get_latest_state_returns_events_and_stats(self):
        """6. Test GET /api/latest-state -> returns events and stats."""
        # Record a contract event to ensure data exists
        mock_event = {
            "event_id": f"req_test_state_{int(time.time()*1000)}",
            "device": "phone1",
            "source": "live_mic",
            "lang": "kn",
            "decision": "PAY",
            "reason_key": "approved",
            "detection": {"synthetic_score": 0.05, "latency_ms": 100},
            "verification": {"match_score": 0.95, "latency_ms": 110},
            "gate_overhead_ms": 0.45,
            "challenge": None,
            "transcript": {"text": "ಇಫ್ಕೊ ಗೊಬ್ಬರ", "english": "IFFCO Fertilizer"},
            "intent": {"amount": 1000.0, "payee": "IFFCO Fertilizer Co-op"},
            "tool": {"name": "pay_upi", "status": "EXECUTED"},
            "cost": {"steps_skipped": 0, "est_inr": 0.0},
            "credits_remaining": 1748,
            "badge": "VERIFIED_AGENT"
        }
        record_contract_event(mock_event)

        resp = self.client.get("/api/latest-state")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Check top-level contract keys
        self.assertIn("events", data)
        self.assertIn("stats", data)
        self.assertIn("credits_remaining", data)
        self.assertIsInstance(data["events"], list)
        self.assertIsInstance(data["stats"], dict)

        # Check Slide 4 official live demo counters
        stats = data["stats"]
        for stat_key in ["checks", "pay", "extra", "block", "steps_skipped", "est_inr"]:
            self.assertIn(stat_key, stats, f"Missing stat field '{stat_key}' in /api/latest-state response")

        self.assertIsInstance(stats["checks"], int)
        self.assertIsInstance(stats["pay"], int)
        self.assertIsInstance(stats["extra"], int)
        self.assertIsInstance(stats["block"], int)
        self.assertIsInstance(stats["steps_skipped"], int)
        self.assertIsInstance(stats["est_inr"], (int, float))

        # Check event structure if events exist
        if len(data["events"]) > 0:
            ev = data["events"][0]
            self.assertIn("event_id", ev)
            self.assertIn("device", ev)
            self.assertIn("source", ev)
            self.assertIn("lang", ev)
            self.assertIn("decision", ev)

    # ==========================================================================
    # 7. Test Fail-Closed: API error or corrupted audio returns decision in
    #    ('BLOCK', 'EXTRA_CHECK'), never PAY.
    # ==========================================================================
    def test_07_fail_closed_api_error_or_corrupted_audio_never_pay(self):
        """7. Test Fail-Closed: API error or corrupted audio returns decision in
        ('BLOCK', 'EXTRA_CHECK'), never PAY.
        """
        # Case A: DetectifAI API error (HTTP 502 / Upstream connection error)
        with patch.object(detectif_client, "detect_deepfake", side_effect=DetectifAPIError("Platform connection timed out")):
            resp_err = self.client.post(
                "/api/check",
                files={"audio": ("test.wav", self.sample_wav, "audio/wav")},
                data={"speaker_id": "farmer_ramesh_01", "lang": "kn"}
            )

        self.assertEqual(resp_err.status_code, 200)
        err_data = resp_err.json()

        # Decision MUST be in ('BLOCK', 'EXTRA_CHECK'), NEVER 'PAY' or 'APPROVE'
        self.assertIn(err_data["decision"], ["BLOCK", "EXTRA_CHECK"])
        self.assertNotIn(err_data["decision"], ["PAY", "APPROVE"])
        self.assertEqual(err_data["reason_key"], "api_error")
        self.assertEqual(err_data["tool"]["status"], "LOCKED")
        self.assertTrue(err_data.get("fail_closed"), "Must explicitly declare fail_closed: True")
        self.assertIsNone(err_data["transcript"], "Never process transcript on API error")
        self.assertIsNone(err_data["intent"], "Never process financial intent on API error")

        # Case B: Unconfigured DetectifAI Key (Platform key missing)
        with patch.object(detectif_client, "is_configured", return_value=False):
            resp_unconf = self.client.post(
                "/api/check",
                files={"audio": ("test.wav", self.sample_wav, "audio/wav")},
                data={"speaker_id": "farmer_ramesh_01", "lang": "hi"}
            )
        self.assertEqual(resp_unconf.status_code, 200)
        unconf_data = resp_unconf.json()

        self.assertIn(unconf_data["decision"], ["BLOCK", "EXTRA_CHECK"])
        self.assertNotIn(unconf_data["decision"], ["PAY", "APPROVE"])
        self.assertEqual(unconf_data["tool"]["status"], "LOCKED")
        self.assertTrue(unconf_data.get("fail_closed"))

        # Case C: Severely corrupted audio buffer (< 44 bytes or empty)
        resp_corrupt = self.client.post(
            "/api/check",
            files={"audio": ("corrupt.wav", b"RIFF_TOO_SHORT", "audio/wav")},
            data={"speaker_id": "farmer_ramesh_01", "lang": "en"}
        )
        # Returns 400 Bad Request with fail_closed: True, or fail-closed BLOCK envelope
        if resp_corrupt.status_code == 400:
            corrupt_data = resp_corrupt.json()
            self.assertTrue(corrupt_data.get("fail_closed"), "Corrupt audio must fail closed with True")
            self.assertNotIn("PAY", str(corrupt_data))
        else:
            corrupt_data = resp_corrupt.json()
            self.assertIn(corrupt_data["decision"], ["BLOCK", "EXTRA_CHECK"])
            self.assertNotIn(corrupt_data["decision"], ["PAY", "APPROVE"])
            self.assertEqual(corrupt_data["tool"]["status"], "LOCKED")


if __name__ == "__main__":
    unittest.main()
