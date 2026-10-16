"""Unit test suite specifically verifying the 3-Tier GramPay Decision Matrix in gate.py.

Verifies:
- Tier 1: Low Risk (Authentic & Matched: synth_score < 0.62 and similarity >= 0.53) -> APPROVE ('PAY' / unlock tool)
- Tier 2: Medium/Uncertain Risk (synth between 0.50 and 0.62 OR similarity between 0.40 and 0.53 OR noisy 8kHz audio) -> STEP_UP ('EXTRA_CHECK' / prompt dynamic active cognitive phrase via Nemotron)
- Tier 3: High Risk (Synthetic Clone: synth_score >= 0.62) -> BLOCK_ALERT ('BLOCK_CLONE' / freeze UPI payout, alert fraud desk, short-circuit LLM compute)
- Fail-Closed: API error or timeout -> BLOCK for payments, STEP_UP for balance queries.
- Calculate compute savings (Rs 10/min, 120s avoided per block).
"""

import unittest
from backend.gate import evaluate_gate, get_dynamic_cognitive_phrase

class TestGramPayDecisionMatrix(unittest.TestCase):
    
    # --------------------------------------------------------------------------
    # Tier 1: Low Risk
    # --------------------------------------------------------------------------
    def test_tier_1_low_risk_approve_pay(self):
        """Tier 1: synth_score < 0.62 and similarity >= 0.53 -> APPROVE ('PAY')."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.15},
            verification={"match_score": 0.88},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "APPROVE")
        self.assertEqual(res["action_code"], "PAY")
        self.assertEqual(res["tier"], 1)
        self.assertTrue(res["tool_allowed"])
        self.assertFalse(res["fail_closed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 0)
        self.assertEqual(res["cost"]["agent_seconds_avoided"], 0.0)
        self.assertEqual(res["cost"]["est_inr"], 0.0)

    # --------------------------------------------------------------------------
    # Tier 2: Medium / Uncertain Risk
    # --------------------------------------------------------------------------
    def test_tier_2_synth_between_050_and_062(self):
        """Tier 2: synth between 0.50 and 0.62 -> STEP_UP ('EXTRA_CHECK')."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.55},
            verification={"match_score": 0.90},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertEqual(res["action_code"], "EXTRA_CHECK")
        self.assertEqual(res["tier"], 2)
        self.assertFalse(res["tool_allowed"])
        self.assertIsNotNone(res["cognitive_phrase"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertEqual(res["cost"]["agent_seconds_avoided"], 120.0)
        self.assertEqual(res["cost"]["est_inr"], 20.0)

    def test_tier_2_similarity_between_040_and_053(self):
        """Tier 2: similarity between 0.40 and 0.53 -> STEP_UP ('EXTRA_CHECK')."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.20},
            verification={"match_score": 0.48},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertEqual(res["action_code"], "EXTRA_CHECK")
        self.assertEqual(res["tier"], 2)
        self.assertFalse(res["tool_allowed"])
        self.assertIsNotNone(res["cognitive_phrase"])

    def test_tier_2_noisy_8khz_audio(self):
        """Tier 2: noisy 8kHz audio -> STEP_UP ('EXTRA_CHECK')."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.10},
            verification={"match_score": 0.90},
            sample_rate=8000,
            is_noisy=True,
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertEqual(res["action_code"], "EXTRA_CHECK")
        self.assertEqual(res["tier"], 2)
        self.assertFalse(res["tool_allowed"])
        self.assertIn("8khz", res["reason"].lower())

    # --------------------------------------------------------------------------
    # Tier 3: High Risk
    # --------------------------------------------------------------------------
    def test_tier_3_high_risk_synthetic_clone(self):
        """Tier 3: synth_score >= 0.62 with matched enrolled user -> BLOCK_ALERT ('BLOCK_CLONE')."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.85},
            verification={"match_score": 0.92},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK_ALERT")
        self.assertEqual(res["action_code"], "BLOCK_CLONE")
        self.assertEqual(res["tier"], 3)
        self.assertFalse(res["tool_allowed"])
        self.assertIn("clone", res["reason"].lower())
        self.assertIn("fraud", res["reason"].lower())
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertEqual(res["cost"]["agent_seconds_avoided"], 120.0)
        self.assertEqual(res["cost"]["est_inr"], 20.0)

    def test_tier_3_high_risk_synthetic_bot_unmatched(self):
        """Tier 3: synth_score >= 0.62 unmatched caller -> BLOCK ('BLOCK')."""
        res = evaluate_gate(
            detection={"synthetic_score": 0.75},
            verification={"match_score": 0.20},
            action="TRANSFER_FUNDS"
        )
        self.assertEqual(res["decision"], "BLOCK")
        self.assertEqual(res["action_code"], "BLOCK")
        self.assertEqual(res["tier"], 3)
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertEqual(res["cost"]["est_inr"], 20.0)

    # --------------------------------------------------------------------------
    # Fail-Closed Tests
    # --------------------------------------------------------------------------
    def test_fail_closed_payments_blocked(self):
        """Fail-Closed on API error / timeout for payments -> BLOCK."""
        res = evaluate_gate(
            detection={},
            verification={},
            action="TRANSFER_FUNDS",
            api_error="DetectifAI upstream timeout (5.0s exceeded)"
        )
        self.assertEqual(res["decision"], "BLOCK")
        self.assertEqual(res["action_code"], "BLOCK")
        self.assertTrue(res["fail_closed"])
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertEqual(res["cost"]["est_inr"], 20.0)

    def test_fail_closed_balance_query_step_up(self):
        """Fail-Closed on API error / timeout for balance queries -> STEP_UP."""
        res = evaluate_gate(
            detection={},
            verification={},
            action="CHECK_BALANCE",
            api_error="Connection reset by peer"
        )
        self.assertEqual(res["decision"], "STEP_UP")
        self.assertEqual(res["action_code"], "EXTRA_CHECK")
        self.assertTrue(res["fail_closed"])
        self.assertFalse(res["tool_allowed"])
        self.assertEqual(res["cost"]["agent_steps_skipped"], 1)
        self.assertEqual(res["cost"]["est_inr"], 20.0)

    # --------------------------------------------------------------------------
    # Dynamic Cognitive Challenge Generator Test
    # --------------------------------------------------------------------------
    def test_dynamic_cognitive_challenge_generation(self):
        """Dynamic cognitive challenge returns non-empty unpredictable phrase."""
        phrase1 = get_dynamic_cognitive_phrase()
        phrase2 = get_dynamic_cognitive_phrase()
        self.assertTrue(len(phrase1) > 0)
        self.assertTrue(len(phrase2) > 0)


if __name__ == "__main__":
    unittest.main()
