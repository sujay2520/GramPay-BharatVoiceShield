"""Comprehensive Edge Case Test Suite for UnClone Gate Backend.

Thoroughly verifies:
1. Corrupt audio headers and malformed WAV payloads
2. 0-byte audio and truncated files (< 44 bytes)
3. Expired JWT credentials and invalid expiry timestamps
4. Invalid cryptographic signatures, tampered payloads, and malformed tokens
5. Token single-use replay attacks and missing JTI tracking
6. Boundary score conditions in gate.py (exact threshold cutoffs & out-of-bounds scores)
7. Invalid, empty, and unauthorized actions across gate, tools, and credential scopes
"""

import io
import os
import sys
import time
import uuid
import struct
import unittest
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import jwt
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    MATCH_HIGH,
    MATCH_LOW,
    SYNTH_HIGH,
    SYNTH_LOW
)
from backend.audio_prep import (
    inspect_wav_header,
    prepare_audio_for_detectif,
    AudioValidationError
)
from backend.credentials import credential_service
from backend.audit import record_used_credential, get_telemetry_stats, log_audit_event
from backend.gate import evaluate_gate
from backend.tools import BankingTools, DEMO_ACCOUNTS


def create_minimal_wav_bytes(sample_rate=16000, num_channels=1, bits_per_sample=16, num_samples=160):
    """Creates a minimal valid PCM WAV byte stream for testing."""
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = num_samples * block_align
    total_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        total_size,
        b"WAVE",
        b"fmt ",
        16,              # Subchunk1Size for PCM
        1,               # AudioFormat: 1 = PCM
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size
    )
    raw_samples = b"\x00" * data_size
    return header + raw_samples


class TestAudioEdgeCases(unittest.TestCase):
    """Edge cases for audio headers, empty audio, truncated streams, and malformed payloads."""

    def setUp(self):
        self.client = TestClient(app)

    # --------------------------------------------------------------------------
    # 1. 0-byte Audio Tests
    # --------------------------------------------------------------------------
    def test_0_byte_audio_in_prepare_audio_raises_error(self):
        """0-byte buffer must raise AudioValidationError immediately."""
        with self.assertRaises(AudioValidationError) as ctx:
            prepare_audio_for_detectif(b"", "empty.wav")
        self.assertIn("Empty audio buffer", str(ctx.exception))

    def test_0_byte_audio_in_inspect_wav_header_raises_error(self):
        """0-byte buffer must raise AudioValidationError in inspect_wav_header."""
        with self.assertRaises(AudioValidationError) as ctx:
            inspect_wav_header(b"")
        self.assertIn("too small", str(ctx.exception))

    def test_api_check_0_byte_audio_returns_400_fail_closed(self):
        """POST /api/check with 0-byte audio must return HTTP 400 Bad Request with fail_closed=True."""
        resp = self.client.post(
            "/api/check",
            files={"audio": ("empty.wav", b"", "audio/wav")},
            data={"speaker_id": "senior_user_01", "action": "TRANSFER_FUNDS", "amount": "10000"}
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertTrue(data.get("fail_closed"))
        self.assertIn("Empty audio buffer", data.get("error", ""))

    def test_api_enroll_0_byte_audio_returns_400_fail_closed(self):
        """POST /api/enroll with 0-byte audio must return HTTP 400 Bad Request."""
        resp = self.client.post(
            "/api/enroll",
            files={"audio": ("empty.wav", b"", "audio/wav")},
            data={"name": "Test User"}
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertTrue(data.get("fail_closed"))
        self.assertIn("Empty audio buffer", data.get("error", ""))

    def test_api_agent_turn_0_byte_audio_returns_400_fail_closed(self):
        """POST /api/agent/turn with 0-byte audio must return HTTP 400 Bad Request."""
        resp = self.client.post(
            "/api/agent/turn",
            files={"audio": ("empty.wav", b"", "audio/wav")},
            data={"speaker_id": "senior_user_01", "user_text_hint": "Check balance"}
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertTrue(data.get("fail_closed"))
        self.assertIn("Empty audio buffer", data.get("error", ""))

    # --------------------------------------------------------------------------
    # 2. Truncated Audio (< 44 bytes) Tests
    # --------------------------------------------------------------------------
    def test_sub_44_byte_audio_raises_validation_error(self):
        """Audio payloads smaller than minimum 44-byte WAV header must raise AudioValidationError."""
        for length in [1, 10, 43]:
            truncated_bytes = b"RIFF" + b"\x00" * (length - 4) if length >= 4 else b"\x00" * length
            with self.assertRaises(AudioValidationError):
                inspect_wav_header(truncated_bytes)

    def test_api_check_truncated_audio_returns_400(self):
        """POST /api/check with truncated 20-byte audio must fail closed with 400."""
        resp = self.client.post(
            "/api/check",
            files={"audio": ("truncated.wav", b"RIFF1234WAVEfmt ", "audio/wav")},
            data={"speaker_id": "senior_user_01", "action": "TRANSFER_FUNDS"}
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertTrue(data.get("fail_closed"))

    # --------------------------------------------------------------------------
    # 3. Corrupt Audio Headers Tests
    # --------------------------------------------------------------------------
    def test_corrupt_wav_header_returns_wav_corrupt_status(self):
        """RIFF/WAVE header followed by corrupt fmt/data chunk must be flagged as 'wav-corrupt'."""
        corrupt_wav = b"RIFF" + b"\x00\x01\x00\x00" + b"WAVE" + b"\xff" * 50
        info = inspect_wav_header(corrupt_wav)
        self.assertEqual(info["format"], "wav-corrupt")
        self.assertIn("error", info)

    def test_non_wav_header_detected(self):
        """Payload >= 44 bytes that does not start with RIFF...WAVE is identified as 'non-wav'."""
        non_wav = b"OggS" + b"\x00" * 60
        info = inspect_wav_header(non_wav)
        self.assertEqual(info["format"], "non-wav")
        self.assertIsNone(info["channels"])
        self.assertIsNone(info["sample_rate"])

    def test_valid_minimal_wav_inspects_cleanly(self):
        """Synthesized minimal WAV header is parsed without error."""
        valid_wav = create_minimal_wav_bytes(sample_rate=16000, num_channels=1, num_samples=1600)
        info = inspect_wav_header(valid_wav)
        self.assertEqual(info["format"], "wav")
        self.assertEqual(info["sample_rate"], 16000)
        self.assertEqual(info["channels"], 1)
        self.assertAlmostEqual(info["duration_seconds"], 0.1, places=2)

    def test_prepare_audio_falls_back_gracefully_for_mp3_or_webm(self):
        """Non-WAV files (e.g. .mp3, .ogg) with non-WAV headers map to proper MIME type without crashing."""
        non_wav_data = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 50
        bytes_out, mime_type, filename = prepare_audio_for_detectif(non_wav_data, "user_note.mp3")
        self.assertEqual(mime_type, "audio/mpeg")
        self.assertEqual(bytes_out, non_wav_data)


class TestJwtCredentialsEdgeCases(unittest.TestCase):
    """Edge cases for agent cryptographic credentials: expiration, invalid signatures, malformed tokens."""

    def setUp(self):
        self.client = TestClient(app)

    # --------------------------------------------------------------------------
    # 1. Expired JWT Credentials
    # --------------------------------------------------------------------------
    def test_expired_jwt_credential_rejected(self):
        """Token with past expiration must be rejected with checks['expiry'] = False."""
        # Issue credential with negative validity (already expired)
        expired_token_info = credential_service.issue_credential(
            agent_id="bot_hdfc_01",
            org="HDFC Bank",
            allowed_actions=["CHECK_BALANCE"],
            validity_seconds=-10
        )
        token = expired_token_info["credential"]

        verify_result = credential_service.verify_handshake(token, required_action="CHECK_BALANCE")
        self.assertEqual(verify_result["badge"], "REJECTED")
        self.assertFalse(verify_result["checks"]["expiry"])
        self.assertTrue(verify_result["checks"]["signature"])
        self.assertIn("expired", verify_result["reason"].lower())

    def test_manually_crafted_expired_token(self):
        """Manually crafted token with exp 1 hour ago is rejected by verify_handshake."""
        past_time = int(time.time()) - 3600
        payload = {
            "iss": "UnClone-Agent-Trust-Registry",
            "sub": "rogue_expired_bot",
            "org": "Unknown Org",
            "actions": ["TRANSFER_FUNDS"],
            "limit_inr": 10000.0,
            "jti": str(uuid.uuid4()),
            "iat": past_time - 300,
            "exp": past_time
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        result = credential_service.verify_handshake(token, required_action="TRANSFER_FUNDS")
        self.assertEqual(result["badge"], "REJECTED")
        self.assertFalse(result["checks"]["expiry"])

    def test_api_verify_endpoint_with_expired_token(self):
        """POST /api/handshake/verify with expired token returns badge='REJECTED'."""
        expired_info = credential_service.issue_credential(
            agent_id="bot_sbi_02",
            org="SBI Cards",
            allowed_actions=["TRANSFER_FUNDS"],
            validity_seconds=-60
        )
        resp = self.client.post("/api/handshake/verify", json={"credential": expired_info["credential"]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["badge"], "REJECTED")
        self.assertFalse(data["checks"]["expiry"])

    # --------------------------------------------------------------------------
    # 2. Invalid Signatures & Malformed Tokens
    # --------------------------------------------------------------------------
    def test_invalid_signature_different_secret_key(self):
        """Token signed with wrong secret key is rejected immediately."""
        payload = {
            "iss": "UnClone-Agent-Trust-Registry",
            "sub": "attacker_bot",
            "org": "Fraudulent Entity",
            "actions": ["TRANSFER_FUNDS"],
            "limit_inr": 999999.0,
            "jti": str(uuid.uuid4()),
            "iat": int(time.time()),
            "exp": int(time.time()) + 300
        }
        forged_token = jwt.encode(payload, "completely_wrong_secret_key_67890", algorithm="HS256")

        result = credential_service.verify_handshake(forged_token, required_action="TRANSFER_FUNDS")
        self.assertEqual(result["badge"], "REJECTED")
        self.assertFalse(result["checks"]["signature"])
        self.assertIn("signature", result["reason"].lower())

    def test_tampered_token_payload_rejected(self):
        """Altering the payload part of a signed JWT invalidates signature."""
        valid_info = credential_service.issue_credential(
            agent_id="bot_axis_03",
            org="Axis Bank",
            allowed_actions=["CHECK_BALANCE"]
        )
        token = valid_info["credential"]
        parts = token.split(".")
        self.assertEqual(len(parts), 3)

        # Corrupt the payload part
        corrupted_payload = parts[1][:-2] + "AA"
        tampered_token = f"{parts[0]}.{corrupted_payload}.{parts[2]}"

        result = credential_service.verify_handshake(tampered_token)
        self.assertEqual(result["badge"], "REJECTED")
        self.assertFalse(result["checks"]["signature"])

    def test_garbage_token_strings_rejected(self):
        """Arbitrary non-JWT strings must be rejected cleanly without unhandled exceptions."""
        garbage_inputs = [
            "not.a.valid.jwt",
            "just_a_random_string",
            "Bearer 1234567890",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.corrupt",
            "!@#$%^&*()_+-="
        ]
        for bad_token in garbage_inputs:
            result = credential_service.verify_handshake(bad_token)
            self.assertEqual(result["badge"], "REJECTED")
            self.assertFalse(result["checks"]["signature"])

    def test_empty_or_none_credential_rejected(self):
        """Empty string or None passed as credential returns badge='REJECTED'."""
        for empty_val in ["", None]:
            result = credential_service.verify_handshake(empty_val)
            self.assertEqual(result["badge"], "REJECTED")
            self.assertIn("Missing agent credential", result["reason"])


class TestTokenReplayProtectionEdgeCases(unittest.TestCase):
    """Edge cases for single-use token replay attacks and missing identifiers."""

    def setUp(self):
        self.client = TestClient(app)

    def test_single_use_token_replay_rejected_on_second_and_third_attempt(self):
        """Token redeemed once cannot be redeemed a second or third time (Single-Use JTI)."""
        issued = credential_service.issue_credential(
            agent_id="bot_kotak_05",
            org="Kotak Mahindra Voice",
            allowed_actions=["TRANSFER_FUNDS"]
        )
        token = issued["credential"]

        # Attempt 1: Must succeed
        first_pass = credential_service.verify_handshake(token, required_action="TRANSFER_FUNDS")
        self.assertEqual(first_pass["badge"], "VERIFIED_AGENT")
        self.assertTrue(first_pass["checks"]["unused"])

        # Attempt 2: Replay attack caught!
        second_attempt = credential_service.verify_handshake(token, required_action="TRANSFER_FUNDS")
        self.assertEqual(second_attempt["badge"], "REJECTED")
        self.assertFalse(second_attempt["checks"]["unused"])
        self.assertIn("REPLAY ATTACK", second_attempt["reason"])

        # Attempt 3: Still rejected
        third_attempt = credential_service.verify_handshake(token, required_action="TRANSFER_FUNDS")
        self.assertEqual(third_attempt["badge"], "REJECTED")
        self.assertFalse(third_attempt["checks"]["unused"])

    def test_api_replay_attack_rejected(self):
        """Replay attack via POST /api/handshake/verify is rejected on the second call."""
        issue_resp = self.client.post("/api/credential/issue", json={
            "agent_id": "bot_canara_07",
            "org": "Canara Bank Support",
            "allowed_actions": ["TRANSFER_FUNDS"]
        })
        token = issue_resp.json()["credential"]

        # 1st verification
        v1 = self.client.post("/api/handshake/verify", json={"credential": token})
        self.assertEqual(v1.status_code, 200)
        self.assertEqual(v1.json()["badge"], "VERIFIED_AGENT")

        # 2nd verification (Replay)
        v2 = self.client.post("/api/handshake/verify", json={"credential": token})
        self.assertEqual(v2.status_code, 200)
        data2 = v2.json()
        self.assertEqual(data2["badge"], "REJECTED")
        self.assertIn("REPLAY ATTACK", data2["reason"])

    def test_token_missing_jti_rejected(self):
        """Token without 'jti' identifier claim is rejected to prevent un-trackable reuse."""
        now = int(time.time())
        payload_no_jti = {
            "iss": "UnClone-Agent-Trust-Registry",
            "sub": "agent_without_jti",
            "org": "Shadow Bank",
            "actions": ["TRANSFER_FUNDS"],
            "iat": now,
            "exp": now + 300
            # 'jti' is intentionally omitted
        }
        token = jwt.encode(payload_no_jti, JWT_SECRET, algorithm=JWT_ALGORITHM)
        result = credential_service.verify_handshake(token)
        self.assertEqual(result["badge"], "REJECTED")
        self.assertIn("missing unique JTI", result["reason"])

    def test_direct_record_used_credential_handles_duplicate(self):
        """Direct database call to record_used_credential returns False on duplicate JTI."""
        test_jti = f"unit_test_jti_{uuid.uuid4().hex}"
        self.assertTrue(record_used_credential(test_jti, "agent_1", "org_1"))
        self.assertFalse(record_used_credential(test_jti, "agent_1", "org_1"))


class TestGateScoreBoundaryEdgeCases(unittest.TestCase):
    """Tests all exact boundary conditions in gate.py 2x2 matrix and fail-closed paths."""

    # --------------------------------------------------------------------------
    # Boundary 1: Clone Attack (synth >= SYNTH_HIGH=0.50 and match >= MATCH_HIGH=0.85)
    # --------------------------------------------------------------------------
    def test_exact_clone_attack_thresholds(self):
        """Exact boundary values: synth == 0.50 and match == 0.85 -> BLOCK_ALERT."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_HIGH},
            verification={"match_score": MATCH_HIGH},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertGreater(res["cost"]["est_inr"], 0.0)

    def test_clone_attack_upper_extremes(self):
        """Max boundary values: synth == 1.0 and match == 1.0 -> BLOCK_ALERT."""
        res = evaluate_gate(
            detection={"synthetic_score": 1.0},
            verification={"match_score": 1.0},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertFalse(res["tool_allowed"])

    def test_clone_attack_synth_boundary_with_max_match(self):
        """synth == SYNTH_HIGH, match == 1.0 -> BLOCK_ALERT."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_HIGH},
            verification={"match_score": 1.0},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertFalse(res["tool_allowed"])

    # --------------------------------------------------------------------------
    # Boundary 2: Synthetic Impostor (synth >= SYNTH_HIGH and match < MATCH_HIGH)
    # --------------------------------------------------------------------------
    def test_synthetic_impostor_just_below_match_high(self):
        """synth == SYNTH_HIGH, match == MATCH_HIGH - 0.000001 -> BLOCK."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_HIGH},
            verification={"match_score": MATCH_HIGH - 0.000001},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)

    def test_synthetic_impostor_zero_match(self):
        """synth == 1.0, match == 0.0 -> BLOCK."""
        res = evaluate_gate(
            detection={"synthetic_score": 1.0},
            verification={"match_score": 0.0},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK")
        self.assertFalse(res["tool_allowed"])

    # --------------------------------------------------------------------------
    # Boundary 3: Authentic Enrolled User (synth < SYNTH_LOW and match >= MATCH_HIGH)
    # --------------------------------------------------------------------------
    def test_authentic_user_just_below_synth_low(self):
        """synth == SYNTH_LOW - 0.000001, match == MATCH_HIGH -> APPROVE."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_LOW - 0.000001},
            verification={"match_score": MATCH_HIGH},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "APPROVE")
        self.assertTrue(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 0)
        self.assertEqual(res["cost"]["est_inr"], 0.0)

    def test_authentic_user_zero_synth_max_match(self):
        """synth == 0.0, match == 1.0 -> APPROVE."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.0},
            verification={"match_score": 1.0},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "APPROVE")
        self.assertTrue(res["tool_allowed"])

    # --------------------------------------------------------------------------
    # Boundary 4: Real Person, Wrong Speaker (synth < SYNTH_LOW and match < MATCH_HIGH)
    # --------------------------------------------------------------------------
    def test_real_wrong_speaker_just_below_match_high(self):
        """synth == 0.0, match == MATCH_HIGH - 0.000001 -> STEP_UP."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.0},
            verification={"match_score": MATCH_HIGH - 0.000001},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertIn("two-factor", res["reason"].lower())

    def test_real_wrong_speaker_check_balance_action(self):
        """synth == 0.10, match == 0.35 with action='CHECK_BALANCE' -> STEP_UP asking for PIN."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.10},
            verification={"match_score": 0.35},
            action="CHECK_BALANCE"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertIn("4-digit pin", res["reason"].lower())

    # --------------------------------------------------------------------------
    # Boundary 5: Borderline Synthetic (SYNTH_LOW <= synth < SYNTH_HIGH)
    # --------------------------------------------------------------------------
    def test_borderline_synth_exact_lower_bound(self):
        """synth == SYNTH_LOW (exact SYNTH_LOW threshold) with match == 0.95 -> STEP_UP (inconclusive)."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_LOW},
            verification={"match_score": 0.95},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertIn("inconclusive", res["reason"].lower())

    def test_borderline_synth_just_below_synth_high(self):
        """synth == SYNTH_HIGH - 0.000001 (just below SYNTH_HIGH) with match == 0.95 -> STEP_UP."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_HIGH - 0.000001},
            verification={"match_score": 0.95},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertIn("inconclusive", res["reason"].lower())

    def test_borderline_synth_mid_range(self):
        """synth == (SYNTH_LOW + SYNTH_HIGH)/2, match == 0.50 -> STEP_UP."""
        res = evaluate_gate(
            detection={"synthetic_score": (SYNTH_LOW + SYNTH_HIGH) / 2.0},
            verification={"match_score": 0.50},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])

    # --------------------------------------------------------------------------
    # 6. Extreme & Out-of-bounds Inputs
    # --------------------------------------------------------------------------
    def test_negative_scores_handled_safely(self):
        """Negative synthetic score (< 0.20) and high match -> APPROVE."""
        res = evaluate_gate(
            detection={"synthetic_score": -0.1},
            verification={"match_score": 0.90},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "APPROVE")
        self.assertTrue(res["tool_allowed"])

    def test_scores_greater_than_one_handled_safely(self):
        """Scores > 1.0 (>= 0.50 and >= 0.85) -> BLOCK_ALERT."""
        res = evaluate_gate(
            detection={"synthetic_score": 1.5},
            verification={"match_score": 1.5},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertFalse(res["tool_allowed"])

    def test_empty_dictionaries_fallback_to_zero(self):
        """Empty dictionaries have missing telemetry -> fail closed: BLOCK for transfers, STEP_UP for balance."""
        res_transfer = evaluate_gate(
            detection={},
            verification={},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res_transfer["decision"], "BLOCK")
        self.assertFalse(res_transfer["tool_allowed"])
        self.assertTrue(res_transfer.get("fail_closed"))

        res_balance = evaluate_gate(
            detection={},
            verification={},
            action="CHECK_BALANCE"
        )
        self.assertEqual(res_balance["decision"], "STEP_UP")
        self.assertFalse(res_balance["tool_allowed"])
        self.assertTrue(res_balance.get("fail_closed"))

    def test_string_formatted_scores(self):
        """Numeric strings for scores (e.g. from JSON serialization) parse cleanly to float."""
        res = evaluate_gate(
            detection={"synthetic_score": "0.95"},
            verification={"match_score": "0.92"},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertFalse(res["tool_allowed"])

    # --------------------------------------------------------------------------
    # 7. Fail-Closed on API Error
    # --------------------------------------------------------------------------
    def test_fail_closed_on_detectif_api_error_for_transfer(self):
        """API error on TRANSFER_FUNDS must BLOCK and mark fail_closed=True."""
        res = evaluate_gate(
            detection={},
            verification={},
            action="TRANSFER_FUNDS",
            api_error="DetectifAI Service Unavailable 503"
        )
        self.assertEqual(res["decision"], "BLOCK")
        self.assertFalse(res["tool_allowed"])
        self.assertTrue(res.get("fail_closed"))

    def test_fail_closed_on_detectif_api_error_for_check_balance(self):
        """API error on CHECK_BALANCE must STEP_UP and mark fail_closed=True."""
        res = evaluate_gate(
            detection={},
            verification={},
            action="CHECK_BALANCE",
            api_error="Connection timed out"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertTrue(res.get("fail_closed"))


class TestInvalidActionsAndScopesEdgeCases(unittest.TestCase):
    """Edge cases for unauthorized actions, invalid action names, and tool locking."""

    def setUp(self):
        self.client = TestClient(app)

    # --------------------------------------------------------------------------
    # 1. Action Scope Authorization in Credentials
    # --------------------------------------------------------------------------
    def test_action_scope_mismatch_rejected(self):
        """Agent issued CHECK_BALANCE scope attempting TRANSFER_FUNDS is rejected."""
        issued = credential_service.issue_credential(
            agent_id="support_bot_01",
            org="Public Bank",
            allowed_actions=["CHECK_BALANCE"]
        )
        token = issued["credential"]

        result = credential_service.verify_handshake(token, required_action="TRANSFER_FUNDS")
        self.assertEqual(result["badge"], "REJECTED")
        self.assertFalse(result["checks"]["scope"])
        self.assertIn("Unauthorized action", result["reason"])

    def test_wildcard_all_scope_allows_any_action(self):
        """Agent issued 'ALL' scope can execute any requested action."""
        issued = credential_service.issue_credential(
            agent_id="master_agent_01",
            org="Apex Banking Core",
            allowed_actions=["ALL"]
        )
        token = issued["credential"]

        result = credential_service.verify_handshake(token, required_action="ANY_CUSTOM_ACTION")
        self.assertEqual(result["badge"], "VERIFIED_AGENT")
        self.assertTrue(result["checks"]["scope"])

    def test_empty_allowed_actions_list_rejected(self):
        """Agent issued with empty allowed_actions cannot verify handshake without scope."""
        issued = credential_service.issue_credential(
            agent_id="restricted_agent_02",
            org="Audit Agency",
            allowed_actions=[]
        )
        token = issued["credential"]

        result = credential_service.verify_handshake(token, required_action="TRANSFER_FUNDS")
        self.assertEqual(result["badge"], "REJECTED")
        self.assertFalse(result["checks"]["scope"])

    # --------------------------------------------------------------------------
    # 2. Invalid Actions in Gate Evaluation
    # --------------------------------------------------------------------------
    def test_unknown_action_in_evaluate_gate(self):
        """Arbitrary action string (e.g. 'UNRECOGNIZED_ACTION') does not crash evaluate_gate."""
        res_real = evaluate_gate(
            detection={"synthetic_score": 0.05},
            verification={"match_score": 0.95},
            action="UNRECOGNIZED_ACTION"
        )
        self.assertEqual(res_real["decision"], "APPROVE")
        self.assertTrue(res_real["tool_allowed"])

        res_wrong_speaker = evaluate_gate(
            detection={"synthetic_score": 0.05},
            verification={"match_score": 0.30},
            action="UNRECOGNIZED_ACTION"
        )
        self.assertEqual(res_wrong_speaker["decision"], "STEP_UP")
        self.assertFalse(res_wrong_speaker["tool_allowed"])

    def test_unknown_action_with_api_error_defaults_to_step_up(self):
        """API error with non-TRANSFER_FUNDS action defaults safely to STEP_UP."""
        res = evaluate_gate(
            detection={},
            verification={},
            action="UNKNOWN_LOW_RISK_ACTION",
            api_error="DetectifAI timeout"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertTrue(res.get("fail_closed"))

    # --------------------------------------------------------------------------
    # 3. Banking Tools Edge Cases & Locked State Verification
    # --------------------------------------------------------------------------
    def test_get_tool_definition_unknown_tool_locked(self):
        """Unknown tool definition request defaults to status='LOCKED'."""
        defn = BankingTools.get_tool_definition("malicious_unregistered_tool")
        self.assertEqual(defn["status"], "LOCKED")
        self.assertIsNone(defn["result"])

    def test_transfer_funds_locked_by_default(self):
        """Executing transfer_funds with is_unlocked=False returns LOCKED."""
        res = BankingTools.execute_transfer_funds(
            amount=1000.0,
            recipient="Unknown",
            from_account_id="senior_user_01",
            is_unlocked=False
        )
        self.assertEqual(res["status"], "LOCKED")
        self.assertIsNone(res["result"])
        self.assertIn("LOCKED", res["message"])

    def test_check_balance_locked_by_default(self):
        """Executing check_balance with is_unlocked=False returns LOCKED."""
        res = BankingTools.execute_check_balance(
            account_id="senior_user_01",
            is_unlocked=False
        )
        self.assertEqual(res["status"], "LOCKED")
        self.assertIsNone(res["result"])

    def test_transfer_funds_insufficient_balance(self):
        """Unlocked transfer exceeding account balance returns FAILED with INSUFFICIENT_FUNDS."""
        res = BankingTools.execute_transfer_funds(
            amount=999999999.0,
            recipient="Grandson",
            from_account_id="senior_user_01",
            is_unlocked=True
        )
        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["result"]["error"], "INSUFFICIENT_FUNDS")

    def test_check_balance_unknown_account_falls_back_to_default(self):
        """Unknown account_id safely falls back to default demo account when unlocked."""
        res = BankingTools.execute_check_balance(
            account_id="non_existent_account_xyz",
            is_unlocked=True
        )
        self.assertEqual(res["status"], "EXECUTED")
        self.assertEqual(res["result"]["holder_name"], DEMO_ACCOUNTS["default"]["name"])


class TestGramPayParametersEdgeCases(unittest.TestCase):
    """Edge cases for GramPay parameters (farmer persona, UPI 123Pay / Hello! UPI, telephony caller ID, merchant payments)."""

    def setUp(self):
        self.client = TestClient(app)
        self.sample_wav_path = ROOT_DIR / "tests" / "sample_human.wav"

    def test_grampay_phone_number_speaker_id_in_check(self):
        """Feature phone caller ID (e.g. +919876543210) passed as speaker_id to /api/check."""
        with open(self.sample_wav_path, "rb") as audio_file:
            resp = self.client.post(
                "/api/check",
                files={"audio": ("sample_human.wav", audio_file, "audio/wav")},
                data={
                    "speaker_id": "+919876543210",
                    "action": "TRANSFER_FUNDS",
                    "amount": "2500"
                }
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("request_id", data)
        self.assertIn("decision", data)
        self.assertEqual(data["tool"]["status"], "LOCKED")
        self.assertTrue(data.get("fail_closed"))

    def test_grampay_send_money_action_gate_evaluation(self):
        """evaluate_gate handles action='SEND_MONEY' across all biometric outcomes."""
        # Tier 1: Real human voice + enrolled match -> APPROVE
        res_approve = evaluate_gate(
            detection={"is_synthetic": False, "synthetic_score": 0.05},
            verification={"matched": True, "match_score": 0.92},
            action="SEND_MONEY"
        )
        self.assertEqual(res_approve["decision"], "APPROVE")
        self.assertTrue(res_approve["tool_allowed"])

        # Tier 2: Real human voice + wrong speaker -> STEP_UP
        res_step_up = evaluate_gate(
            detection={"is_synthetic": False, "synthetic_score": 0.08},
            verification={"matched": False, "match_score": 0.40},
            action="SEND_MONEY"
        )
        self.assertEqual(res_step_up["decision"], "STEP_UP")
        self.assertFalse(res_step_up["tool_allowed"])

        # Tier 3: Cloned voice -> BLOCK_ALERT
        res_block_alert = evaluate_gate(
            detection={"is_synthetic": True, "synthetic_score": 0.90},
            verification={"matched": True, "match_score": 0.94},
            action="SEND_MONEY"
        )
        self.assertEqual(res_block_alert["decision"], "BLOCK_ALERT")
        self.assertFalse(res_block_alert["tool_allowed"])

    def test_grampay_pay_merchant_zero_and_negative_amounts(self):
        """BankingTools.pay_merchant rejects zero or negative amounts with INVALID_AMOUNT error."""
        for bad_amount in [0.0, -100.0, -0.01]:
            res = BankingTools.pay_merchant(amount=bad_amount, is_unlocked=True)
            self.assertEqual(res["status"], "FAILED")
            self.assertEqual(res["result"]["error"], "INVALID_AMOUNT")
            self.assertIn("greater than zero", res["message"])

    def test_grampay_pay_merchant_exceeds_daily_limit(self):
        """BankingTools.pay_merchant rejects amounts exceeding NPCI 123Pay daily voice limit (₹50,000)."""
        res = BankingTools.pay_merchant(amount=55000.0, account_id="senior_user_01", is_unlocked=True)
        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["result"]["error"], "DAILY_LIMIT_EXCEEDED")
        self.assertIn("daily_limit_inr", res["result"])

    def test_grampay_pay_merchant_exceeds_balance(self):
        """BankingTools.pay_merchant rejects amount exceeding available Kisan account balance."""
        res = BankingTools.pay_merchant(
            amount=35000.0,
            account_id="kisan_farmer_01",
            is_unlocked=True
        )
        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["result"]["error"], "INSUFFICIENT_FUNDS")
        self.assertIn("available_balance_inr", res["result"])

    def test_grampay_pay_merchant_locked_cannot_bypass(self):
        """BankingTools.pay_merchant is strictly LOCKED when is_unlocked=False."""
        res = BankingTools.pay_merchant(
            amount=500.0,
            merchant_name="IFFCO Fertilizer Co-op",
            is_unlocked=False
        )
        self.assertEqual(res["status"], "LOCKED")
        self.assertIsNone(res["result"])
        self.assertIn("LOCKED", res["message"])

    def test_grampay_check_kisan_balance_locked_and_unlocked(self):
        """BankingTools.check_kisan_balance adheres to gate lock state."""
        locked_res = BankingTools.check_kisan_balance(account_id="kisan_farmer_01", is_unlocked=False)
        self.assertEqual(locked_res["status"], "LOCKED")
        self.assertIsNone(locked_res["result"])

        unlocked_res = BankingTools.check_kisan_balance(account_id="kisan_farmer_01", is_unlocked=True)
        self.assertEqual(unlocked_res["status"], "EXECUTED")
        self.assertIn("Ramesh Patel", unlocked_res["result"]["holder_name"])
        self.assertIn("Kisan Credit Card", unlocked_res["result"]["account_type"])

    def test_grampay_verify_pm_kisan_dbt_locked_and_unlocked(self):
        """BankingTools.verify_pm_kisan_dbt adheres to gate lock state."""
        locked_res = BankingTools.verify_pm_kisan_dbt(account_id="kisan_farmer_01", is_unlocked=False)
        self.assertEqual(locked_res["status"], "LOCKED")
        self.assertIsNone(locked_res["result"])

        unlocked_res = BankingTools.verify_pm_kisan_dbt(account_id="kisan_farmer_01", is_unlocked=True)
        self.assertEqual(unlocked_res["status"], "EXECUTED")
        self.assertEqual(unlocked_res["result"]["dbt_status"], "ACTIVE")
        self.assertEqual(unlocked_res["result"]["latest_installment"]["amount_inr"], 2000.0)

    def test_grampay_unicode_hindi_recipient(self):
        """BankingTools.pay_merchant handles unicode Hindi recipient names cleanly."""
        res = BankingTools.pay_merchant(
            amount=800.0,
            merchant_name="इफको किसान सेवा केंद्र",
            upi_id="kisan.seva@upi",
            account_id="kisan_farmer_01",
            is_unlocked=True
        )
        self.assertEqual(res["status"], "EXECUTED")
        self.assertEqual(res["result"]["merchant_name"], "इफको किसान सेवा केंद्र")
        self.assertIn("TXN-NPCI-123PAY", res["result"]["transaction_id"])

    def test_grampay_agent_credential_unauthorized_action_rejected(self):
        """GramPay agent credential restricted to voice payment actions rejects unauthorized scopes."""
        issued = credential_service.issue_credential(
            agent_id="grampay_ivr_bot_03",
            org="GramPay Voice Network",
            allowed_actions=["PAY_MERCHANT", "CHECK_BALANCE"],
            limit_inr=5000.0
        )
        token = issued["credential"]

        # Valid allowed action passes
        pass_res = credential_service.verify_handshake(token, required_action="PAY_MERCHANT")
        self.assertEqual(pass_res["badge"], "VERIFIED_AGENT")

        # Second token with different scope tested for unauthorized action
        issued2 = credential_service.issue_credential(
            agent_id="grampay_ivr_bot_04",
            org="GramPay Voice Network",
            allowed_actions=["CHECK_BALANCE"],
            limit_inr=5000.0
        )
        fail_res = credential_service.verify_handshake(issued2["credential"], required_action="TRANSFER_MILLIONS")
        self.assertEqual(fail_res["badge"], "REJECTED")
        self.assertFalse(fail_res["checks"]["scope"])


class TestThreeTierGateLogicEdgeCases(unittest.TestCase):
    """Exhaustive edge case tests for the 3-Tier Gate Logic: APPROVE, STEP_UP with active challenge, and BLOCK_ALERT."""

    # --------------------------------------------------------------------------
    # Tier 1: APPROVE Edge Cases
    # --------------------------------------------------------------------------
    def test_tier_1_approve_exact_boundary_conditions(self):
        """Tier 1 exact boundary: synth=SYNTH_LOW - 0.000001 (< SYNTH_LOW) and match=MATCH_HIGH (>= MATCH_HIGH) -> APPROVE."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_LOW - 0.000001},
            verification={"match_score": MATCH_HIGH},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "APPROVE")
        self.assertTrue(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 0)
        self.assertEqual(res["cost"]["agent_seconds_avoided"], 0.0)
        self.assertEqual(res["cost"]["est_inr"], 0.0)

    def test_tier_1_approve_zero_synth_max_match(self):
        """Tier 1 perfect audio: synth=0.0 and match=1.0 -> APPROVE."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.0},
            verification={"match_score": 1.0},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "APPROVE")
        self.assertTrue(res["tool_allowed"])

    # --------------------------------------------------------------------------
    # Tier 2: STEP_UP with Active Challenge Edge Cases
    # --------------------------------------------------------------------------
    def test_tier_2_step_up_borderline_synthetic_lower_bound(self):
        """Tier 2 borderline lower bound: synth=SYNTH_LOW (exact SYNTH_LOW) with match=0.95 -> STEP_UP."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_LOW},
            verification={"match_score": 0.95},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertIn("inconclusive", res["reason"].lower())

    def test_tier_2_step_up_borderline_synthetic_upper_bound(self):
        """Tier 2 borderline upper bound: synth=SYNTH_HIGH - 0.000001 (just under SYNTH_HIGH) with match=0.95 -> STEP_UP."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_HIGH - 0.000001},
            verification={"match_score": 0.95},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)

    def test_tier_2_step_up_active_challenge_unmatched_caller(self):
        """Tier 2 unverified caller: natural human voice (< SYNTH_LOW) but match=MATCH_HIGH - 0.000001 (< MATCH_HIGH) -> STEP_UP."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.05},
            verification={"match_score": MATCH_HIGH - 0.000001},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertIn("two-factor", res["reason"].lower())

    def test_tier_2_step_up_active_challenge_twiml_generation(self):
        """Tier 2 active challenge IVR: build_twilio_step_up_twiml produces valid PIN gather prompt."""
        from backend.telephony_bridge import TwilioMediaStreamBridge
        twiml = TwilioMediaStreamBridge.build_twilio_step_up_twiml()
        self.assertIn('numDigits="4"', twiml)
        self.assertIn("PIN", twiml)
        self.assertIn("<Gather", twiml)
        self.assertIn("</Response>", twiml)

    def test_tier_2_step_up_active_challenge_agent_intent(self):
        """Tier 2 in voice_agent: STEP_UP decision sets intent='STEP_UP_CHALLENGE' and asks for PIN."""
        from backend.agent import voice_agent
        sample_wav = ROOT_DIR / "tests" / "sample_human.wav"
        with open(sample_wav, "rb") as f:
            audio_bytes = f.read()

        # In fail-closed / unconfigured environment, process_turn executes through gate
        res = voice_agent.process_turn(audio_bytes=audio_bytes, speaker_id="unregistered_user")
        self.assertIn(res["decision"], ["BLOCK", "STEP_UP", "BLOCK_ALERT"])
        self.assertFalse(res["tool"]["result"])
        if res["decision"] == "STEP_UP":
            self.assertIn(res["intent"], ["STEP_UP_CHALLENGE", "STAGE_B_ACTIVE_CHALLENGE"])
            self.assertTrue(any(k in res["agent_reply_text"] for k in ("PIN", "पिन", "ಪದಗಳನ್ನು", "words", "challenge")))

    # --------------------------------------------------------------------------
    # Tier 3: BLOCK_ALERT Clone Attack Edge Cases
    # --------------------------------------------------------------------------
    def test_tier_3_block_alert_clone_attack_exact_boundary(self):
        """Tier 3 exact boundary: synth=SYNTH_HIGH (exact SYNTH_HIGH) and match=MATCH_HIGH (exact MATCH_HIGH) -> BLOCK_ALERT."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_HIGH},
            verification={"match_score": MATCH_HIGH},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertEqual(res["cost"]["agent_seconds_avoided"], 120.0)
        self.assertEqual(res["cost"]["est_inr"], 20.0)
        self.assertIn("clone", res["reason"].lower())

    def test_tier_3_block_alert_clone_attack_upper_extremes(self):
        """Tier 3 high-confidence clone attack: synth=1.0 and match=1.0 -> BLOCK_ALERT."""
        res = evaluate_gate(
            detection={"synthetic_score": 1.0},
            verification={"match_score": 1.0},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertFalse(res["tool_allowed"])
        self.assertIn("fraud", res["reason"].lower())

    def test_tier_3_block_synthetic_unknown_speaker(self):
        """Tier 3 synthetic unknown speaker: synth=SYNTH_HIGH and match=MATCH_HIGH - 0.000001 -> BLOCK."""
        res = evaluate_gate(
            detection={"synthetic_score": SYNTH_HIGH},
            verification={"match_score": MATCH_HIGH - 0.000001},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)

    def test_3_tier_fail_closed_never_promotes_to_approve(self):
        """Fail-closed guarantees that errors, missing values, or None payloads NEVER promote to APPROVE."""
        bad_inputs = [
            ({"synthetic_score": None}, {"match_score": 0.95}),
            ({"synthetic_score": 0.05}, {"match_score": None}),
            ({}, {}),
            ({"error": "DetectifAI timeout"}, {"match_score": 0.95}),
            ({"synthetic_score": 0.05}, {"error": "Speaker verification failed"}),
        ]
        for det, ver in bad_inputs:
            res = evaluate_gate(detection=det, verification=ver, action="TRANSFER_FUNDS")
            self.assertIn(res["decision"], ["BLOCK", "STEP_UP"])
            self.assertFalse(res["tool_allowed"])
            self.assertTrue(res.get("fail_closed"))


class TestSlide4CountersEdgeCases(unittest.TestCase):
    """Edge cases for Slide 4 live demo counters: checks run, clones blocked, agent steps skipped, agent time saved."""

    def setUp(self):
        self.client = TestClient(app)

    def test_slide_4_counters_exact_field_keys_and_types(self):
        """Validates all Slide 4 counters are returned with correct schema and non-negative values."""
        stats = get_telemetry_stats()

        # Counter 1: checks run
        self.assertIn("checks", stats)
        self.assertIn("total_checks", stats)
        self.assertGreaterEqual(stats["checks"], 0)

        # Counter 2: clones blocked
        self.assertIn("blocks", stats)
        self.assertIn("total_blocked", stats)
        self.assertGreaterEqual(stats["blocks"], 0)

        # Counter 3: agent steps skipped
        self.assertIn("steps_skipped", stats)
        self.assertIn("agent_steps_skipped", stats)
        self.assertGreaterEqual(stats["steps_skipped"], 0)

        # Counter 4: agent time saved (seconds and INR)
        self.assertIn("seconds_avoided", stats)
        self.assertIn("agent_seconds_avoided", stats)
        self.assertIn("est_inr", stats)
        self.assertIn("est_cost_savings_inr", stats)
        self.assertGreaterEqual(stats["seconds_avoided"], 0.0)
        self.assertGreaterEqual(stats["est_inr"], 0.0)

        # Editable rate assumption
        self.assertIn("assumption", stats)
        self.assertIn("per min", stats["assumption"])

    def test_slide_4_counters_mathematical_consistency(self):
        """Slide 4 Counters adhere to core mathematical invariants: est_inr = (seconds / 60) * rate."""
        stats = get_telemetry_stats()
        # Cost saving calculation invariant
        expected_inr = round((stats["seconds_avoided"] / 60.0) * 10.0, 2)
        self.assertAlmostEqual(stats["est_inr"], expected_inr, places=1)
        # Checks count is greater than or equal to sum of individual categories
        self.assertGreaterEqual(stats["checks"], stats["blocks"])
        self.assertGreaterEqual(stats["steps_skipped"], stats["blocks"])

    def test_slide_4_cost_saving_helper_math(self):
        """Direct verification of cost-savings formula helper in gate.py."""
        from backend.gate import _calculate_cost_saving

        # When skipped=False (APPROVE)
        cost_approve = _calculate_cost_saving(skipped=False)
        self.assertEqual(cost_approve["agent_steps_skipped"], 0)
        self.assertEqual(cost_approve["agent_seconds_avoided"], 0.0)
        self.assertEqual(cost_approve["est_inr"], 0.0)

        # When skipped=True (BLOCK / BLOCK_ALERT / STEP_UP)
        cost_blocked = _calculate_cost_saving(skipped=True)
        self.assertEqual(cost_blocked["agent_steps_skipped"], 1)
        self.assertEqual(cost_blocked["agent_seconds_avoided"], 120.0)
        self.assertEqual(cost_blocked["est_inr"], 20.0)

    def test_slide_4_counters_sequential_simulation(self):
        """Simulates sequential events and verifies Slide 4 demo counters accurately accumulate."""
        initial = get_telemetry_stats()

        # Log 1: APPROVE event
        log_audit_event(
            request_id=f"sim_approve_{uuid.uuid4().hex[:6]}",
            ts="2026-10-16T15:00:00Z",
            speaker_id="senior_user_01",
            action="TRANSFER_FUNDS",
            decision="APPROVE",
            reason="Natural voice and biometric match verified.",
            detection={"is_synthetic": False, "synthetic_score": 0.04, "latency_ms": 150},
            verification={"matched": True, "match_score": 0.95, "latency_ms": 150},
            tool_status="EXECUTED",
            cost={"agent_steps_skipped": 0, "agent_seconds_avoided": 0.0, "est_inr": 0.0}
        )

        # Log 2: BLOCK_ALERT event (Clone attack caught)
        log_audit_event(
            request_id=f"sim_clone_{uuid.uuid4().hex[:6]}",
            ts="2026-10-16T15:01:00Z",
            speaker_id="senior_user_01",
            action="TRANSFER_FUNDS",
            decision="BLOCK_ALERT",
            reason="Voice clone detected. Funds frozen.",
            detection={"is_synthetic": True, "synthetic_score": 0.94, "latency_ms": 160},
            verification={"matched": True, "match_score": 0.91, "latency_ms": 160},
            tool_status="LOCKED",
            cost={"agent_steps_skipped": 1, "agent_seconds_avoided": 120.0, "est_inr": 20.0}
        )

        # Log 3: STEP_UP event (Active challenge)
        log_audit_event(
            request_id=f"sim_stepup_{uuid.uuid4().hex[:6]}",
            ts="2026-10-16T15:02:00Z",
            speaker_id="unknown_speaker",
            action="TRANSFER_FUNDS",
            decision="STEP_UP",
            reason="Unverified speaker. 4-digit PIN requested.",
            detection={"is_synthetic": False, "synthetic_score": 0.08, "latency_ms": 140},
            verification={"matched": False, "match_score": 0.35, "latency_ms": 140},
            tool_status="LOCKED",
            cost={"agent_steps_skipped": 1, "agent_seconds_avoided": 120.0, "est_inr": 20.0}
        )

        after = get_telemetry_stats()
        self.assertEqual(after["checks"], initial["checks"] + 3)
        self.assertEqual(after["blocks"], initial["blocks"] + 1)
        self.assertEqual(after["approvals"], initial["approvals"] + 1)
        self.assertEqual(after["total_step_up"], initial["total_step_up"] + 1)
        self.assertEqual(after["steps_skipped"], initial["steps_skipped"] + 2)
        self.assertAlmostEqual(after["seconds_avoided"], initial["seconds_avoided"] + 240.0, places=1)
        self.assertAlmostEqual(after["est_inr"], initial["est_inr"] + 40.0, places=1)


if __name__ == "__main__":
    unittest.main()

