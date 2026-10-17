"""Comprehensive test suite for UnClone Gate Backend.
Verifies all endpoints, contracts, gate logic, cryptographic tokens, and fail-closed security.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.main import app
from backend.gate import evaluate_gate
from backend.tools import BankingTools
from backend.credentials import credential_service
from backend.audit import (
    get_telemetry_stats,
    log_audit_event,
    update_audit_challenge,
    get_recent_audit_logs
)

class TestUnCloneContract(unittest.TestCase):
    def setUp(self):
        try:
            from backend.voice_enrollment import reset_enrolled_voice
            reset_enrolled_voice()
        except Exception:
            pass
        self.client = TestClient(app)
        self.sample_wav_path = ROOT_DIR / "tests" / "sample_human.wav"
        self.assertTrue(self.sample_wav_path.exists(), "Sample WAV must exist for testing.")

    def tearDown(self):
        try:
            from backend.voice_enrollment import reset_enrolled_voice
            reset_enrolled_voice()
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # 1. Gate Logic & 2x2 Matrix Tests
    # --------------------------------------------------------------------------
    def test_gate_real_enrolled_approve(self):
        """Case 1: Real human voice (< 0.20) + High match (>= 0.85) -> APPROVE"""
        res = evaluate_gate(
            detection={"is_synthetic": False, "synthetic_score": 0.05},
            verification={"matched": True, "match_score": 0.94},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "APPROVE")
        self.assertTrue(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 0)

    def test_gate_synthetic_clone_block_alert(self):
        """Case 2: Synthetic vocoder (>= 0.50) + High match (>= 0.85) -> BLOCK_ALERT (Clone attack caught!)"""
        res = evaluate_gate(
            detection={"is_synthetic": True, "synthetic_score": 0.89},
            verification={"matched": True, "match_score": 0.92},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertGreater(res["cost"]["est_inr"], 0.0)

    def test_gate_real_wrong_speaker_step_up(self):
        """Case 3: Real human voice (< 0.20) + Low match (< 0.85) -> STEP_UP"""
        res = evaluate_gate(
            detection={"is_synthetic": False, "synthetic_score": 0.08},
            verification={"matched": False, "match_score": 0.42},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)

    def test_gate_synthetic_unknown_block(self):
        """Case 4: Synthetic (>= 0.50) + Low match (< 0.85) -> BLOCK"""
        res = evaluate_gate(
            detection={"is_synthetic": True, "synthetic_score": 0.95},
            verification={"matched": False, "match_score": 0.31},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK")
        self.assertFalse(res["tool_allowed"])

    def test_gate_fail_closed_on_error(self):
        """API Error / Timeout -> MUST FAIL CLOSED (Never APPROVE)"""
        res = evaluate_gate(
            detection={},
            verification={},
            action="TRANSFER_FUNDS",
            api_error="Connection timed out"
        )
        self.assertIn(res["decision"], ["BLOCK", "STEP_UP"])
        self.assertFalse(res["tool_allowed"])
        self.assertTrue(res.get("fail_closed"))

    # --------------------------------------------------------------------------
    # 2. Banking Tools & Locking Mechanism Tests
    # --------------------------------------------------------------------------
    def test_tool_locked_by_default(self):
        res = BankingTools.execute_transfer_funds(amount=5000.0, is_unlocked=False)
        self.assertEqual(res["status"], "LOCKED")
        self.assertIsNone(res["result"])

    def test_tool_unlocked_execution(self):
        res = BankingTools.execute_transfer_funds(amount=5000.0, is_unlocked=True)
        self.assertEqual(res["status"], "EXECUTED")
        self.assertIsNotNone(res["result"])
        self.assertIn("TXN-UNCLONE", res["result"]["transaction_id"])

    # --------------------------------------------------------------------------
    # 3. Agent Cryptographic Credential & Replay Protection Tests
    # --------------------------------------------------------------------------
    def test_credential_issue_and_single_use_verification(self):
        """Issues credential, verifies it successfully once, then asserts replay is rejected."""
        issued = credential_service.issue_credential(
            agent_id="agent_icici_voice_01",
            org="ICICI Bank Voice Ops",
            allowed_actions=["TRANSFER_FUNDS", "CHECK_BALANCE"]
        )
        token = issued["credential"]
        self.assertTrue(token)

        # First verification must pass and issue VERIFIED_AGENT badge
        verify1 = credential_service.verify_handshake(token, required_action="TRANSFER_FUNDS")
        self.assertEqual(verify1["badge"], "VERIFIED_AGENT")
        self.assertTrue(verify1["checks"]["signature"])
        self.assertTrue(verify1["checks"]["unused"])

        # Second verification of the exact same token MUST BE REJECTED (Single-use replay attack protection)
        verify2 = credential_service.verify_handshake(token, required_action="TRANSFER_FUNDS")
        self.assertEqual(verify2["badge"], "REJECTED")
        self.assertFalse(verify2["checks"]["unused"])
        self.assertIn("REPLAY ATTACK", verify2["reason"])

    # --------------------------------------------------------------------------
    # 4. REST Endpoints Contract Verification
    # --------------------------------------------------------------------------
    def test_api_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("request_id", data)
        self.assertIn("ts", data)
        self.assertIn("detectif_reachable", data)

    def test_api_credential_endpoints(self):
        # Issue endpoint
        issue_resp = self.client.post("/api/credential/issue", json={
            "agent_id": "south_indian_bank_bot_03",
            "org": "South Indian Bank Support",
            "allowed_actions": ["CHECK_BALANCE"]
        })
        self.assertEqual(issue_resp.status_code, 200)
        issue_data = issue_resp.json()
        self.assertIn("credential", issue_data)
        
        # Verify endpoint
        verify_resp = self.client.post("/api/handshake/verify", json={
            "credential": issue_data["credential"]
        })
        self.assertEqual(verify_resp.status_code, 200)
        verify_data = verify_resp.json()
        self.assertEqual(verify_data["badge"], "VERIFIED_AGENT")

    def test_api_check_with_audio_fail_closed_if_unconfigured(self):
        """When DETECTIF_API_KEY is not yet populated with live platform key, endpoint fails closed safely."""
        with open(self.sample_wav_path, "rb") as audio_file:
            resp = self.client.post(
                "/api/check",
                files={"audio": ("sample_human.wav", audio_file, "audio/wav")},
                data={"speaker_id": "senior_user_01", "action": "TRANSFER_FUNDS", "amount": "25000"}
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("request_id", data)
        self.assertIn("decision", data)
        # Must fail closed: either BLOCK or STEP_UP
        self.assertIn(data["decision"], ["BLOCK", "STEP_UP"])
        self.assertEqual(data["tool"]["status"], "LOCKED")
        self.assertTrue(data.get("fail_closed"))
        self.assertEqual(data.get("status"), "error")
        # Rule 5.4: Strictly NO mock or fake numbers when DetectifAI is unconfigured
        self.assertIsNone(data["detection"]["synthetic_score"])
        self.assertIsNone(data["verification"]["match_score"])

    def test_api_health_endpoint_no_fake_connected_when_unconfigured(self):
        """Rule 5.4: Health endpoint must NOT fake 'connected' or 'ok=True' when DetectifAI is unconfigured."""
        from unittest.mock import patch
        from backend.detectif_client import detectif_client
        with patch.object(detectif_client, "is_configured", return_value=False):
            resp = self.client.get("/api/health")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertFalse(data["detectif_reachable"])
            self.assertFalse(data["ok"])
            self.assertIn("reason", data["detectif_details"])

        # And verify when configured it correctly reflects reachability
        if detectif_client.is_configured():
            resp = self.client.get("/api/health")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["detectif_reachable"])
            self.assertTrue(data["ok"])


    def test_agent_turn_fail_closed_no_mock_scores(self):
        """Rule 5.4: Agent turn pre-gate fails closed without fabricating mock scores."""
        with open(self.sample_wav_path, "rb") as audio_file:
            resp = self.client.post(
                "/api/agent/turn",
                files={"audio": ("sample_human.wav", audio_file, "audio/wav")},
                data={"speaker_id": "senior_user_01", "user_text_hint": "Transfer 10000 to granddaughter"}
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "error")
        self.assertTrue(data["fail_closed"])
        self.assertIn(data["decision"], ["BLOCK", "STEP_UP"])
        self.assertEqual(data["tool"]["status"], "LOCKED")
        self.assertIsNone(data["detection"]["synthetic_score"])
        self.assertIsNone(data["verification"]["match_score"])

    def test_api_audit_and_stats_endpoints(self):
        audit_resp = self.client.get("/api/audit?limit=10")
        self.assertEqual(audit_resp.status_code, 200)
        audit_data = audit_resp.json()
        self.assertIn("request_id", audit_data)
        self.assertIn("ts", audit_data)
        self.assertIn("logs", audit_data)
        self.assertIn("count", audit_data)
        
        # Verify Section 4 exact row keys
        if len(audit_data["logs"]) > 0:
            sample_row = audit_data["logs"][0]
            self.assertIn("time", sample_row)
            self.assertIn("decision", sample_row)
            self.assertIn("reason", sample_row)
            self.assertIn("scores", sample_row)
            self.assertIn("latency", sample_row)
            self.assertIn("tool_status", sample_row)
            self.assertIn("blocked_parameters", sample_row)

        stats_resp = self.client.get("/api/stats")
        self.assertEqual(stats_resp.status_code, 200)
        stats_data = stats_resp.json()
        self.assertIn("request_id", stats_data)
        self.assertIn("ts", stats_data)
        # Slide 4 Official Live Demo Counters
        self.assertIn("checks_run", stats_data)
        self.assertIn("clones_blocked", stats_data)
        self.assertIn("agent_steps_skipped", stats_data)
        self.assertIn("agent_time_saved_inr", stats_data)
        self.assertIn("logs", stats_data)
        self.assertIn("detailed_logs", stats_data)

        # Blueprint Section 4 totals
        self.assertIn("checks", stats_data)
        self.assertIn("blocks", stats_data)
        self.assertIn("approvals", stats_data)
        self.assertIn("steps_skipped", stats_data)
        self.assertIn("seconds_avoided", stats_data)
        self.assertIn("est_inr", stats_data)

    def test_active_challenge_telemetry_and_slide_4_counters(self):
        """Verifies active challenge latency/verdict columns in SQLite and Slide 4 counters."""
        initial_stats = get_telemetry_stats()
        initial_checks = initial_stats["checks_run"]
        initial_clones = initial_stats["clones_blocked"]
        initial_skipped = initial_stats["agent_steps_skipped"]
        initial_inr = initial_stats["agent_time_saved_inr"]

        # Log event with Stage B active challenge fields
        req_id = "req_test_challenge_99"
        audit_id = log_audit_event(
            request_id=req_id,
            ts="2026-10-16T12:00:00.000000+00:00",
            speaker_id="senior_user_01",
            action="TRANSFER_FUNDS",
            decision="BLOCK_ALERT",
            reason="Synthetic clone caught during active vocal challenge",
            detection={"is_synthetic": True, "synthetic_score": 0.95, "latency_ms": 120},
            verification={"matched": True, "match_score": 0.92, "latency_ms": 130},
            tool_status="LOCKED",
            cost={"agent_steps_skipped": 1, "agent_seconds_avoided": 120.0, "est_inr": 20.0},
            challenge_latency_ms=185,
            challenge_verdict="CLONE_DETECTED"
        )
        self.assertIsInstance(audit_id, int)

        # Retrieve and verify logs have challenge fields
        recent_logs = get_recent_audit_logs(limit=5)
        matched_log = next((l for l in recent_logs if l["request_id"] == req_id), None)
        self.assertIsNotNone(matched_log)
        self.assertEqual(matched_log["challenge_latency_ms"], 185)
        self.assertEqual(matched_log["challenge_verdict"], "CLONE_DETECTED")
        self.assertEqual(matched_log["active_challenge_latency_ms"], 185)
        self.assertEqual(matched_log["active_challenge_verdict"], "CLONE_DETECTED")

        # Test update_audit_challenge helper
        updated = update_audit_challenge(
            audit_id=audit_id,
            challenge_latency_ms=210,
            challenge_verdict="STEP_UP_PASS"
        )
        self.assertTrue(updated)

        updated_logs = get_recent_audit_logs(limit=5)
        updated_log = next((l for l in updated_logs if l["id"] == audit_id), None)
        self.assertIsNotNone(updated_log)
        self.assertEqual(updated_log["challenge_latency_ms"], 210)
        self.assertEqual(updated_log["challenge_verdict"], "STEP_UP_PASS")

        # Verify Slide 4 counters updated accurately
        new_stats = get_telemetry_stats()
        self.assertEqual(new_stats["checks_run"], initial_checks + 1)
        self.assertGreaterEqual(new_stats["clones_blocked"], initial_clones + 1)
        self.assertEqual(new_stats["agent_steps_skipped"], initial_skipped + 1)
        self.assertAlmostEqual(new_stats["agent_time_saved_inr"], initial_inr + 20.0, places=1)
        self.assertIsInstance(new_stats["logs"], list)
        self.assertIsInstance(new_stats["detailed_logs"], list)

    def test_section_4_strict_field_structure_verification(self):
        """Validates all Section 4 exact contract field keys on /api/check and /api/agent/turn."""
        # 1. Check endpoint
        with open(self.sample_wav_path, "rb") as audio_file:
            resp = self.client.post(
                "/api/check",
                files={"audio": ("sample_human.wav", audio_file, "audio/wav")},
                data={"speaker_id": "senior_user_01", "action": "TRANSFER_FUNDS", "amount": "45000"}
            )
        data = resp.json()
        # Top-level contract fields
        for field in ["request_id", "ts", "decision", "reason", "detection", "verification", "tool", "cost", "audit_id"]:
            self.assertIn(field, data, f"Missing required Section 4 field '{field}' in /api/check response")
        
        # Nested detection fields
        for field in ["is_synthetic", "synthetic_score", "raw", "latency_ms"]:
            self.assertIn(field, data["detection"], f"Missing detection field '{field}'")
            
        # Nested verification fields
        for field in ["matched", "match_score", "raw", "latency_ms"]:
            self.assertIn(field, data["verification"], f"Missing verification field '{field}'")

        # Nested tool fields
        for field in ["name", "status", "result"]:
            self.assertIn(field, data["tool"], f"Missing tool field '{field}'")

        # Nested cost fields
        for field in ["agent_steps_skipped", "agent_seconds_avoided", "est_inr", "assumption"]:
            self.assertIn(field, data["cost"], f"Missing cost field '{field}'")

        # 2. Agent Turn endpoint
        with open(self.sample_wav_path, "rb") as audio_file:
            turn_resp = self.client.post(
                "/api/agent/turn",
                files={"audio": ("sample_human.wav", audio_file, "audio/wav")},
                data={"speaker_id": "senior_user_01", "user_text_hint": "Check my balance"}
            )
        turn_data = turn_resp.json()
        for field in ["request_id", "ts", "decision", "reason", "detection", "verification", "tool", "cost", "audit_id", "transcript", "agent_reply_text", "intent"]:
            self.assertIn(field, turn_data, f"Missing required Section 4 field '{field}' in /api/agent/turn response")

    def test_global_error_fail_closed_contract(self):
        """Rule Section 4: All errors must return { 'request_id': ..., 'ts': ..., 'error': '...', 'fail_closed': true }."""
        # Test 400 validation error (missing required audio)
        resp = self.client.post("/api/check", data={"speaker_id": "user1"})
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("request_id", data)
        self.assertIn("ts", data)
        self.assertIn("error", data)
        self.assertTrue(data.get("fail_closed"))

    # --------------------------------------------------------------------------
    # 5. GramPay Voice Payment Parameters Contract Tests
    # --------------------------------------------------------------------------
    def test_grampay_check_endpoint_contract(self):
        """POST /api/check with GramPay parameters (kisan_farmer_01, amount=5000, action=TRANSFER_FUNDS)."""
        with open(self.sample_wav_path, "rb") as audio_file:
            resp = self.client.post(
                "/api/check",
                files={"audio": ("sample_human.wav", audio_file, "audio/wav")},
                data={
                    "speaker_id": "kisan_farmer_01",
                    "action": "TRANSFER_FUNDS",
                    "amount": "5000.0"
                }
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("request_id", data)
        self.assertIn("decision", data)
        self.assertIn("tool", data)
        self.assertIn("cost", data)
        self.assertIn(data["decision"], ["APPROVE", "BLOCK_ALERT", "STEP_UP", "BLOCK"])
        # Tool is locked under fail-closed without live DetectifAI API credentials
        self.assertEqual(data["tool"]["status"], "LOCKED")
        self.assertTrue(data.get("fail_closed"))

    def test_grampay_agent_turn_endpoint_contract(self):
        """POST /api/agent/turn with GramPay voice prompt for UPI 123Pay / Hello! UPI."""
        with open(self.sample_wav_path, "rb") as audio_file:
            resp = self.client.post(
                "/api/agent/turn",
                files={"audio": ("sample_human.wav", audio_file, "audio/wav")},
                data={
                    "speaker_id": "kisan_farmer_01",
                    "action": "TRANSFER_FUNDS",
                    "user_text_hint": "Bhaiya Kisan Kendra ko 5000 rupaye bhej do"
                }
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("request_id", data)
        self.assertIn("decision", data)
        self.assertIn("transcript", data)
        self.assertIn("agent_reply_text", data)
        self.assertIn("intent", data)
        self.assertIn("tool", data)
        self.assertIn("cost", data)

    def test_grampay_kisan_tools_locked_by_default(self):
        """GramPay Kisan tools (pay_merchant, check_kisan_balance, verify_pm_kisan_dbt) are LOCKED when is_unlocked=False."""
        pay_res = BankingTools.pay_merchant(amount=2500.0, is_unlocked=False)
        self.assertEqual(pay_res["status"], "LOCKED")
        self.assertIsNone(pay_res["result"])
        self.assertIn("LOCKED", pay_res["message"])

        bal_res = BankingTools.check_kisan_balance(is_unlocked=False)
        self.assertEqual(bal_res["status"], "LOCKED")
        self.assertIsNone(bal_res["result"])

        dbt_res = BankingTools.verify_pm_kisan_dbt(is_unlocked=False)
        self.assertEqual(dbt_res["status"], "LOCKED")
        self.assertIsNone(dbt_res["result"])

    def test_grampay_kisan_tools_unlocked_execution(self):
        """GramPay Kisan tools execute safely when gate unlocks them (is_unlocked=True)."""
        pay_res = BankingTools.pay_merchant(
            amount=1500.0,
            merchant_name="IFFCO Fertilizer Co-op",
            upi_id="iffco@upi",
            account_id="kisan_farmer_01",
            is_unlocked=True
        )
        self.assertEqual(pay_res["status"], "EXECUTED")
        self.assertIsNotNone(pay_res["result"])
        self.assertIn("TXN-NPCI-123PAY", pay_res["result"]["transaction_id"])
        self.assertEqual(pay_res["result"]["merchant_name"], "IFFCO Fertilizer Co-op")

        bal_res = BankingTools.check_kisan_balance(account_id="kisan_farmer_01", is_unlocked=True)
        self.assertEqual(bal_res["status"], "EXECUTED")
        self.assertIn("Ramesh Patel", bal_res["result"]["holder_name"])

        dbt_res = BankingTools.verify_pm_kisan_dbt(account_id="kisan_farmer_01", is_unlocked=True)
        self.assertEqual(dbt_res["status"], "EXECUTED")
        self.assertEqual(dbt_res["result"]["dbt_status"], "ACTIVE")

    def test_grampay_agent_credential_issuance_and_handshake(self):
        """Issues scoped GramPay voice bot credential and verifies cryptographic handshake."""
        issue_resp = self.client.post("/api/credential/issue", json={
            "agent_id": "grampay_upi123_voice_bot",
            "org": "GramPay Rural Banking (NPCI Hello! UPI)",
            "allowed_actions": ["TRANSFER_FUNDS", "CHECK_BALANCE"],
            "limit_inr": 5000.0
        })
        self.assertEqual(issue_resp.status_code, 200)
        issue_data = issue_resp.json()
        self.assertIn("credential", issue_data)
        self.assertEqual(issue_data["limit_inr"], 5000.0)

        verify_resp = self.client.post("/api/handshake/verify", json={
            "credential": issue_data["credential"],
            "action": "TRANSFER_FUNDS"
        })
        self.assertEqual(verify_resp.status_code, 200)
        verify_data = verify_resp.json()
        self.assertEqual(verify_data["badge"], "VERIFIED_AGENT")
        self.assertEqual(verify_data["agent_id"], "grampay_upi123_voice_bot")

    # --------------------------------------------------------------------------
    # 6. 3-Tier Gate Logic Contract Tests (APPROVE, STEP_UP, BLOCK_ALERT)
    # --------------------------------------------------------------------------
    def test_3_tier_gate_contract_tier_1_approve(self):
        """Tier 1: APPROVE -> Natural human voice + Enrolled speaker match -> Tool Unlocked."""
        res = evaluate_gate(
            detection={"is_synthetic": False, "synthetic_score": 0.04},
            verification={"matched": True, "match_score": 0.95},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "APPROVE")
        self.assertTrue(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 0)
        self.assertEqual(res["cost"]["est_inr"], 0.0)

        tool_exec = BankingTools.execute_transfer_funds(amount=5000.0, is_unlocked=res["tool_allowed"])
        self.assertEqual(tool_exec["status"], "EXECUTED")

    def test_3_tier_gate_contract_tier_2_step_up_active_challenge(self):
        """Tier 2: STEP_UP -> Real voice but unverified/borderline -> Active Challenge, Tool Locked."""
        res = evaluate_gate(
            detection={"is_synthetic": False, "synthetic_score": 0.08},
            verification={"matched": False, "match_score": 0.40},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertIn("two-factor", res["reason"].lower())

        # Verify active challenge TwiML generated by Telephony Bridge
        from backend.telephony_bridge import TwilioMediaStreamBridge
        twiml = TwilioMediaStreamBridge.build_twilio_step_up_twiml()
        self.assertIn("<Gather", twiml)
        self.assertIn("PIN", twiml)

    def test_3_tier_gate_contract_tier_3_block_alert(self):
        """Tier 3: BLOCK_ALERT -> Cloned voice detected -> Tool Hard-Locked, Fraud Alert Triggered."""
        res = evaluate_gate(
            detection={"is_synthetic": True, "synthetic_score": 0.92},
            verification={"matched": True, "match_score": 0.94},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertGreater(res["cost"]["est_inr"], 0.0)
        self.assertIn("clone", res["reason"].lower())
        self.assertIn("fraud", res["reason"].lower())

        tool_locked = BankingTools.execute_transfer_funds(amount=5000.0, is_unlocked=res["tool_allowed"])
        self.assertEqual(tool_locked["status"], "LOCKED")

    # --------------------------------------------------------------------------
    # 7. Slide 4 Live Demo Counters Contract Tests
    # --------------------------------------------------------------------------
    def test_slide_4_counters_contract_structure(self):
        """Slide 4 Counters Contract: validates presence and types of all 4 demo counters."""
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Counter 1: checks run
        self.assertIn("checks", data)
        self.assertIn("total_checks", data)
        self.assertIsInstance(data["checks"], int)

        # Counter 2: clones blocked
        self.assertIn("blocks", data)
        self.assertIn("total_blocked", data)
        self.assertIsInstance(data["blocks"], int)

        # Counter 3: agent steps skipped
        self.assertIn("steps_skipped", data)
        self.assertIn("agent_steps_skipped", data)
        self.assertIsInstance(data["steps_skipped"], int)

        # Counter 4: agent time saved (seconds and rupees)
        self.assertIn("seconds_avoided", data)
        self.assertIn("agent_seconds_avoided", data)
        self.assertIn("est_inr", data)
        self.assertIn("est_cost_savings_inr", data)
        self.assertIn("assumption", data)
        self.assertIsInstance(data["seconds_avoided"], (int, float))
        self.assertIsInstance(data["est_inr"], (int, float))
        self.assertIn("Rs", data["assumption"])

    def test_slide_4_counters_increment_contract(self):
        """Slide 4 Counters increment accurately when audit events are logged."""
        from backend.audit import log_audit_event
        initial = self.client.get("/api/stats").json()

        # Log a simulated clone block (Slide 4 clones blocked counter)
        log_audit_event(
            request_id="req_slide4_test_block",
            ts="2026-10-16T12:00:00Z",
            speaker_id="farmer_test_01",
            action="TRANSFER_FUNDS",
            decision="BLOCK_ALERT",
            reason="Voice clone detected on UPI 123Pay call.",
            detection={"is_synthetic": True, "synthetic_score": 0.95, "latency_ms": 200},
            verification={"matched": True, "match_score": 0.92, "latency_ms": 200},
            tool_status="LOCKED",
            cost={"agent_steps_skipped": 1, "agent_seconds_avoided": 120.0, "est_inr": 20.0}
        )

        after = self.client.get("/api/stats").json()
        self.assertEqual(after["checks"], initial["checks"] + 1)
        self.assertEqual(after["blocks"], initial["blocks"] + 1)
        self.assertEqual(after["steps_skipped"], initial["steps_skipped"] + 1)
        self.assertAlmostEqual(after["seconds_avoided"], initial["seconds_avoided"] + 120.0, places=1)
        self.assertAlmostEqual(after["est_inr"], initial["est_inr"] + 20.0, places=1)


if __name__ == "__main__":
    unittest.main()

