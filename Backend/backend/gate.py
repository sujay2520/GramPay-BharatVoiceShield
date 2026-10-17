"""Deterministic Security Policy Gate (Lexis Engine).
Implements the 3-Tier GramPay Decision Matrix from the competition slides:
- Tier 1: Low Risk (Authentic & Matched: synth_score < 0.62 and similarity >= 0.53) -> APPROVE ('PAY' / unlock tool)
- Tier 2: Medium/Uncertain Risk (synth between 0.50 and 0.62 OR similarity between 0.40 and 0.53 OR noisy 8kHz audio) -> STEP_UP ('EXTRA_CHECK' / prompt dynamic active cognitive phrase via Nemotron)
- Tier 3: High Risk (Synthetic Clone: synth_score >= 0.62) -> BLOCK_ALERT ('BLOCK_CLONE' / freeze UPI payout, alert fraud desk, short-circuit LLM compute)
- Fail-Closed: API error or timeout -> BLOCK for payments, STEP_UP for balance queries.
Calculate compute savings (Rs 10/min, 120s avoided per block).

NON-NEGOTIABLE RULE: The LLM NEVER decides allow or block.
Security decisions are 100% deterministic code based on DetectifAI model outputs.
"""

import math
import random
from typing import Dict, Any, Optional
from backend.config import (
    MATCH_HIGH as CFG_MATCH_HIGH,
    MATCH_LOW as CFG_MATCH_LOW,
    SYNTH_HIGH as CFG_SYNTH_HIGH,
    SYNTH_LOW as CFG_SYNTH_LOW,
    ASSUMED_COST_PER_MIN_INR,
    EST_CALL_SECONDS_SAVED_PER_BLOCK
)

# 3-Tier GramPay Decision Matrix Grounded Thresholds
SYNTH_HIGH = float(CFG_SYNTH_HIGH if CFG_SYNTH_HIGH is not None else 0.62)
SYNTH_LOW = float(CFG_SYNTH_LOW if CFG_SYNTH_LOW is not None else 0.50)
MATCH_HIGH = float(CFG_MATCH_HIGH if CFG_MATCH_HIGH is not None else 0.53)
MATCH_LOW = float(CFG_MATCH_LOW if CFG_MATCH_LOW is not None else 0.40)

# GramPay Action / Decision Identifiers
ACTION_APPROVE_PAY = "PAY"
ACTION_STEP_UP_EXTRA_CHECK = "EXTRA_CHECK"
ACTION_BLOCK_CLONE = "BLOCK_CLONE"
ACTION_BLOCK = "BLOCK"

# High-risk financial actions requiring payment locking
PAYMENT_ACTIONS = {
    "TRANSFER_FUNDS", "PAY", "PAYMENT", "SEND_MONEY", "UPI_PAY", "UPI_PAYOUT",
    "TRANSFER", "WITHDRAWAL", "PAY_BILL", "DEBIT", "HIGH"
}

# Low-risk query actions
BALANCE_ACTIONS = {
    "CHECK_BALANCE", "GET_BALANCE", "VIEW_ACCOUNT", "BALANCE", "READ_STATEMENT",
    "ACCOUNT_STATUS", "INQUIRY", "LOW"
}

# Pool of dynamic active cognitive challenge phrases for Nemotron in Tier 2
COGNITIVE_CHALLENGE_TEMPLATES = [
    "Suraksha {code} payment confirmation",
    "GramPay verification code {code}",
    "Kisan voice security {code} approve",
    "Harit Dharti {code} confirm payment",
    "Neela Aasman {code} voice check"
]

def get_dynamic_cognitive_phrase() -> str:
    """Generates an unpredictable dynamic active cognitive challenge phrase.
    
    Used in Tier 2 (Medium/Uncertain Risk) to prompt the caller via NVIDIA Nemotron.
    Forces the caller to utter dynamic, non-replayable tokens to defeat recorded
    audio or asynchronous vocoder spoofing.
    """
    code = random.randint(1000, 9999)
    template = random.choice(COGNITIVE_CHALLENGE_TEMPLATES)
    return template.format(code=code)

def evaluate_gate(
    detection: Optional[Dict[str, Any]] = None,
    verification: Optional[Dict[str, Any]] = None,
    action: str = "TRANSFER_FUNDS",
    api_error: Optional[str] = None,
    sample_rate: Optional[int] = None,
    is_noisy: bool = False,
    is_noisy_8k: bool = False,
    audio_meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Evaluates the 3-Tier GramPay Decision Matrix.
    
    Args:
        detection: {"is_synthetic": bool, "synthetic_score": float, ...}
        verification: {"matched": bool, "match_score": float, ...}
        action: "TRANSFER_FUNDS" / "PAY" (payment) or "CHECK_BALANCE" (balance query)
        api_error: Error message if DetectifAI call failed or timed out
        sample_rate: Optional integer audio sample rate (e.g. 8000 for telephony)
        is_noisy: Optional boolean indicating high background acoustic noise
        is_noisy_8k: Optional flag indicating noisy 8kHz audio stream
        audio_meta: Optional metadata dictionary with audio attributes
        
    Returns:
        {
            "decision": "APPROVE" | "BLOCK_ALERT" | "STEP_UP" | "BLOCK",
            "action_code": "PAY" | "EXTRA_CHECK" | "BLOCK_CLONE" | "BLOCK",
            "tier": 1 | 2 | 3 | None,
            "tier_name": str,
            "reason": str (senior-accessible plain English explanation),
            "tool_allowed": bool,
            "fail_closed": bool,
            "cognitive_phrase": Optional[str],
            "cost": {
                "agent_steps_skipped": int,
                "agent_seconds_avoided": float,
                "est_inr": float,
                "assumption": str
            }
        }
    """
    detection = detection or {}
    verification = verification or {}
    act_upper = (action or "").strip().upper()
    is_payment = (act_upper in PAYMENT_ACTIONS) or any(
        k in act_upper for k in ["TRANSFER", "PAY", "SEND", "DEBIT", "WITHDRAW"]
    )

    # --------------------------------------------------------------------------
    # 1. FAIL-CLOSED CHECK: API error, timeout, or missing/incomplete telemetry
    #    Rule: BLOCK for payments, STEP_UP for balance queries.
    # --------------------------------------------------------------------------
    error_msg = api_error or detection.get("error") or verification.get("error")
    
    # Extract synthetic score (support multiple key variants)
    synth_val = detection.get("synthetic_score")
    if synth_val is None:
        synth_val = detection.get("synth_score", detection.get("score"))
        
    # Extract similarity/match score (support multiple key variants)
    sim_val = verification.get("match_score")
    if sim_val is None:
        sim_val = verification.get("similarity", verification.get("similarity_score", verification.get("score")))

    has_invalid_telemetry = (synth_val is None or sim_val is None)
    is_explicit_fail_closed = detection.get("fail_closed") or verification.get("fail_closed")

    if error_msg or has_invalid_telemetry or is_explicit_fail_closed:
        decision = "BLOCK" if is_payment else "STEP_UP"
        action_code = ACTION_BLOCK if is_payment else ACTION_STEP_UP_EXTRA_CHECK
        fail_reason = (
            f"Security verification system unavailable: {error_msg}. Transaction held safely to protect your funds."
            if error_msg else
            "Incomplete biometric telemetry from DetectifAI. Transaction held safely to protect your funds."
        )
        return {
            "decision": decision,
            "action_code": action_code,
            "tier": None,
            "tier_name": "Fail-Closed",
            "reason": fail_reason,
            "tool_allowed": False,
            "fail_closed": True,
            "cognitive_phrase": get_dynamic_cognitive_phrase() if decision == "STEP_UP" else None,
            "cost": _calculate_cost_saving(skipped=True)
        }

    try:
        synth_score = float(synth_val)
        similarity = float(sim_val)
    except (ValueError, TypeError):
        decision = "BLOCK" if is_payment else "STEP_UP"
        return {
            "decision": decision,
            "action_code": ACTION_BLOCK if is_payment else ACTION_STEP_UP_EXTRA_CHECK,
            "tier": None,
            "tier_name": "Fail-Closed",
            "reason": "Malformed non-numeric biometric scores received from detection engine.",
            "tool_allowed": False,
            "fail_closed": True,
            "cognitive_phrase": get_dynamic_cognitive_phrase() if decision == "STEP_UP" else None,
            "cost": _calculate_cost_saving(skipped=True)
        }

    synth_high = float(detection.get("threshold", SYNTH_HIGH))
    match_high = float(verification.get("threshold", MATCH_HIGH))
    if (
        not all(math.isfinite(v) for v in (synth_score, similarity, synth_high, match_high))
        or not 0.0 <= synth_score <= 1.0
        or not -1.0 <= similarity <= 1.0
        or not 0.0 <= synth_high <= 1.0
        or not -1.0 <= match_high <= 1.0
    ):
        decision = "BLOCK" if is_payment else "STEP_UP"
        return {
            "decision": decision,
            "action_code": ACTION_BLOCK if is_payment else ACTION_STEP_UP_EXTRA_CHECK,
            "tier": None,
            "tier_name": "Fail-Closed",
            "reason": "Invalid biometric scores or thresholds received from the voice provider.",
            "tool_allowed": False,
            "fail_closed": True,
            "cognitive_phrase": None,
            "cost": _calculate_cost_saving(skipped=True)
        }

    provider_verdict = detection.get("verdict")
    provider_synthetic = detection.get("is_synthetic")
    provider_matched = verification.get("matched")
    if provider_verdict not in (None, "real", "fake", "not_sure"):
        provider_verdict = "invalid"
    if (
        provider_verdict == "invalid"
        or (provider_synthetic is not None and not isinstance(provider_synthetic, bool))
        or (provider_matched is not None and not isinstance(provider_matched, bool))
        or (provider_verdict in ("real", "fake") and (provider_verdict == "fake") != (synth_score >= synth_high))
        or (provider_verdict != "not_sure" and provider_synthetic is not None and provider_synthetic != (synth_score >= synth_high))
        or (provider_matched is not None and provider_matched != (similarity >= match_high))
    ):
        decision = "BLOCK" if is_payment else "STEP_UP"
        return {
            "decision": decision,
            "action_code": ACTION_BLOCK if is_payment else ACTION_STEP_UP_EXTRA_CHECK,
            "tier": None,
            "tier_name": "Fail-Closed",
            "reason": "Conflicting biometric results received from the voice provider.",
            "tool_allowed": False,
            "fail_closed": True,
            "cognitive_phrase": None,
            "cost": _calculate_cost_saving(skipped=True)
        }

    if provider_verdict == "not_sure":
        return {
            "decision": "STEP_UP",
            "action_code": ACTION_STEP_UP_EXTRA_CHECK,
            "tier": 2,
            "tier_name": "Tier 2: Provider Uncertain",
            "reason": "The voice provider could not determine whether this sample is real or synthetic. Another check is required.",
            "tool_allowed": False,
            "fail_closed": True,
            "cognitive_phrase": get_dynamic_cognitive_phrase(),
            "cost": _calculate_cost_saving(skipped=True)
        }

    # --------------------------------------------------------------------------
    # 2. AUDIO FORMAT & NOISE INSPECTION
    # --------------------------------------------------------------------------
    sr = sample_rate
    if sr is None and audio_meta:
        sr = audio_meta.get("sample_rate")
    if sr is None:
        sr = detection.get("sample_rate")

    noise_flag = is_noisy or (audio_meta.get("is_noisy") if audio_meta else False) or detection.get("is_noisy", False) or detection.get("noisy", False)
    
    noisy_8k_detected = (
        is_noisy_8k
        or (sr == 8000 and noise_flag)
        or detection.get("noisy_8k", False)
        or detection.get("is_noisy_8k", False)
        or (audio_meta.get("is_noisy_8k", False) if audio_meta else False)
    )

    # --------------------------------------------------------------------------
    # 3. EVALUATE 3-TIER GRAMPAY DECISION MATRIX
    # --------------------------------------------------------------------------

    # TIER 3: HIGH RISK (Synthetic Clone / Bot: synth_score >= 0.62)
    # Action: BLOCK_ALERT ('BLOCK_CLONE' / freeze UPI payout, alert fraud desk, short-circuit LLM compute)
    if provider_verdict == "fake" or provider_synthetic is True or synth_score >= synth_high:
        # Check if matched to enrolled account holder
        matched_enrolled = provider_matched if provider_matched is not None else similarity >= match_high
        
        if matched_enrolled:
            decision = "BLOCK_ALERT"
            action_code = ACTION_BLOCK_CLONE
            reason = (
                "CRITICAL WARNING: Computer-generated voice clone detected! "
                f"Although the voice sounds like the account holder, neural synthesis was identified (synth_score {synth_score:.2f} >= {SYNTH_HIGH:.2f}). "
                "UPI payout frozen, bank fraud desk alerted, and LLM compute short-circuited."
            )
        else:
            # Synthetic voice from an unverified speaker / robot spammer
            decision = "BLOCK"
            action_code = ACTION_BLOCK
            reason = (
                f"Synthetic computer-generated audio detected from an unverified caller (synth_score {synth_score:.2f} >= {SYNTH_HIGH:.2f}). "
                "Call terminated, payout frozen, and downstream compute short-circuited."
            )

        return {
            "decision": decision,
            "action_code": action_code,
            "tier": 3,
            "tier_name": "Tier 3: High Risk",
            "reason": reason,
            "tool_allowed": False,
            "fail_closed": False,
            "cognitive_phrase": None,
            "cost": _calculate_cost_saving(skipped=True)
        }

    # TIER 2: MEDIUM / UNCERTAIN RISK
    # Conditions:
    # - synth between 0.50 and 0.62
    # - OR similarity between 0.40 and 0.53
    # - OR noisy 8kHz audio
    # - OR unverified speaker (similarity < 0.40 with human voice)
    # Action: STEP_UP ('EXTRA_CHECK' / prompt dynamic active cognitive phrase via Nemotron)
    is_synth_uncertain = (SYNTH_LOW <= synth_score < synth_high)
    is_similarity_uncertain = (MATCH_LOW <= similarity < match_high)
    is_similarity_low = (similarity < MATCH_LOW)

    if is_synth_uncertain or is_similarity_uncertain or noisy_8k_detected or is_similarity_low:
        decision = "STEP_UP"
        action_code = ACTION_STEP_UP_EXTRA_CHECK
        cognitive_phrase = get_dynamic_cognitive_phrase()

        if noisy_8k_detected:
            if action == "CHECK_BALANCE":
                reason = (
                    "Medium/Uncertain Risk: Noisy 8kHz telephony audio detected, authenticity inconclusive. "
                    "Real human voice recognized, but voice does not match account records. Please provide your 4-digit PIN. "
                    f"Step-up challenge required: prompt dynamic active cognitive phrase via Nemotron: \"{cognitive_phrase}\"."
                )
            else:
                reason = (
                    "Medium/Uncertain Risk: Noisy 8kHz telephony audio detected, authenticity inconclusive. "
                    "Real human voice detected, but speaker does not match the enrolled account holder. "
                    "Transfer locked pending two-factor authorization. "
                    f"Step-up challenge required: prompt dynamic active cognitive phrase via Nemotron: \"{cognitive_phrase}\"."
                )
        elif action == "CHECK_BALANCE":
            reason = (
                f"Medium/Uncertain Risk: Voice authenticity confidence is inconclusive or speaker similarity is unverified "
                f"(synth {synth_score:.2f}, similarity {similarity:.2f}). "
                "Real human voice recognized, but voice does not match account records. Please provide your 4-digit PIN. "
                f"Step-up challenge required: prompt dynamic active cognitive phrase via Nemotron: \"{cognitive_phrase}\"."
            )
        else:
            reason = (
                f"Medium/Uncertain Risk: Voice authenticity confidence is inconclusive or speaker similarity is unverified "
                f"(synth {synth_score:.2f}, similarity {similarity:.2f}). "
                "Real human voice detected, but speaker does not match the enrolled account holder. "
                "Transfer locked pending two-factor authorization. "
                f"Step-up challenge required: prompt dynamic active cognitive phrase via Nemotron: \"{cognitive_phrase}\"."
            )

        return {
            "decision": decision,
            "action_code": action_code,
            "tier": 2,
            "tier_name": "Tier 2: Medium/Uncertain Risk",
            "reason": reason,
            "tool_allowed": False,
            "fail_closed": False,
            "cognitive_phrase": cognitive_phrase,
            "cost": _calculate_cost_saving(skipped=True)
        }

    # TIER 1: LOW RISK (Authentic & Matched: synth_score < 0.62 and similarity >= 0.53)
    # Action: APPROVE ('PAY' / unlock tool)
    decision = "APPROVE"
    action_code = ACTION_APPROVE_PAY
    reason = (
        f"Verified Safe (Tier 1): Provider score is below the synthetic threshold ({synth_score:.2f} < {synth_high:.2f}) "
        f"and account holder identity confirmed (similarity {similarity:.2f} >= {match_high:.2f}). "
        "Payment tool unlocked."
    )

    return {
        "decision": decision,
        "action_code": action_code,
        "tier": 1,
        "tier_name": "Tier 1: Low Risk",
        "reason": reason,
        "tool_allowed": True,
        "fail_closed": False,
        "cognitive_phrase": None,
        "cost": _calculate_cost_saving(skipped=False)
    }

def _calculate_cost_saving(skipped: bool) -> Dict[str, Any]:
    """Calculates agent compute minutes & INR saved by short-circuiting.
    
    Standard parameters from GramPay / UnClone specifications:
    - Burn Rate: Rs 10.00 / minute of LLM + TTS + ASR telephony compute
    - Avoided Duration: 120.0 seconds saved per blocked fraudulent turn
    """
    assumption_text = f"Rs {ASSUMED_COST_PER_MIN_INR:.2f} per min, {EST_CALL_SECONDS_SAVED_PER_BLOCK:.0f}s avoided per block (editable)"
    if not skipped:
        return {
            "agent_steps_skipped": 0,
            "agent_seconds_avoided": 0.0,
            "est_inr": 0.0,
            "assumption": assumption_text
        }
    
    seconds_avoided = EST_CALL_SECONDS_SAVED_PER_BLOCK
    est_inr = round((seconds_avoided / 60.0) * ASSUMED_COST_PER_MIN_INR, 2)
    return {
        "agent_steps_skipped": 1,
        "agent_seconds_avoided": seconds_avoided,
        "est_inr": est_inr,
        "assumption": assumption_text
    }
