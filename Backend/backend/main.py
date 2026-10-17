"""FastAPI REST Server for UnClone Gate.
Implements the exact Section 4 API Contract for UnClone Gate (Track 3: UNCLONE Agents).

CORS restricted to the local frontend.
Deterministic fail-closed behavior on all error paths.
"""

import time
import uuid
import re
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, HTMLResponse
from pydantic import BaseModel

from backend.config import ALLOWED_ORIGIN, NVIDIA_API_KEY, SYNTH_HIGH, SYNTH_LOW, MATCH_HIGH
from backend.audio_prep import prepare_audio_for_detectif, AudioValidationError
from backend.detectif_client import detectif_client, DetectifAPIError, CREDIT_RESERVE_FLOOR
from backend.gate import evaluate_gate
from backend.credentials import credential_service
from backend.audit import (
    log_audit_event,
    get_recent_audit_logs,
    get_telemetry_stats,
    update_audit_challenge,
    reset_audit_logs,
    record_contract_event,
    get_events_since,
    get_contract_stats
)
from backend.agent import voice_agent
from backend.telephony_bridge import telephony_router
from backend.multilingual_config import (
    MULTILINGUAL_CONFIG,
    normalize_lang,
    generate_challenge_words,
    get_localized_reason,
    save_pending_challenge,
    get_pending_challenge,
    remove_pending_challenge
)

# Day 2 Global Editable Assumptions (Defaults: Rs 10/min, 2 minutes saved)

APP_SESSION_EVENT_IDS: set[str] = set()

app = FastAPI(
    title="UnClone Gate API",
    description="Zero-Trust BFSI Voice Agent Security & Cost-Optimization Gateway powered by DetectifAI & NVIDIA Nemotron",
    version="1.0.0"
)

@app.middleware("http")
async def reject_simulated_or_unavailable_routes(request: Request, call_next):
    """Fail closed for mock/demo routes and unintegrated financial actions."""
    path = request.url.path
    if path.startswith(("/api/demo/", "/api/demo-audio/")) or path in ("/api/assumptions", "/api/telephony/simulate"):
        return JSONResponse(status_code=410, content={**make_metadata(), "error": "This endpoint is unavailable.", "fail_closed": True})
    if path in ("/api/pay/upi", "/api/agent/turn", "/api/challenge/verify"):
        return JSONResponse(status_code=501, content={**make_metadata(), "error": "No live financial execution integration is configured.", "fail_closed": True})
    return await call_next(request)

# Mount Telephony Bridge Router (Day 2 Reference Architecture)
app.include_router(telephony_router)

# CORS middleware for Grok frontend and all clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def make_metadata():
    """Generates standard tracking headers for contract responses."""
    return {
        "request_id": f"req_{uuid.uuid4().hex[:12]}",
        "ts": datetime.now(timezone.utc).isoformat()
    }

# Global exception handlers ensuring Section 4 error contract:
# All errors return JSON: { "request_id": "...", "ts": "...", "error": "...", "fail_closed": true }
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    meta = make_metadata()
    error_msg = "; ".join(f"{err.get('loc', ['field'])[-1]}: {err.get('msg', 'invalid')}" for err in exc.errors())
    return JSONResponse(
        status_code=400,
        content={
            **meta,
            "error": f"Validation error: {error_msg}",
            "fail_closed": True
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    meta = make_metadata()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            **meta,
            "error": str(exc.detail),
            "fail_closed": True
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    meta = make_metadata()
    return JSONResponse(
        status_code=500,
        content={
            **meta,
            "error": f"Internal server error: {str(exc)}",
            "fail_closed": True
        }
    )

# ==============================================================================
# Pydantic Request Models
# ==============================================================================
class IssueCredentialRequest(BaseModel):
    agent_id: str
    org: str
    allowed_actions: List[str] = ["TRANSFER_FUNDS", "CHECK_BALANCE"]
    limit_inr: float = 50000.0

class VerifyHandshakeRequest(BaseModel):
    credential: str
    action: Optional[str] = None

class TtsRequest(BaseModel):
    text: str
    lang: Optional[str] = "kn"

# ==============================================================================
# 1. Health & Telemetry Verification
# ==============================================================================
@app.get("/api/health")
async def get_health():
    """Lightweight check of DetectifAI provider reachability.
    Section 4 Contract: { 'request_id': '...', 'ts': '...', 'ok': true, 'detectif_reachable': true|false }
    """
    meta = make_metadata()
    reachable, detectif_details = detectif_client.check_health()
    return {
        **meta,
        "ok": reachable,
        "detectif_reachable": reachable,
        "detectif_details": detectif_details,
        "nemotron_configured": bool(NVIDIA_API_KEY)
    }

@app.get("/v1/credits")
@app.get("/api/credits")
async def get_credits_endpoint():
    """Returns available DetectifAI credits for the live account.
    Guarantees Credit Guardian status: reserve_protected=True when remaining >= 3000.
    """
    meta = make_metadata()
    try:
        credits_data = detectif_client.get_credits()
        avail = credits_data.get("available")
        if avail is None:
            avail = detectif_client.remaining_credits
        unlimited = bool(credits_data.get("unlimited"))
        remaining_credits = int(avail) if avail is not None else None
        reserve_protected = unlimited or bool(remaining_credits is not None and remaining_credits > CREDIT_RESERVE_FLOOR)
        return {
            **meta,
            "status": "ok",
            **credits_data,
            "credits": remaining_credits,
            "credits_remaining": remaining_credits,
            "remaining": remaining_credits,
            "reserve_floor": CREDIT_RESERVE_FLOOR,
            "reserve_protected": reserve_protected,
            "circuit_breaker_active": not unlimited and remaining_credits is not None and remaining_credits <= CREDIT_RESERVE_FLOOR,
        }
    except DetectifAPIError as e:
        return JSONResponse(
            status_code=502,
            content={**meta, "error": f"DetectifAI Credits query failed: {str(e)}", "fail_closed": True}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={**meta, "error": f"Internal error querying credits: {str(e)}", "fail_closed": True}
        )


# ==============================================================================
# 2. Speaker Enrollment (/api/enroll)
# ==============================================================================
@app.post("/api/enroll")
async def enroll_speaker_endpoint(
    request: Request,
    audio: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    name: Optional[str] = Form(None),
    speaker_name: Optional[str] = Form(None),
    speaker_id: Optional[str] = Form(None),
    lang: Optional[str] = Form("kn")
):
    """Enrolls a customer's live voice into DetectifAI Eidos engine."""
    meta = make_metadata()
    audio_upload = audio or file
    if not audio_upload:
        return JSONResponse(
            status_code=400,
            content={**meta, "error": "Missing audio file in form data (expected 'audio' or 'file')", "fail_closed": True}
        )
    target_name = name or speaker_name or speaker_id or "Account_holder"
    normalized_language = normalize_lang(lang)

    try:
        raw_bytes = await audio_upload.read()
        prep_bytes, mime_type, filename = prepare_audio_for_detectif(raw_bytes, audio_upload.filename or "enroll.wav")
        detectif_client.get_credits(force_refresh=True)

        result = detectif_client.enroll_speaker(
            audio_bytes=prep_bytes,
            speaker_name=target_name,
            filename=filename,
        )

        credits_remaining = detectif_client.remaining_credits

        return {
            **meta,
            **result,
            "speaker_id": result.get("speaker_id") or target_name,
            "name": target_name,
            "lang": normalized_language,
            "latency_ms": result.get("latency_ms", 0),
            "credits_remaining": credits_remaining
        }
    except AudioValidationError as e:
        return JSONResponse(
            status_code=400,
            content={**meta, "error": f"Audio validation error: {str(e)}", "fail_closed": True}
        )
    except DetectifAPIError as e:
        return JSONResponse(
            status_code=502,
            content={**meta, "error": f"DetectifAI enrollment error: {str(e)}", "fail_closed": True}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={**meta, "error": f"Internal server error: {str(e)}", "fail_closed": True}
        )

# ==============================================================================
# 3. Dual-Gate Audio Check (/api/check)
# ==============================================================================
@app.post("/api/check")
async def check_audio_endpoint(
    request: Request,
    audio: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    speaker_id: str = Form("senior_user_01"),
    action: str = Form("VOICE_VERIFY"),
    amount: Optional[float] = Form(None),
    lang: Optional[str] = Form("kn"),
    device: Optional[str] = Form("phone1"),
    source: Optional[str] = Form("live_mic")
):
    """Executes parallel DetectifAI Aletheia + Eidos evaluation and applies the Day 2 Contract Gate."""
    meta = make_metadata()
    audio_upload = audio or file
    if not audio_upload:
        return JSONResponse(
            status_code=400,
            content={**meta, "error": "Missing audio file in form data (expected 'audio' or 'file')", "fail_closed": True}
        )
    
    norm_lang = normalize_lang(lang)
    device_id = device or "phone1"
    audio_source = source or "live_mic"
    event_id = meta["request_id"]

    try:
        raw_bytes = await audio_upload.read()
        prep_bytes, mime_type, filename = prepare_audio_for_detectif(raw_bytes, audio_upload.filename or "check.wav")
        
        # Read live credits before inference
        initial_credits = detectif_client.remaining_credits
        try:
            credits_data = detectif_client.get_credits(force_refresh=True)
            initial_credits = credits_data.get("available", initial_credits)
        except Exception as err:
            return JSONResponse(
                status_code=503,
                content={**meta, "error": f"Cannot confirm DetectifAI credits; audio was not analyzed. {err}", "fail_closed": True}
            )

        detection_res = None
        verification_res = None
        api_error = None

        # Execute Deepfake Detection & Speaker Verification in parallel
        # Note: perf_counter inside detectif_client wraps strictly the HTTP inference call
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_detect = executor.submit(detectif_client.detect_deepfake, prep_bytes, filename)
            future_verify = executor.submit(detectif_client.verify_speaker, prep_bytes, speaker_id, filename)

            try:
                detection_res = future_detect.result()
            except Exception as err:
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
            except Exception as err:
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

        # ----------------------------------------------------------------------
        # Measure Gate Overhead Separately
        # ----------------------------------------------------------------------
        t_gate_start = time.perf_counter()

        synth_val = detection_res.get("synthetic_score") if detection_res.get("synthetic_score") is not None else detection_res.get("score")
        match_val = verification_res.get("match_score") if verification_res.get("match_score") is not None else (verification_res.get("similarity") if verification_res.get("similarity") is not None else verification_res.get("score"))
        synth_score = float(synth_val) if synth_val is not None else None
        match_score = float(match_val) if match_val is not None else None

        # Day 2 Contract Gate Decision Logic
        if api_error or synth_score is None or match_score is None:
            decision = "BLOCK"
            reason_key = "api_error"
        elif detection_res.get("verdict") == "not_sure":
            decision = "EXTRA_CHECK"
            reason_key = "uncertain_challenge"
        elif detection_res.get("verdict") == "fake" or detection_res.get("is_synthetic") is True or synth_score >= float(detection_res.get("threshold", SYNTH_HIGH)):
            decision = "BLOCK"
            reason_key = "synthetic_blocked"
        elif synth_score >= SYNTH_LOW:
            decision = "EXTRA_CHECK"
            reason_key = "uncertain_challenge"
        elif match_score < float(verification_res.get("threshold", MATCH_HIGH)):
            decision = "EXTRA_CHECK"
            reason_key = "speaker_mismatch"
        else:
            decision = "PAY"
            reason_key = "approved"

        gate_overhead_ms = round((time.perf_counter() - t_gate_start) * 1000, 2)

        # ----------------------------------------------------------------------
        # Order of Operations: DetectifAI runs FIRST.
        # Run STT & Intent ONLY after a final PAY or prepare challenge for EXTRA_CHECK.
        # A BLOCK skips all paid speech/LLM steps.
        # ----------------------------------------------------------------------
        challenge_payload = None
        transcript_payload = None
        intent_payload = None

        if decision == "EXTRA_CHECK":
            ch_data = generate_challenge_words(norm_lang)
            ch_id = ch_data["challenge_id"]
            # Bind this follow-up check to the first voice recording and profile.
            save_pending_challenge(
                challenge_id=ch_id,
                audio_bytes=raw_bytes,
                speaker_id=speaker_id,
                lang=norm_lang,
                device=device_id,
                source=audio_source
            )
            challenge_payload = {
                "challenge_id": ch_id,
                "words": ch_data["words"],
                "lang": norm_lang
            }
            tool_status = "LOCKED"
            steps_skipped = 0

        elif decision == "PAY":
            # This endpoint verifies voice identity only. No speech-to-text or
            # downstream payment integration is configured, so never invent an
            # order transcript, amount, or payee.
            tool_status = "VOICE_VERIFIED"
            steps_skipped = 0

        else: # BLOCK
            # Fraudulent/Synthetic: short-circuit all downstream LLM/STT compute
            tool_status = "LOCKED"
            steps_skipped = 1

        localized_reason = get_localized_reason(reason_key, norm_lang)
        credits_remaining = detectif_client.remaining_credits

        # Build Contract Response Object
        contract_response = {
            "event_id": event_id,
            "device": device_id,
            "source": audio_source,
            "lang": norm_lang,
            "decision": decision,
            "reason_key": reason_key,
            "detection": {
                "is_synthetic": None if detection_res.get("verdict") == "not_sure" else (detection_res.get("is_synthetic") if detection_res.get("is_synthetic") is not None else ((synth_score >= float(detection_res.get("threshold", SYNTH_HIGH))) if synth_score is not None else None)),
                "synthetic_score": synth_score,
                "verdict": detection_res.get("verdict"),
                "threshold": detection_res.get("threshold", SYNTH_HIGH),
                "latency_ms": detection_res.get("latency_ms", 0),
                "raw": detection_res.get("raw", {})
            },
            "verification": {
                "matched": verification_res.get("matched") if verification_res.get("matched") is not None else ((match_score >= float(verification_res.get("threshold", MATCH_HIGH))) if match_score is not None else None),
                "match_score": match_score,
                "threshold": verification_res.get("threshold", MATCH_HIGH),
                "latency_ms": verification_res.get("latency_ms", 0),
                "raw": verification_res.get("raw", {})
            },
            "gate_overhead_ms": gate_overhead_ms,
            "challenge": challenge_payload,
            "transcript": transcript_payload,
            "intent": intent_payload,
            "tool": {
                "name": "downstream_action",
                "status": tool_status,
                "result": None
            },
            "cost": {
                "steps_skipped": steps_skipped,
                "agent_steps_skipped": steps_skipped
            },
            "credits_remaining": credits_remaining,
            "badge": "VERIFIED_AGENT" if decision == "PAY" else None
        }

        # Record in SQLite Audit Table
        record_contract_event(contract_response)
        APP_SESSION_EVENT_IDS.add(event_id)

        # Include Day 1 backwards-compatibility keys
        contract_response.update({
            **meta,
            "status": "error" if api_error else "ok",
            "fail_closed": bool(api_error or decision in ("BLOCK", "EXTRA_CHECK")),
            "reason": localized_reason,
            "api_error": api_error,
            "audit_id": event_id
        })

        return contract_response

    except AudioValidationError as e:
        return JSONResponse(
            status_code=400,
            content={**meta, "error": f"Audio format error: {str(e)}", "fail_closed": True}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={**meta, "error": f"Server error: {str(e)}", "fail_closed": True}
        )


# ==============================================================================
# 3b. Tier-2 Active Challenge Submission (/api/challenge/submit)
# ==============================================================================
@app.post("/api/challenge/submit")
async def submit_challenge_endpoint(
    request: Request,
    audio: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    challenge_id: str = Form(...),
    speaker_id: str = Form("senior_user_01"),
    response_delay_ms: Optional[float] = Form(None)
):
    """Rechecks a pending caller voice challenge without executing a payment.

    Response delay is recorded as telemetry only. Challenges are bound to the
    original speaker profile and expire after two minutes.
    """
    meta = make_metadata()
    if not re.fullmatch(r"ch_[a-f0-9]{12}", challenge_id or ""):
        return JSONResponse(
            status_code=410,
            content={**meta, "error": "This voice challenge is invalid or expired. Start a new voice check.", "fail_closed": True}
        )
    audio_upload = audio or file
    if not audio_upload:
        return JSONResponse(
            status_code=400,
            content={**meta, "error": "Missing audio file in form data", "fail_closed": True}
        )

    # Look up the pending first-pass voice check for this caller/profile.
    cached_first = get_pending_challenge(challenge_id)
    if not cached_first or time.time() - float(cached_first.get("created_at", 0)) > 120:
        remove_pending_challenge(challenge_id)
        return JSONResponse(
            status_code=410,
            content={**meta, "error": "This voice challenge expired. Start a new voice check.", "fail_closed": True}
        )
    if speaker_id != cached_first.get("speaker_id"):
        return JSONResponse(
            status_code=403,
            content={**meta, "error": "The voice challenge belongs to a different voice profile.", "fail_closed": True}
        )
    lang = cached_first.get("lang", "kn")
    device = cached_first.get("device", "phone1")
    source = cached_first.get("source", "live_mic")
    event_id = meta["request_id"]

    try:
        raw_challenge_bytes = await audio_upload.read()
        prep_bytes, mime_type, filename = prepare_audio_for_detectif(raw_challenge_bytes, audio_upload.filename or "challenge.wav")

        initial_credits = detectif_client.remaining_credits
        try:
            credits_data = detectif_client.get_credits(force_refresh=True)
            initial_credits = credits_data.get("available", initial_credits)
        except Exception as err:
            remove_pending_challenge(challenge_id)
            return JSONResponse(
                status_code=503,
                content={**meta, "error": f"Cannot confirm DetectifAI credits; audio was not analyzed. {err}", "fail_closed": True}
            )

        detection_res = None
        verification_res = None
        api_error = None

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_detect = executor.submit(detectif_client.detect_deepfake, prep_bytes, filename)
            future_verify = executor.submit(detectif_client.verify_speaker, prep_bytes, speaker_id, filename)

            try:
                detection_res = future_detect.result()
            except DetectifAPIError as err:
                api_error = str(err)
                detection_res = {"status": "error", "error": str(err), "synthetic_score": None, "latency_ms": 0, "raw": {}}

            try:
                verification_res = future_verify.result()
            except DetectifAPIError as err:
                if not api_error:
                    api_error = str(err)
                verification_res = {"status": "error", "error": str(err), "match_score": None, "latency_ms": 0, "raw": {}}

        t_gate_start = time.perf_counter()
        synth_val = detection_res.get("synthetic_score") if detection_res.get("synthetic_score") is not None else detection_res.get("score")
        match_val = verification_res.get("match_score") if verification_res.get("match_score") is not None else (verification_res.get("similarity") if verification_res.get("similarity") is not None else verification_res.get("score"))
        synth_score = float(synth_val) if synth_val is not None else None
        match_score = float(match_val) if match_val is not None else None

        # Second pass decides:
        # Pass -> PAY, otherwise BLOCK. Never block on response delay.
        if api_error or synth_score is None or match_score is None:
            decision = "BLOCK"
            reason_key = "challenge_failed"
        elif detection_res.get("verdict") == "not_sure":
            decision = "BLOCK"
            reason_key = "challenge_failed"
        elif detection_res.get("verdict") == "fake" or detection_res.get("is_synthetic") is True or synth_score >= float(detection_res.get("threshold", SYNTH_HIGH)):
            decision = "BLOCK"
            reason_key = "synthetic_blocked"
        elif synth_score < SYNTH_LOW and match_score >= float(verification_res.get("threshold", MATCH_HIGH)):
            decision = "PAY"
            reason_key = "approved"
        else:
            decision = "BLOCK"
            reason_key = "challenge_failed"

        gate_overhead_ms = round((time.perf_counter() - t_gate_start) * 1000, 2)

        transcript_payload = None
        intent_payload = None

        if decision == "PAY":
            # Challenge approval is a voice check only. Do not derive fake
            # transaction details from a canned transcript.
            tool_status = "VOICE_VERIFIED"
            steps_skipped = 0
        else:
            tool_status = "LOCKED"
            steps_skipped = 1

        # Cleanup cached challenge
        remove_pending_challenge(challenge_id)
        credits_remaining = detectif_client.remaining_credits

        contract_response = {
            "event_id": event_id,
            "device": device,
            "source": source,
            "lang": lang,
            "decision": decision,
            "reason_key": reason_key,
            "detection": {
                "is_synthetic": None if detection_res.get("verdict") == "not_sure" else (detection_res.get("is_synthetic") if detection_res.get("is_synthetic") is not None else ((synth_score >= float(detection_res.get("threshold", SYNTH_HIGH))) if synth_score is not None else None)),
                "synthetic_score": synth_score,
                "verdict": detection_res.get("verdict"),
                "threshold": detection_res.get("threshold", SYNTH_HIGH),
                "latency_ms": detection_res.get("latency_ms", 0),
                "raw": detection_res.get("raw", {})
            },
            "verification": {
                "matched": verification_res.get("matched") if verification_res.get("matched") is not None else ((match_score >= float(verification_res.get("threshold", MATCH_HIGH))) if match_score is not None else None),
                "match_score": match_score,
                "threshold": verification_res.get("threshold", MATCH_HIGH),
                "latency_ms": verification_res.get("latency_ms", 0),
                "raw": verification_res.get("raw", {})
            },
            "gate_overhead_ms": gate_overhead_ms,
            "response_delay_ms": response_delay_ms,
            "challenge": None,
            "transcript": transcript_payload,
            "intent": intent_payload,
            "tool": {
                "name": "downstream_action",
                "status": tool_status,
                "result": None
            },
            "cost": {
                "steps_skipped": steps_skipped,
                "agent_steps_skipped": steps_skipped
            },
            "credits_remaining": credits_remaining,
            "badge": "VERIFIED_AGENT" if decision == "PAY" else None
        }

        record_contract_event(contract_response)
        APP_SESSION_EVENT_IDS.add(event_id)
        contract_response.update({
            **meta,
            "status": "error" if api_error else "ok",
            "fail_closed": bool(api_error or decision == "BLOCK"),
            "reason": get_localized_reason(reason_key, lang)
        })

        return contract_response

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={**meta, "error": f"Challenge verification error: {str(e)}", "fail_closed": True}
        )


# ==============================================================================
# 3c. Console Polling Latest State (/api/latest-state)
# ==============================================================================
# ==============================================================================
def _session_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate only recorded events created by this server process."""
    return {
        "checks_run": len(rows),
        "clones_blocked": sum(1 for row in rows if row.get("decision") in ("BLOCK", "BLOCK_ALERT")),
        "agent_steps_skipped": sum(int(row.get("steps_skipped") or 0) for row in rows),
        "agent_time_saved_inr": None,
    }

def _get_session_rows() -> List[Dict[str, Any]]:
    """Return only audit records created by this running API process."""
    return [row for row in get_recent_audit_logs(limit=10000) if row.get("event_id") in APP_SESSION_EVENT_IDS]

@app.get("/api/latest-state")
async def get_latest_state_endpoint(since: Optional[str] = Query(None)):
    """Returns new events since `since_event_id` and updated Slide 4 stats."""
    events = [event for event in get_events_since(since_event_id=since, limit=10000) if event.get("event_id") in APP_SESSION_EVENT_IDS][-50:]
    session_rows = _get_session_rows()
    stats = _session_stats(session_rows)

    credits_remaining = detectif_client.remaining_credits
    try:
        credits_data = detectif_client.get_credits()
        credits_remaining = credits_data.get("available", credits_remaining)
    except Exception:
        pass

    return {
        "events": events,
        "stats": stats,
        "credits_remaining": credits_remaining
    }


# ==============================================================================
# 3e. Localized Challenge Words Generator (/api/challenge/new)
# ==============================================================================
@app.get("/api/challenge/new")
async def get_challenge_new_endpoint(lang: str = Query("kn")):
    """Generates 4 random rural words from the selected language's dictionary."""
    return generate_challenge_words(lang)


# ==============================================================================
# 4. Full Voice Agent Turn (/api/agent/turn)
# ==============================================================================
@app.post("/api/agent/turn")
async def agent_turn_endpoint():
    return JSONResponse(status_code=501, content={**make_metadata(), "error": "No live downstream agent integration is configured.", "fail_closed": True})

# ==============================================================================
# 5. Agent Handshake & Credential Service
# ==============================================================================
@app.post("/api/credential/issue")
async def issue_credential_endpoint(req: IssueCredentialRequest):
    """Issues a signed, expiring, single-use JWT agent credential."""
    meta = make_metadata()
    try:
        token_info = credential_service.issue_credential(
            agent_id=req.agent_id,
            org=req.org,
            allowed_actions=req.allowed_actions,
            limit_inr=req.limit_inr
        )
        return {
            **meta,
            **token_info
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={**meta, "error": f"Credential issuance error: {str(e)}", "fail_closed": True}
        )

@app.post("/api/handshake/verify")
async def verify_handshake_endpoint(req: VerifyHandshakeRequest):
    """Verifies cryptographic signature, expiry, and single-use status (replay prevention)."""
    meta = make_metadata()
    try:
        result = credential_service.verify_handshake(req.credential, required_action=req.action)
        return {
            **meta,
            **result
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={**meta, "error": f"Handshake verification error: {str(e)}", "fail_closed": True}
        )

# ==============================================================================
# 6. Audit & Telemetry Analytics
# ==============================================================================
@app.get("/api/audit")
async def get_audit_endpoint(limit: int = Query(50, ge=1, le=200)):
    """Returns recent verified audit logs for the Judge Console."""
    meta = make_metadata()
    try:
        logs = _get_session_rows()[:limit]
        return {
            **meta,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={**meta, "error": f"Audit query error: {str(e)}", "fail_closed": True}
        )

@app.get("/api/stats")
async def get_stats_endpoint(limit: int = Query(50, ge=1, le=200)):
    """Returns aggregate security counts, approvals, blocks, and saved agent compute costs.
    Guarantees the exact 4 slide counters: checks_run, clones_blocked, agent_steps_skipped, agent_time_saved_inr.
    """
    meta = make_metadata()
    try:
        stats = _session_stats(_get_session_rows())
        return {**meta, **stats}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={**meta, "error": f"Stats query error: {str(e)}", "fail_closed": True}
        )

# ==============================================================================
# GramPay 3-Tier Security Endpoints
# Tier 2: Dynamic Challenge-Response (/api/challenge/generate, /api/challenge/verify)
# Tier 3: NPCI Hello! UPI Payment Tool Call (/api/pay/upi)
# ==============================================================================

ACTIVE_CHALLENGES: Dict[str, Dict[str, Any]] = {}

@app.post("/api/challenge/generate")
async def generate_challenge_endpoint(request: Request):
    """Return a localized four-word prompt for an optional second voice sample."""
    meta = make_metadata()
    try:
        content_type = request.headers.get("content-type", "")
        body = {}
        if "application/json" in content_type:
            try:
                body = await request.json()
            except Exception:
                body = {}
        elif "form" in content_type:
            try:
                form_data = await request.form()
                body = dict(form_data)
            except Exception:
                body = {}
        else:
            try:
                body = await request.json()
            except Exception:
                pass

        speaker_id = body.get("speaker_id") or "senior_user_01"
        language = body.get("language") or "en"
        action = body.get("action") or "TRANSFER_FUNDS"
        try:
            amount = float(body.get("amount", 45000.0))
        except (ValueError, TypeError):
            amount = 45000.0

        phrase = voice_agent.generate_challenge_phrase(language=language)
        challenge_id = f"ch_{uuid.uuid4().hex[:12]}"
        now = time.time()
        expires_at = now + 120.0  # 2 minute expiry window

        ACTIVE_CHALLENGES[challenge_id] = {
            "challenge_id": challenge_id,
            "phrase": phrase,
            "speaker_id": speaker_id,
            "action": action,
            "amount": amount,
            "expires_at": expires_at,
            "created_at": meta["ts"]
        }

        return {
            **meta,
            "status": "ok",
            "challenge_id": challenge_id,
            "phrase": phrase,
            "speaker_id": speaker_id,
            "action": action,
            "amount": amount,
            "valid_seconds": 120,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
            "tier": 2,
            "engine": "NVIDIA Nemotron Dynamic Challenge"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={**meta, "error": f"Challenge generation error: {str(e)}", "fail_closed": True}
        )

@app.post("/api/challenge/verify")
async def verify_challenge_endpoint():
    return JSONResponse(status_code=501, content={**make_metadata(), "error": "No live financial execution integration is configured.", "fail_closed": True})

@app.post("/api/pay/upi")
async def pay_upi_endpoint():
    return JSONResponse(status_code=501, content={**make_metadata(), "error": "No live UPI payment integration is configured.", "fail_closed": True})

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "Frontend"
if not (FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists()):
    FRONTEND_DIR = Path(__file__).resolve().parent.parent / "Frontend"
if not (FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists()):
    FRONTEND_DIR = Path("Frontend").resolve()


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"), media_type="text/html")


@app.get("/app.js")
async def serve_app_js():
    file_path = FRONTEND_DIR / "app.js"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="app.js not found")
    return Response(content=file_path.read_text(encoding="utf-8"), media_type="application/javascript")


@app.get("/styles.css")
async def serve_styles_css():
    file_path = FRONTEND_DIR / "styles.css"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="styles.css not found")
    return Response(content=file_path.read_text(encoding="utf-8"), media_type="text/css")


@app.get("/strings.js")
async def serve_strings_js():
    file_path = FRONTEND_DIR / "strings.js"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="strings.js not found")
    return Response(content=file_path.read_text(encoding="utf-8"), media_type="application/javascript")


@app.get("/audio_recorder.js")
async def serve_audio_recorder_js():
    file_path = FRONTEND_DIR / "audio_recorder.js"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="audio_recorder.js not found")
    return Response(content=file_path.read_text(encoding="utf-8"), media_type="application/javascript")


@app.get("/GramPay_Executive_Summary_and_Architecture.pdf")
async def serve_pdf():
    pdf_path = FRONTEND_DIR / "GramPay_Executive_Summary_and_Architecture.pdf"
    if not pdf_path.exists():
        alt_pdf = Path(__file__).resolve().parent.parent / "GramPay_Executive_Summary_and_Architecture.pdf"
        if alt_pdf.exists():
            pdf_path = alt_pdf
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="GramPay_Executive_Summary_and_Architecture.pdf not found")
    return Response(content=pdf_path.read_bytes(), media_type="application/pdf")


@app.get("/qr_code_phone.svg")
@app.get("/api/qr-code.svg")
async def serve_qr_code(request: Request, url: Optional[str] = None):
    target_url = url
    if not target_url:
        host = request.headers.get("host", "127.0.0.1:8000")
        target_url = f"http://{host}/?mode=caller"
    try:
        import qrcode
        import qrcode.image.svg
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(target_url)
        qr.make(fit=True)
        img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        return Response(content=img.to_string(), media_type="image/svg+xml")
    except Exception:
        fallback_file = FRONTEND_DIR / "qr_code_phone.svg"
        if fallback_file.exists():
            return Response(content=fallback_file.read_bytes(), media_type="image/svg+xml")
        raise HTTPException(status_code=500, detail="Could not generate QR code")



@app.get("/audio/{filename}")
async def serve_audio_file(filename: str):
    file_path = FRONTEND_DIR / "audio" / filename
    if not file_path.exists():
        file_path = FRONTEND_DIR / "data_audio" / filename
    if not file_path.exists():
        file_path = Path(__file__).resolve().parent.parent / "data_audio" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return Response(content=file_path.read_bytes(), media_type="audio/wav")


@app.get("/data_audio/{filename}")
async def serve_data_audio_file(filename: str):
    file_path = FRONTEND_DIR / "data_audio" / filename
    if not file_path.exists():
        file_path = FRONTEND_DIR / "audio" / filename
    if not file_path.exists():
        file_path = Path(__file__).resolve().parent.parent / "data_audio" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return Response(content=file_path.read_bytes(), media_type="audio/wav")


@app.get("/clips/{file_path:path}")
async def serve_clips_file(file_path: str):
    p = FRONTEND_DIR / "clips" / file_path
    if not p.exists():
        p = Path(__file__).resolve().parent.parent / "clips" / file_path
    if not p.exists():
        raise HTTPException(status_code=404, detail="Audio clip not found")
    return Response(content=p.read_bytes(), media_type="audio/wav")
