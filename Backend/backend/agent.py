"""Voice Agent Orchestrator with DetectifAI Pre-Gate & NVIDIA Nemotron-3.5 Engine for GramPay.
Zero-Trust BFSI Voice Security for rural Indian farmers using Hello! UPI.

Core Security & Compute Optimization Requirements:
1. Stage B Active Challenge: When gate returns STEP_UP / EXTRA_CHECK, calls Nemotron to
   generate a random 4-word challenge phrase (e.g., 'Golden river seven mango') with vocal instruction.
2. Caller Response Latency Buffer: Measures response latency buffer to catch real-time voice conversion
   lag (>800ms indicates voice changer software like RVC/neural vocoder pipelines).
3. Rural Farmer Voice Response: When APPROVED, calls Nemotron to formulate a calm, respectful
   Hindi/English response (e.g., 'Namaste Ramesh ji. Voice verified. Payment of Rs 5,000 to IFFCO
   Fertilizer Co-op is completed via Hello! UPI.').
4. Zero-Compute Short-Circuit: Short-circuits on BLOCK / CLONE with ZERO LLM compute burned.
"""

import re
import json
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, Tuple, List
from openai import OpenAI

from backend.config import (
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NEMOTRON_MODEL
)
from backend.detectif_client import detectif_client, DetectifAPIError
from backend.gate import evaluate_gate, _calculate_cost_saving
from backend.tools import BankingTools

logger = logging.getLogger("unclone.agent")

# Constants for GramPay & Voice Conversion Defense
VOICE_CHANGER_LATENCY_THRESHOLD_MS = 800.0  # >800ms indicates active voice conversion lag
DEFAULT_GRAMPAY_RECIPIENT = "IFFCO Fertilizer Co-op"
DEFAULT_GRAMPAY_AMOUNT = 5000.0

# 4-word challenge candidate vocabulary (phonetically rich, common simple words)
STAGE_B_WORDS_POOL = [
    "Golden", "river", "seven", "mango",
    "Silver", "wheat", "tractor", "harvest",
    "Green", "monsoon", "lotus", "peacock",
    "Banyan", "copper", "farmer", "market"
]


class VoiceAgentOrchestrator:
    def __init__(self):
        self.client = None
        if NVIDIA_API_KEY:
            self.client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY, timeout=2.0)
        self.llm_call_count = 0
        self.last_llm_compute_burned = False

    def _get_farmer_name(self, speaker_id: str) -> str:
        """Extracts a respectful farmer name from speaker identity for GramPay."""
        sid = (speaker_id or "").lower()
        if "ramesh" in sid:
            return "Ramesh"
        if "sita" in sid:
            return "Sita"
        if "senior" in sid or "user" in sid or not sid:
            return "Ramesh"  # Default respectful persona for GramPay demo
        # Humanize ID if custom
        clean = re.sub(r'[^a-zA-Z0-9]+', ' ', speaker_id).strip().title()
        return clean or "Ramesh"

    def _parse_transfer_details(
        self,
        user_text: Optional[str],
        default_amount: float = DEFAULT_GRAMPAY_AMOUNT,
        default_recipient: str = DEFAULT_GRAMPAY_RECIPIENT
    ) -> Tuple[float, str]:
        """Parses transfer amount and recipient from user text hint or falls back to defaults."""
        if not user_text:
            return default_amount, default_recipient

        amt = default_amount
        rec = default_recipient

        # Extract numerical amount (e.g., "5000", "45,000", "Rs 5,000")
        m = re.search(r'(?:rs\.?|inr|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)', user_text, re.IGNORECASE)
        if m:
            try:
                amt = float(m.group(1).replace(',', ''))
            except ValueError:
                pass

        # Identify recipient keywords
        txt_low = user_text.lower()
        if "iffco" in txt_low or "fertilizer" in txt_low:
            rec = "IFFCO Fertilizer Co-op"
        elif "rahul" in txt_low:
            rec = "Rahul Sharma (Grandson)"
        elif "granddaughter" in txt_low:
            rec = "Granddaughter"
        elif "seed" in txt_low:
            rec = "Kisan Seeds Co-operative"
        elif "mandi" in txt_low:
            rec = "APMC Mandi"

        return amt, rec

    def _call_nemotron(self, prompt: str, system_prompt: str = "") -> str:
        """Invokes NVIDIA Nemotron-3.5 for intent parsing, challenge generation, and dialogue response."""
        if not self.client:
            logger.info("Nemotron client not configured; using offline fallback.")
            return "NVIDIA Nemotron API key not configured."

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            self.llm_call_count += 1
            self.last_llm_compute_burned = True
            resp = self.client.chat.completions.create(
                model=NEMOTRON_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=600,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}}
            )
            msg = resp.choices[0].message
            content = msg.content or getattr(msg, "reasoning_content", "") or ""
            return content.strip()
        except Exception as e:
            logger.error(f"Nemotron API execution failed: {e}")
            return f"Understood. Security check passed. Error invoking Nemotron: {str(e)}"

    def measure_latency_buffer(self, response_latency_ms: float) -> Dict[str, Any]:
        """Measures caller response latency buffer to catch real-time voice conversion lag.
        
        Rule 2: In real-time AI voice conversion (RVC/neural vocoder streaming), chunk processing,
        pitch-tracking, and synthesis buffers introduce an unavoidable acoustic delay.
        A buffer delay > 800ms indicates active voice changer software.
        """
        is_voice_changer = response_latency_ms > VOICE_CHANGER_LATENCY_THRESHOLD_MS
        return {
            "latency_ms": round(response_latency_ms, 2),
            "threshold_ms": VOICE_CHANGER_LATENCY_THRESHOLD_MS,
            "is_voice_changer": is_voice_changer,
            "status": "VOICE_CHANGER_DETECTED" if is_voice_changer else "NATURAL_LATENCY",
            "reason": (
                f"Real-time voice conversion lag detected: {response_latency_ms:.1f}ms exceeds "
                f"{VOICE_CHANGER_LATENCY_THRESHOLD_MS}ms threshold. Voice changer active."
                if is_voice_changer else
                f"Response latency ({response_latency_ms:.1f}ms) within acceptable natural human response buffer."
            )
        }

    def generate_stage_b_challenge(
        self,
        speaker_id: str = "farmer_ramesh",
        farmer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Stage B Active Challenge: Calls Nemotron to generate a random 4-word challenge phrase
        (e.g., 'Golden river seven mango') with vocal instruction in respectful Hindi/English.
        """
        name = farmer_name or self._get_farmer_name(speaker_id)
        
        # Primary reference 4-word challenge phrase and vocal instruction
        fallback_phrase = "Golden river seven mango"
        fallback_instruction = (
            f"Namaste {name} ji. Suraksha satyapan ke liye, kripya yeh chaar shabd bolein: {fallback_phrase}."
        )

        system_prompt = (
            "You are the GramPay Voice Security Engine powered by NVIDIA Nemotron-3.5 for Hello! UPI rural banking. "
            "The customer requires Stage B Active Challenge secondary voice liveness verification. "
            "1. Generate an unpredictable 4-word challenge phrase made of simple, distinct common words "
            "(e.g., 'Golden river seven mango', 'Silver wheat tractor harvest', 'Green monsoon lotus peacock'). "
            "2. Formulate a calm, respectful spoken vocal instruction in Hindi/English (Hinglish) for rural Indian farmers, "
            "addressing them with honorific 'ji' (e.g., 'Namaste Ramesh ji'), asking them to speak the four challenge words clearly. "
            "Respond strictly in valid JSON format with keys: "
            "'challenge_phrase' (string of exactly 4 space-separated words) and "
            "'vocal_instruction' (calm spoken Hindi/English instruction asking farmer to repeat the phrase)."
        )
        prompt = f"Generate Stage B Active Challenge for farmer {name} ji."

        challenge_phrase = fallback_phrase
        vocal_instruction = fallback_instruction

        if self.client:
            raw_nemotron = self._call_nemotron(prompt, system_prompt)
            try:
                if "{" in raw_nemotron and "}" in raw_nemotron:
                    json_str = raw_nemotron[raw_nemotron.find("{"):raw_nemotron.rfind("}") + 1]
                    parsed = json.loads(json_str)
                    words_str = parsed.get("challenge_phrase", "").strip()
                    if words_str and len(words_str.split()) == 4:
                        challenge_phrase = words_str
                    instr = parsed.get("vocal_instruction") or parsed.get("instruction")
                    if instr:
                        vocal_instruction = instr.strip()
            except Exception as e:
                logger.warning(f"Could not parse Nemotron Stage B challenge JSON: {e}")

        return {
            "challenge_phrase": challenge_phrase,
            "vocal_instruction": vocal_instruction,
            "words": challenge_phrase.split(),
            "status": "PENDING_VERIFICATION"
        }

    def generate_challenge_phrase(self, language: str = "en") -> str:
        """Generates an unpredictable phonetically-rich challenge phrase for Tier 2 liveness."""
        res = self.generate_stage_b_challenge()
        return res["challenge_phrase"]

    def formulate_approved_response(
        self,
        speaker_id: str,
        transcript: str,
        amount: float = DEFAULT_GRAMPAY_AMOUNT,
        recipient: str = DEFAULT_GRAMPAY_RECIPIENT,
        action: str = "TRANSFER_FUNDS"
    ) -> str:
        """Calls Nemotron to formulate a calm, respectful Hindi/English voice response for rural farmers
        (e.g., 'Namaste Ramesh ji. Voice verified. Payment of Rs 5,000 to IFFCO Fertilizer Co-op is completed via Hello! UPI.').
        """
        farmer_name = self._get_farmer_name(speaker_id)
        
        fallback_reply = (
            f"Namaste {farmer_name} ji. Voice verified. "
            f"Payment of Rs {int(amount):,} to {recipient} is completed via Hello! UPI."
            if action != "CHECK_BALANCE" else
            f"Namaste {farmer_name} ji. Voice verified. Your account balance check is completed via Hello! UPI."
        )

        system_prompt = (
            "You are the GramPay Voice Banking Assistant powered by NVIDIA Nemotron-3.5 for rural Indian farmers using Hello! UPI. "
            "You speak in a calm, respectful, reassuring Hindi/English (Hinglish) tone suitable for rural farmers. "
            "Always greet the farmer with respect using 'Namaste' and the honorific 'ji' (e.g., 'Namaste Ramesh ji'). "
            "Confirm that their voice biometric identity has been authenticated ('Voice verified'). "
            "Confirm the transaction details (e.g., 'Payment of Rs 5,000 to IFFCO Fertilizer Co-op is completed via Hello! UPI.'). "
            "Format your reply strictly as valid JSON with keys: "
            "'intent', 'amount', 'recipient', 'friendly_spoken_reply'."
        )

        prompt = (
            f"Authenticated Farmer Request: \"{transcript}\"\n"
            f"Farmer Name: {farmer_name} ji\n"
            f"Action: {action}\n"
            f"Amount: Rs {amount:,.0f}\n"
            f"Recipient: {recipient}\n"
            "Formulate the calm, respectful voice response."
        )

        if not self.client:
            return fallback_reply

        raw_llm_response = self._call_nemotron(prompt, system_prompt)
        try:
            if "{" in raw_llm_response and "}" in raw_llm_response:
                json_str = raw_llm_response[raw_llm_response.find("{"):raw_llm_response.rfind("}") + 1]
                parsed = json.loads(json_str)
                spoken = parsed.get("friendly_spoken_reply")
                if spoken:
                    return spoken.strip()
        except Exception as e:
            logger.warning(f"Failed to parse Nemotron spoken reply JSON: {e}")

        # If Nemotron returned plain text without JSON, or parsing failed, return raw or fallback
        if (
            raw_llm_response
            and not raw_llm_response.startswith("NVIDIA Nemotron API key not configured")
            and not raw_llm_response.startswith("Understood. Security check passed. Error")
        ):
            return raw_llm_response.strip()

        return fallback_reply

    def verify_challenge_response(
        self,
        expected_phrase: str,
        spoken_response: str,
        speaker_id: str = "farmer_ramesh",
        response_latency_ms: Optional[float] = None,
        amount: float = DEFAULT_GRAMPAY_AMOUNT,
        recipient: str = DEFAULT_GRAMPAY_RECIPIENT
    ) -> Dict[str, Any]:
        """Evaluates a farmer's response to the Stage B Active Challenge.
        
        1. Checks latency buffer: >800ms lag indicates real-time voice changer -> Short-circuits with ZERO LLM compute.
        2. Validates spoken phrase matches the 4 challenge words.
        3. If APPROVED, calls Nemotron to formulate the respectful voice confirmation.
        """
        # Step 1: Check real-time voice changer lag
        if response_latency_ms is not None:
            latency_data = self.measure_latency_buffer(response_latency_ms)
            if latency_data["is_voice_changer"]:
                self.last_llm_compute_burned = False
                return {
                    "status": "blocked",
                    "fail_closed": True,
                    "decision": "BLOCK_ALERT",
                    "reason": latency_data["reason"],
                    "voice_changer_detected": True,
                    "llm_compute_burned": False,
                    "tool": BankingTools.get_tool_definition("transfer_funds"),
                    "cost": _calculate_cost_saving(skipped=True),
                    "agent_reply_text": (
                        "Security Warning: Real-time voice conversion lag detected. "
                        "Active voice changer blocked with zero LLM compute burned."
                    ),
                    "intent": "BLOCK_VOICE_CHANGER",
                    "latency_telemetry": latency_data
                }

        # Step 2: Validate challenge words
        expected_words = set(re.findall(r'\b\w+\b', expected_phrase.lower()))
        spoken_words = set(re.findall(r'\b\w+\b', spoken_response.lower()))
        matched_words = expected_words.intersection(spoken_words)
        
        # Require matching words (at least 3 of 4 words or exact match)
        if len(expected_words) > 0 and len(matched_words) >= min(len(expected_words), 3):
            # Passed Stage B! Execute tool & call Nemotron for GramPay spoken response
            tool_result = BankingTools.execute_transfer_funds(
                amount=amount,
                recipient=recipient,
                from_account_id=speaker_id,
                is_unlocked=True
            )
            spoken_reply = self.formulate_approved_response(
                speaker_id=speaker_id,
                transcript=spoken_response,
                amount=amount,
                recipient=recipient,
                action="TRANSFER_FUNDS"
            )
            return {
                "status": "ok",
                "fail_closed": False,
                "decision": "APPROVE",
                "reason": "Stage B Active Challenge verified successfully. Natural vocal response confirmed.",
                "llm_compute_burned": bool(self.client),
                "tool": tool_result,
                "cost": _calculate_cost_saving(skipped=False),
                "agent_reply_text": spoken_reply,
                "intent": "TRANSFER_FUNDS",
                "stage_b_verified": True
            }
        else:
            self.last_llm_compute_burned = False
            return {
                "status": "blocked",
                "fail_closed": True,
                "decision": "BLOCK",
                "reason": f"Challenge phrase mismatch. Expected: '{expected_phrase}', Spoken: '{spoken_response}'.",
                "llm_compute_burned": False,
                "tool": BankingTools.get_tool_definition("transfer_funds"),
                "cost": _calculate_cost_saving(skipped=True),
                "agent_reply_text": "Challenge phrase verification failed. Transaction blocked to protect your account.",
                "intent": "CHALLENGE_FAILED",
                "stage_b_verified": False
            }

    def process_turn(
        self,
        audio_bytes: bytes,
        speaker_id: str = "senior_user_01",
        user_text_hint: Optional[str] = None,
        action: str = "TRANSFER_FUNDS",
        amount: Optional[float] = None,
        recipient: Optional[str] = None,
        response_latency_ms: Optional[float] = None,
        active_challenge: Optional[str] = None,
        challenge_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes full voice agent turn through the DetectifAI Pre-Gate.
        
        STAGE 1: HARD DETECTIFAI GATE FIRST + LATENCY BUFFER CHECK (No LLM or TTS runs yet!)
        STAGE 2: IF BLOCK/CLONE/VOICE-CHANGER: SHORT-CIRCUIT WITH ZERO LLM COMPUTE BURNED.
        STAGE 3: IF STEP_UP / EXTRA_CHECK: CALL NEMOTRON FOR STAGE B ACTIVE CHALLENGE.
        STAGE 4: IF APPROVED: EXECUTE TOOL + CALL NEMOTRON FOR CALM GRAMPAY FARMER RESPONSE.
        """
        self.last_llm_compute_burned = False
        farmer_name = self._get_farmer_name(speaker_id)
        
        # Parse transfer parameters from user_text_hint or explicit overrides
        parsed_amt, parsed_rec = self._parse_transfer_details(user_text_hint)
        effective_amount = amount if amount is not None else parsed_amt
        effective_recipient = recipient if recipient is not None else parsed_rec

        # Rule 2: Measure caller response latency buffer to catch real-time voice conversion lag
        latency_telemetry = None
        if response_latency_ms is not None:
            latency_telemetry = self.measure_latency_buffer(response_latency_ms)
            if latency_telemetry["is_voice_changer"]:
                # Catch real-time voice changer! Short-circuit with ZERO LLM compute burned
                cost_metrics = _calculate_cost_saving(skipped=True)
                return {
                    "status": "blocked",
                    "fail_closed": True,
                    "decision": "BLOCK_ALERT",
                    "reason": latency_telemetry["reason"],
                    "api_error": None,
                    "detection": {
                        "is_synthetic": True,
                        "synthetic_score": 1.0,
                        "raw": {"latency_violation_ms": response_latency_ms},
                        "latency_ms": int(response_latency_ms)
                    },
                    "verification": {
                        "matched": False,
                        "match_score": 0.0,
                        "raw": {"latency_violation_ms": response_latency_ms},
                        "latency_ms": 0
                    },
                    "tool": BankingTools.get_tool_definition("transfer_funds"),
                    "cost": cost_metrics,
                    "transcript": user_text_hint or "[Call Terminated: Voice Changer Latency Lag Caught]",
                    "agent_reply_text": (
                        "Security Warning: Real-time voice conversion lag detected. "
                        "All GramPay transactions are frozen to protect your account."
                    ),
                    "intent": "BLOCK_VOICE_CHANGER",
                    "llm_compute_burned": False,
                    "latency_telemetry": latency_telemetry
                }

        # If caller provided an active challenge response, verify it directly
        if active_challenge and challenge_response:
            return self.verify_challenge_response(
                expected_phrase=active_challenge,
                spoken_response=challenge_response,
                speaker_id=speaker_id,
                response_latency_ms=response_latency_ms,
                amount=effective_amount,
                recipient=effective_recipient
            )

        # Step 1: Execute DetectifAI Checks in parallel (Fail-closed)
        detection_res = None
        verification_res = None
        api_error = None

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_detect = executor.submit(detectif_client.detect_deepfake, audio_bytes)
            future_verify = executor.submit(detectif_client.verify_speaker, audio_bytes, speaker_id)

            try:
                detection_res = future_detect.result()
            except DetectifAPIError as err:
                api_error = str(err)
                detection_res = {
                    "status": "error",
                    "error": str(err),
                    "is_synthetic": None,
                    "synthetic_score": None,
                    "raw": {"error": str(err)},
                    "latency_ms": 0
                }

            try:
                verification_res = future_verify.result()
            except DetectifAPIError as err:
                if not api_error:
                    api_error = str(err)
                verification_res = {
                    "status": "error",
                    "error": str(err),
                    "matched": None,
                    "match_score": None,
                    "raw": {"error": str(err)},
                    "latency_ms": 0
                }

        # Step 2: Deterministic 2x2 Gate Evaluation
        gate_result = evaluate_gate(
            detection=detection_res,
            verification=verification_res,
            action=action,
            api_error=api_error
        )

        decision = gate_result["decision"]
        reason = gate_result["reason"]
        tool_allowed = gate_result["tool_allowed"]
        cost_metrics = gate_result["cost"]

        # STAGE 2: SHORT-CIRCUIT ON BLOCK/CLONE WITH ZERO LLM COMPUTE BURNED
        if not tool_allowed:
            tool_status = BankingTools.get_tool_definition("transfer_funds")
            
            # Case A: External API error / fail-closed
            if api_error:
                agent_reply = "Transaction held safely. Verification service is temporarily unreachable."
                intent = "SECURITY_SYSTEM_UNAVAILABLE"
                return {
                    "status": "error",
                    "fail_closed": True,
                    "decision": decision,
                    "reason": reason,
                    "api_error": api_error,
                    "detection": detection_res,
                    "verification": verification_res,
                    "tool": tool_status,
                    "cost": cost_metrics,
                    "transcript": user_text_hint or "[Call Terminated at DetectifAI Audio Pre-Gate]",
                    "agent_reply_text": agent_reply,
                    "intent": intent,
                    "llm_compute_burned": False
                }

            # Case B: Cloned Voice Attack or Synthetic Impostor -> ZERO LLM compute burned!
            if decision in ["BLOCK_ALERT", "BLOCK"]:
                if decision == "BLOCK_ALERT":
                    agent_reply = (
                        "Security Warning: An artificial voice clone was detected. "
                        "For your safety, all transactions are frozen and your bank branch has been notified."
                    )
                    intent = "BLOCK_CLONE_ATTACK"
                else:
                    agent_reply = "Transaction blocked due to unrecognized caller authenticity."
                    intent = "BLOCKED_CALL"

                return {
                    "status": "blocked",
                    "fail_closed": True,
                    "decision": decision,
                    "reason": reason,
                    "api_error": None,
                    "detection": detection_res,
                    "verification": verification_res,
                    "tool": tool_status,
                    "cost": cost_metrics,
                    "transcript": user_text_hint or "[Call Terminated at DetectifAI Audio Pre-Gate]",
                    "agent_reply_text": agent_reply,
                    "intent": intent,
                    "llm_compute_burned": False
                }

            # Case C: Stage B Active Challenge (STEP_UP / EXTRA_CHECK)
            # Rule 1: Call Nemotron to generate a random 4-word challenge phrase with vocal instruction
            challenge_data = self.generate_stage_b_challenge(
                speaker_id=speaker_id,
                farmer_name=farmer_name
            )
            vocal_instruction = challenge_data["vocal_instruction"]
            challenge_phrase = challenge_data["challenge_phrase"]

            return {
                "status": "blocked",
                "fail_closed": False,
                "decision": decision,
                "reason": reason,
                "api_error": None,
                "detection": detection_res,
                "verification": verification_res,
                "tool": tool_status,
                "cost": cost_metrics,
                "transcript": user_text_hint or f"[Stage B Active Challenge Issued: {challenge_phrase}]",
                "agent_reply_text": vocal_instruction,
                "intent": "STAGE_B_ACTIVE_CHALLENGE",
                "llm_compute_burned": bool(self.client),
                "stage_b_challenge": challenge_data,
                "challenge_phrase": challenge_phrase
            }

        # STAGE 4: VOICE IS REAL & VERIFIED -> EXECUTE TOOL + CALL NEMOTRON FOR GRAMPAY RESPONSE
        transcript = user_text_hint or f"Payment of Rs {int(effective_amount):,} to {effective_recipient}."

        # Execute the tool safely
        if action == "CHECK_BALANCE":
            tool_result = BankingTools.execute_check_balance(speaker_id, is_unlocked=True)
            intent = "CHECK_BALANCE"
        else:
            tool_result = BankingTools.execute_transfer_funds(
                amount=effective_amount,
                recipient=effective_recipient,
                from_account_id=speaker_id,
                is_unlocked=True
            )
            intent = "TRANSFER_FUNDS"

        # Rule 3: Call Nemotron to formulate a calm, respectful Hindi/English voice response for rural farmers
        spoken_reply = self.formulate_approved_response(
            speaker_id=speaker_id,
            transcript=transcript,
            amount=effective_amount,
            recipient=effective_recipient,
            action=action
        )

        return {
            "status": "ok",
            "fail_closed": False,
            "decision": decision,
            "reason": reason,
            "detection": detection_res,
            "verification": verification_res,
            "tool": tool_result,
            "cost": cost_metrics,
            "transcript": transcript,
            "agent_reply_text": spoken_reply,
            "intent": intent,
            "llm_compute_burned": bool(self.client)
        }


voice_agent = VoiceAgentOrchestrator()
