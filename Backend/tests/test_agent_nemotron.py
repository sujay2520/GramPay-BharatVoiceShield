"""Unit and Integration Tests for NVIDIA Nemotron-3.5 Voice Agent Integration in GramPay.

Tests the 4 Core Requirements:
1. Stage B Active Challenge: When gate returns STEP_UP / EXTRA_CHECK, calls Nemotron to
   generate a random 4-word challenge phrase (e.g., 'Golden river seven mango') with vocal instruction.
2. Measures caller response latency buffer to catch real-time voice conversion lag (>800ms lag indicates voice changer).
3. If APPROVED, calls Nemotron to formulate a calm, respectful Hindi/English voice response for rural farmers
   (e.g., 'Namaste Ramesh ji. Voice verified. Payment of Rs 5,000 to IFFCO Fertilizer Co-op is completed via Hello! UPI.').
4. Short-circuits on BLOCK/CLONE with ZERO LLM compute burned.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure root directory is on path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.agent import (
    voice_agent,
    VoiceAgentOrchestrator,
    VOICE_CHANGER_LATENCY_THRESHOLD_MS,
    DEFAULT_GRAMPAY_RECIPIENT,
    DEFAULT_GRAMPAY_AMOUNT
)
from backend.tools import BankingTools


class TestNemotronGramPayAgent(unittest.TestCase):
    def setUp(self):
        self.orchestrator = VoiceAgentOrchestrator()
        self.sample_wav_path = ROOT_DIR / "tests" / "sample_human.wav"
        with open(self.sample_wav_path, "rb") as f:
            self.sample_audio = f.read()

    # --------------------------------------------------------------------------
    # 1. Stage B Active Challenge Tests
    # --------------------------------------------------------------------------
    def test_stage_b_challenge_generates_4_word_phrase_and_vocal_instruction(self):
        """When called, generate_stage_b_challenge must produce a 4-word phrase and respectful vocal instruction."""
        challenge = self.orchestrator.generate_stage_b_challenge(speaker_id="farmer_ramesh")
        
        self.assertIn("challenge_phrase", challenge)
        self.assertIn("vocal_instruction", challenge)
        self.assertIn("words", challenge)
        
        words = challenge["challenge_phrase"].split()
        self.assertEqual(len(words), 4, f"Challenge phrase must contain exactly 4 words, got: {words}")
        self.assertEqual(challenge["status"], "PENDING_VERIFICATION")
        self.assertIn("Namaste", challenge["vocal_instruction"])
        self.assertIn("Ramesh ji", challenge["vocal_instruction"])

    def test_stage_b_challenge_invokes_nemotron_when_client_configured(self):
        """When client is configured, Nemotron is called with prompt and system prompt for Stage B challenge."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"challenge_phrase": "Golden river seven mango", "vocal_instruction": "Namaste Ramesh ji. Suraksha ke liye bolein: Golden river seven mango."}'))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        agent = VoiceAgentOrchestrator()
        agent.client = mock_client

        res = agent.generate_stage_b_challenge(speaker_id="farmer_ramesh")
        self.assertEqual(res["challenge_phrase"], "Golden river seven mango")
        self.assertEqual(len(res["words"]), 4)
        self.assertIn("Golden river seven mango", res["vocal_instruction"])
        self.assertEqual(agent.llm_call_count, 1)

    @patch("backend.agent.detectif_client.detect_deepfake")
    @patch("backend.agent.detectif_client.verify_speaker")
    def test_step_up_gate_triggers_stage_b_active_challenge(self, mock_verify, mock_detect):
        """When gate returns STEP_UP / EXTRA_CHECK, agent triggers Stage B Active Challenge with locked tool."""
        # Unmatched real human voice triggers STEP_UP
        mock_detect.return_value = {"is_synthetic": False, "synthetic_score": 0.05, "latency_ms": 100}
        mock_verify.return_value = {"matched": False, "match_score": 0.40, "latency_ms": 120}

        turn = self.orchestrator.process_turn(
            audio_bytes=self.sample_audio,
            speaker_id="farmer_ramesh",
            action="TRANSFER_FUNDS"
        )

        self.assertIn(turn["decision"], ["STEP_UP", "EXTRA_CHECK"])
        self.assertEqual(turn["intent"], "STAGE_B_ACTIVE_CHALLENGE")
        self.assertEqual(turn["tool"]["status"], "LOCKED")
        self.assertIn("stage_b_challenge", turn)
        self.assertEqual(len(turn["stage_b_challenge"]["words"]), 4)
        self.assertIn("Namaste Ramesh ji", turn["agent_reply_text"])

    # --------------------------------------------------------------------------
    # 2. Latency Buffer Defense (>800ms catches voice changers)
    # --------------------------------------------------------------------------
    def test_measure_latency_buffer_exceeding_threshold_detects_voice_changer(self):
        """Latency > 800ms must be flagged as active voice changer software."""
        # 950ms lag (typical of real-time RVC pitch-tracking + neural synthesis pipeline)
        telemetry = self.orchestrator.measure_latency_buffer(950.0)
        self.assertTrue(telemetry["is_voice_changer"])
        self.assertEqual(telemetry["status"], "VOICE_CHANGER_DETECTED")
        self.assertIn("Real-time voice conversion lag detected", telemetry["reason"])
        self.assertIn("950.0ms exceeds 800.0ms", telemetry["reason"])

    def test_measure_latency_buffer_within_threshold_passes(self):
        """Natural human response latency <= 800ms passes without flagging voice changer."""
        telemetry = self.orchestrator.measure_latency_buffer(450.0)
        self.assertFalse(telemetry["is_voice_changer"])
        self.assertEqual(telemetry["status"], "NATURAL_LATENCY")

    def test_process_turn_short_circuits_on_voice_changer_latency_lag(self):
        """Turn with caller response latency buffer > 800ms immediately blocks with ZERO LLM compute."""
        agent = VoiceAgentOrchestrator()
        agent.client = MagicMock()  # Mock client must NOT be called

        turn = agent.process_turn(
            audio_bytes=self.sample_audio,
            speaker_id="farmer_ramesh",
            response_latency_ms=920.0
        )

        self.assertEqual(turn["decision"], "BLOCK_ALERT")
        self.assertEqual(turn["intent"], "BLOCK_VOICE_CHANGER")
        self.assertEqual(turn["tool"]["status"], "LOCKED")
        self.assertFalse(turn["llm_compute_burned"])
        self.assertEqual(agent.llm_call_count, 0, "Zero LLM compute must be burned on latency lag!")
        self.assertGreater(turn["cost"]["est_inr"], 0.0)

    # --------------------------------------------------------------------------
    # 3. Rural Farmer Spoken Response Formulation
    # --------------------------------------------------------------------------
    def test_formulate_approved_response_default_tone_and_format(self):
        """Approved response formulation delivers respectful Hindi/English response for rural farmers."""
        spoken = self.orchestrator.formulate_approved_response(
            speaker_id="farmer_ramesh",
            transcript="Send 5000 to IFFCO Fertilizer Co-op",
            amount=5000.0,
            recipient="IFFCO Fertilizer Co-op",
            action="TRANSFER_FUNDS"
        )
        self.assertIn("Namaste Ramesh ji", spoken)
        self.assertIn("Voice verified", spoken)
        self.assertIn("5,000", spoken)
        self.assertIn("IFFCO Fertilizer Co-op", spoken)
        self.assertIn("Hello! UPI", spoken)

    def test_formulate_approved_response_with_nemotron_generation(self):
        """Nemotron is invoked to generate the respectful Hinglish greeting and confirmation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"friendly_spoken_reply": "Namaste Ramesh ji. Voice verified. Payment of Rs 5,000 to IFFCO Fertilizer Co-op is completed via Hello! UPI."}'))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        agent = VoiceAgentOrchestrator()
        agent.client = mock_client

        spoken = agent.formulate_approved_response(
            speaker_id="farmer_ramesh",
            transcript="Pay 5000 to IFFCO",
            amount=5000.0,
            recipient="IFFCO Fertilizer Co-op"
        )

        self.assertEqual(
            spoken,
            "Namaste Ramesh ji. Voice verified. Payment of Rs 5,000 to IFFCO Fertilizer Co-op is completed via Hello! UPI."
        )
        self.assertEqual(agent.llm_call_count, 1)

    @patch("backend.agent.detectif_client.detect_deepfake")
    @patch("backend.agent.detectif_client.verify_speaker")
    def test_approved_turn_executes_tool_and_formulates_grampay_response(self, mock_verify, mock_detect):
        """Approved turn unlocks banking tool and delivers respectful GramPay voice response."""
        mock_detect.return_value = {"is_synthetic": False, "synthetic_score": 0.08, "latency_ms": 90}
        mock_verify.return_value = {"matched": True, "match_score": 0.95, "latency_ms": 110}

        turn = self.orchestrator.process_turn(
            audio_bytes=self.sample_audio,
            speaker_id="farmer_ramesh",
            user_text_hint="Payment of Rs 5,000 to IFFCO Fertilizer Co-op",
            amount=5000.0,
            recipient="IFFCO Fertilizer Co-op",
            response_latency_ms=350.0  # Natural latency <= 800ms
        )

        self.assertEqual(turn["decision"], "APPROVE")
        self.assertEqual(turn["tool"]["status"], "EXECUTED")
        self.assertEqual(turn["tool"]["result"]["amount_inr"], 5000.0)
        self.assertEqual(turn["tool"]["result"]["recipient"], "IFFCO Fertilizer Co-op")
        self.assertIn("Namaste Ramesh ji", turn["agent_reply_text"])
        self.assertIn("Voice verified", turn["agent_reply_text"])
        self.assertIn("Hello! UPI", turn["agent_reply_text"])

    # --------------------------------------------------------------------------
    # 4. Short-Circuit on BLOCK/CLONE with ZERO LLM Compute
    # --------------------------------------------------------------------------
    @patch("backend.agent.detectif_client.detect_deepfake")
    @patch("backend.agent.detectif_client.verify_speaker")
    def test_short_circuit_on_clone_burns_zero_llm_compute(self, mock_verify, mock_detect):
        """Voice clone attack (high match + synthetic vocoder) must short-circuit with ZERO LLM compute."""
        mock_detect.return_value = {"is_synthetic": True, "synthetic_score": 0.94, "latency_ms": 80}
        mock_verify.return_value = {"matched": True, "match_score": 0.91, "latency_ms": 95}

        agent = VoiceAgentOrchestrator()
        agent.client = MagicMock()  # Must not be touched

        turn = agent.process_turn(
            audio_bytes=self.sample_audio,
            speaker_id="farmer_ramesh",
            user_text_hint="Transfer 5000 to IFFCO Fertilizer Co-op"
        )

        self.assertEqual(turn["decision"], "BLOCK_ALERT")
        self.assertEqual(turn["intent"], "BLOCK_CLONE_ATTACK")
        self.assertEqual(turn["tool"]["status"], "LOCKED")
        self.assertFalse(turn["llm_compute_burned"])
        self.assertEqual(agent.llm_call_count, 0, "No LLM calls allowed on clone block!")
        self.assertIn("artificial voice clone was detected", turn["agent_reply_text"])
        self.assertGreater(turn["cost"]["est_inr"], 0.0)

    @patch("backend.agent.detectif_client.detect_deepfake")
    @patch("backend.agent.detectif_client.verify_speaker")
    def test_short_circuit_on_synthetic_bot_burns_zero_llm_compute(self, mock_verify, mock_detect):
        """Synthetic audio from unverified caller (synth_score >= 0.50, low match) blocks with ZERO LLM compute."""
        mock_detect.return_value = {"is_synthetic": True, "synthetic_score": 0.92, "latency_ms": 80}
        mock_verify.return_value = {"matched": False, "match_score": 0.25, "latency_ms": 90}

        agent = VoiceAgentOrchestrator()
        agent.client = MagicMock()

        turn = agent.process_turn(
            audio_bytes=self.sample_audio,
            speaker_id="unknown_bot"
        )

        self.assertEqual(turn["decision"], "BLOCK")
        self.assertEqual(turn["tool"]["status"], "LOCKED")
        self.assertFalse(turn["llm_compute_burned"])
        self.assertEqual(agent.llm_call_count, 0)

    # --------------------------------------------------------------------------
    # 5. Challenge Verification End-to-End
    # --------------------------------------------------------------------------
    def test_verify_challenge_response_success(self):
        """Farmer accurately speaking 4 challenge words with latency <= 800ms is approved."""
        res = self.orchestrator.verify_challenge_response(
            expected_phrase="Golden river seven mango",
            spoken_response="Golden river seven mango",
            speaker_id="farmer_ramesh",
            response_latency_ms=420.0,
            amount=5000.0,
            recipient="IFFCO Fertilizer Co-op"
        )
        self.assertEqual(res["decision"], "APPROVE")
        self.assertTrue(res["stage_b_verified"])
        self.assertEqual(res["tool"]["status"], "EXECUTED")
        self.assertIn("Namaste Ramesh ji. Voice verified.", res["agent_reply_text"])

    def test_verify_challenge_response_voice_changer_lag_blocked(self):
        """Even if words match, response latency > 800ms blocks voice changer with zero LLM compute."""
        agent = VoiceAgentOrchestrator()
        agent.client = MagicMock()

        res = agent.verify_challenge_response(
            expected_phrase="Golden river seven mango",
            spoken_response="Golden river seven mango",
            speaker_id="farmer_ramesh",
            response_latency_ms=880.0
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertTrue(res["voice_changer_detected"])
        self.assertFalse(res["llm_compute_burned"])
        self.assertEqual(agent.llm_call_count, 0)
        self.assertEqual(res["tool"]["status"], "LOCKED")


if __name__ == "__main__":
    unittest.main()
