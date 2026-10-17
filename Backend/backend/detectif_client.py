"""DetectifAI Platform Client (OpenAPI 3.1.0 Specification).
THE SOLE MODULE IN THE SYSTEM THAT COMMUNICATES WITH DetectifAI APIs.

Conforms strictly to:
- Official DetectifAI OpenAPI 3.1.0 specification (https://platform.detectif.ai/openapi.json)
- Base URL: https://platform.detectif.ai/v1
- Hackathon Rule 5.4:
  * ZERO mocked, hardcoded, or synthetic scores under any circumstances.
  * Every score and metric is parsed strictly from live upstream API responses.
  * Deterministic fail-closed error handling on any API fault, timeout, or missing field.
"""

import logging
import math
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from backend.config import (
    DETECTIF_API_KEY,
    DETECTIF_BASE_URL,
    DETECTIF_TIMEOUT_SECONDS,
    CREDIT_RESERVE_FLOOR,
    MATCH_HIGH,
    SYNTH_HIGH,
)

logger = logging.getLogger("detectif_client")

class DetectifAPIError(Exception):
    """Raised when an interaction with DetectifAI fails, times out, or returns invalid telemetry.
    Adheres strictly to Rule 5.4: Fails closed deterministically with zero mock data.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None,
        request_id: Optional[str] = None,
        raw_body: Optional[str] = None,
        raw_json: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.error_type = error_type
        self.request_id = request_id
        self.raw_body = raw_body
        self.raw_json = raw_json


class DetectifClient:
    """Client for the DetectifAI Developer API v1.0.0 (OpenAPI 3.1.0).
    Default Base URL: https://platform.detectif.ai/v1
    Equipped with Credit Guardian & Circuit Breaker preserving 3,000 credits for judge demos.
    """

    def __init__(
        self,
        api_key: str = DETECTIF_API_KEY,
        base_url: str = DETECTIF_BASE_URL,
        timeout: float = DETECTIF_TIMEOUT_SECONDS,
        credit_reserve_floor: int = CREDIT_RESERVE_FLOOR,
        initial_credits: Optional[int] = None,
    ):
        self.api_key = api_key.strip() if api_key else ""
        raw_base = (base_url or "https://platform.detectif.ai/v1").rstrip("/")
        self.base_url = raw_base
        self.timeout = timeout
        self.credit_reserve_floor = credit_reserve_floor
        self.remaining_credits: Optional[int] = (
            initial_credits
            if initial_credits is not None
            else (int(os.getenv("DETECTIF_INITIAL_CREDITS")) if os.getenv("DETECTIF_INITIAL_CREDITS") else None)
        )

    def _update_tracked_credits(self, credits_info: Any) -> None:
        """Tracks remaining credits from DetectifAI responses or /v1/credits."""
        if credits_info is None:
            return
        if isinstance(credits_info, dict):
            for k in ("balance", "available", "remaining", "credits"):
                val = credits_info.get(k)
                if val is not None:
                    try:
                        self.remaining_credits = int(val)
                        return
                    except (ValueError, TypeError):
                        pass
        elif isinstance(credits_info, (int, float)):
            self.remaining_credits = int(credits_info)

    def is_circuit_breaker_active(self, is_demo: bool = False) -> bool:
        """Returns true when the configured credit reserve prohibits provider calls."""
        # Forced circuit breaker testing flag
        if os.getenv("FORCE_CIRCUIT_BREAKER", "").lower() in ("1", "true", "yes"):
            return True

        # Circuit breaker trips when remaining credits are at or below reserve floor
        if self.remaining_credits is not None and self.remaining_credits <= self.credit_reserve_floor:
            return True

        return False

    def _ensure_live_analysis_allowed(self, operation: str, is_demo: bool = False) -> None:
        """Never return a fabricated result when live analysis is blocked."""
        if self.is_circuit_breaker_active(is_demo=is_demo):
            raise DetectifAPIError(
                f"Live DetectifAI {operation} was not run because the credit reserve "
                f"floor ({self.credit_reserve_floor}) is active; no voice classification is available."
            )

    def _url(self, endpoint: str) -> str:
        """Constructs full URL guaranteeing the /v1 prefix defined in OpenAPI 3.1.0."""
        ep = endpoint.lstrip("/")
        base = self.base_url.rstrip("/")
        if base.endswith("/v1"):
            if ep.startswith("v1/"):
                ep = ep[3:]
            return f"{base}/{ep}"
        else:
            if not ep.startswith("v1/"):
                ep = f"v1/{ep}"
            return f"{base}/{ep}"

    def _get_headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        """Assembles standard bearer authorization and idempotency headers."""
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "UnClone-Gate-BFSI/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        if idempotency_key:
            headers["Idempotency-Key"] = str(idempotency_key)
        return headers

    def _raise_for_error(self, resp: requests.Response) -> None:
        """Parses DetectifAI OpenAPI 3.1.0 Error envelope:
        {"error": {"type": str, "code": str, "message": str, "param": Optional[str]}, "request_id": str}
        """
        status_code = resp.status_code
        raw_body = resp.text
        error_code: Optional[str] = None
        error_type: Optional[str] = None
        request_id: Optional[str] = resp.headers.get("X-Request-Id")
        raw_json: Optional[Dict[str, Any]] = None
        message = f"DetectifAI request failed with HTTP {status_code}"

        try:
            data = resp.json()
            if isinstance(data, dict):
                raw_json = data
                if data.get("request_id"):
                    request_id = str(data["request_id"])
                err = data.get("error")
                if isinstance(err, dict):
                    error_code = err.get("code")
                    error_type = err.get("type")
                    err_msg = err.get("message")
                    param = err.get("param")
                    prefix = f"DetectifAI Error ({error_code or error_type or status_code})"
                    if err_msg:
                        message = f"{prefix}: {err_msg}"
                        if param:
                            message += f" [param: {param}]"
                    else:
                        message = f"{prefix}: HTTP {status_code}"
                elif isinstance(data.get("message"), str):
                    message = f"DetectifAI Error: {data['message']}"
        except Exception:
            if raw_body:
                message = f"DetectifAI request failed with HTTP {status_code}: {raw_body[:200]}"

        raise DetectifAPIError(
            message=message,
            status_code=status_code,
            error_code=error_code,
            error_type=error_type,
            request_id=request_id,
            raw_body=raw_body,
            raw_json=raw_json,
        )

    def is_configured(self) -> bool:
        """Checks if a valid, non-placeholder API key has been supplied."""
        return bool(self.api_key and self.api_key != "your_detectifai_api_key_here")

    # ==========================================================================
    # 1. Health & Status (GET /v1/health)
    # ==========================================================================
    def check_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Lightweight reachability check to DetectifAI platform.
        Adheres to Rule 5.4: Fails closed and reports reachable=False if unconfigured.
        """
        if not self.is_configured():
            return False, {
                "reachable": False,
                "reason": "DETECTIF_API_KEY is not configured in .env",
                "base_url": self.base_url,
            }

        now = time.time()
        if hasattr(self, "_last_health_ts") and (now - self._last_health_ts < 5.0) and hasattr(self, "_last_health_result"):
            return self._last_health_result

        start_time = time.perf_counter()
        try:
            url = self._url("/health")
            # GET /v1/health requires no auth per OpenAPI spec
            resp = requests.get(url, headers={"Accept": "application/json"}, timeout=3.0)
            latency = int((time.perf_counter() - start_time) * 1000)

            if resp.status_code == 200:
                raw_json = resp.json()
                status = raw_json.get("status")
                inference = raw_json.get("inference")
                is_healthy = status == "ok" and inference != "unavailable"
                res = is_healthy, {
                    "reachable": is_healthy,
                    "status": status,
                    "version": raw_json.get("version"),
                    "database": raw_json.get("database"),
                    "inference": inference,
                    "status_code": resp.status_code,
                    "latency_ms": latency,
                    "raw": raw_json,
                }
                self._last_health_ts = now
                self._last_health_result = res
                return res
            elif resp.status_code in (401, 403):
                res = False, {
                    "reachable": False,
                    "reason": f"DetectifAI authentication rejected with HTTP {resp.status_code}. Please verify DETECTIF_API_KEY.",
                    "status_code": resp.status_code,
                    "latency_ms": latency,
                }
                self._last_health_ts = now
                self._last_health_result = res
                return res
            else:
                res = False, {
                    "reachable": False,
                    "reason": f"DetectifAI /health returned HTTP {resp.status_code}",
                    "status_code": resp.status_code,
                    "latency_ms": latency,
                }
                self._last_health_ts = now
                self._last_health_result = res
                return res
        except requests.RequestException as exc:
            return False, {"reachable": False, "error": str(exc)}

    def get_health(self) -> Dict[str, Any]:
        """GET /v1/health - Check service health.
        OpenAPI 3.1.0 response schema HealthResponse:
        { "request_id": str, "status": "ok"|"degraded", "version": str, "database": "ok"|"unavailable", "inference": "ok"|"unavailable" }
        """
        url = self._url("/health")
        start_time = time.perf_counter()
        try:
            resp = requests.get(url, headers={"Accept": "application/json"}, timeout=self.timeout)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            if resp.status_code >= 400:
                self._raise_for_error(resp)
            data = resp.json()
            data["latency_ms"] = latency_ms
            return data
        except requests.RequestException as exc:
            raise DetectifAPIError(f"DetectifAI GET /v1/health failed or timed out: {exc}")

    # ==========================================================================
    # 2. Account Credits Balance (GET /v1/credits)
    # ==========================================================================
    def get_credits(self, force_refresh: bool = False) -> Dict[str, Any]:
        """GET /v1/credits - Returns account plan, available credits, and reserved credits.
        Requires scope: credits:read.
        OpenAPI 3.1.0 response schema CreditsObject:
        {
            "request_id": str,
            "object": "credits",
            "plan": "free"|"unlimited",
            "unlimited": bool,
            "available": Optional[int],
            "reserved": int,
            "price_per_operation": int
        }
        """
        if not self.is_configured():
            raise DetectifAPIError(
                "DETECTIF_API_KEY is not configured in environment. "
                "Set your API key in .env to query live credits balance."
            )

        now = time.time()
        if not force_refresh and hasattr(self, "_last_credits_ts") and (now - self._last_credits_ts < 10.0) and hasattr(self, "_last_credits_result"):
            return dict(self._last_credits_result)

        url = self._url("/credits")
        headers = self._get_headers()
        start_time = time.perf_counter()

        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            if resp.status_code >= 400:
                self._raise_for_error(resp)

            raw_json = resp.json()
            avail = raw_json.get("available")
            if avail is not None:
                self.remaining_credits = int(avail)
            elif "credits" in raw_json:
                self._update_tracked_credits(raw_json["credits"])

            remaining = self.remaining_credits if self.remaining_credits is not None else avail
            reserve_protected = bool(remaining is not None and remaining >= self.credit_reserve_floor)
            circuit_breaker_active = bool(remaining is not None and remaining <= self.credit_reserve_floor)

            res = {
                "plan": raw_json.get("plan"),
                "unlimited": bool(raw_json.get("unlimited", False)),
                "available": raw_json.get("available"),
                "credits": remaining,
                "credits_remaining": remaining,
                "remaining": remaining,
                "reserved": raw_json.get("reserved", 0),
                "price_per_operation": raw_json.get("price_per_operation", 0),
                "reserve_floor": self.credit_reserve_floor,
                "reserve_protected": reserve_protected,
                "circuit_breaker_active": circuit_breaker_active,
                "request_id": raw_json.get("request_id"),
                "raw": raw_json,
                "latency_ms": latency_ms,
            }
            self._last_credits_ts = now
            self._last_credits_result = res
            return res
        except requests.RequestException as exc:
            raise DetectifAPIError(f"DetectifAI GET /v1/credits failed or timed out: {exc}")

    # ==========================================================================
    # 3. Deepfake Detection (POST /v1/deepfake/detect)
    # ==========================================================================
    def detect_deepfake(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        idempotency_key: Optional[str] = None,
        is_demo: bool = False,
    ) -> Dict[str, Any]:
        """POST /v1/deepfake/detect (Aletheia Engine).
        Checks whether an audio recording contains AI-generated synthetic speech.

        Parameters:
            audio_bytes: Raw audio bytes (WAV, MP3, FLAC, OGG/Opus, WebM, M4A/AAC, AIFF).
            filename: Audio file name (e.g. 'audio.wav').
            idempotency_key: Optional UUID idempotency key; auto-generated if omitted.
            is_demo: Legacy compatibility parameter; it does not bypass the credit reserve.

        Parses strictly per OpenAPI 3.1.0 DeepfakeResponse:
            result.verdict: 'real' | 'fake' | 'not_sure'
            result.score: float (0.0 to 1.0)
            result.threshold: float (0.62)
            result.is_synthetic: bool (True only when verdict == 'fake')
        """
        if not self.is_configured():
            raise DetectifAPIError(
                "DETECTIF_API_KEY is not configured in environment. "
                "Set your API key in .env to run live deepfake detection."
            )

        if not audio_bytes:
            raise DetectifAPIError("Empty audio buffer provided for deepfake detection.")

        # Credit Guardian Circuit Breaker Check
        self._ensure_live_analysis_allowed("deepfake detection", is_demo=is_demo)

        url = self._url("/deepfake/detect")
        idem_key = idempotency_key or str(uuid.uuid4())
        headers = self._get_headers(idempotency_key=idem_key)
        files = {"file": (filename, audio_bytes, "audio/wav")}

        start_time = time.perf_counter()
        last_error = None

        # Execute call with retry using the SAME Idempotency-Key
        for attempt in range(2):
            try:
                resp = requests.post(url, headers=headers, files=files, timeout=self.timeout)
                latency_ms = int((time.perf_counter() - start_time) * 1000)

                # Retry once on upstream 502/503/504
                if attempt == 0 and resp.status_code in (502, 503, 504):
                    time.sleep(0.2)
                    continue

                if resp.status_code >= 400:
                    self._raise_for_error(resp)

                raw_json = resp.json()

                # Extract result per OpenAPI DeepfakeResult
                res_obj = raw_json.get("result")
                if not isinstance(res_obj, dict):
                    res_obj = raw_json

                verdict = res_obj.get("verdict")
                if verdict not in ("real", "fake", "not_sure"):
                    label = res_obj.get("label")
                    if label == "synthetic":
                        verdict = "fake"
                    elif label == "genuine":
                        verdict = "real"
                    elif label == "uncertain":
                        verdict = "not_sure"

                score = res_obj.get("score")
                if score is not None:
                    score = float(score)
                else:
                    alt_score = res_obj.get("synthetic", res_obj.get("synthetic_probability"))
                    if alt_score is not None:
                        score = float(alt_score)

                threshold = float(res_obj.get("threshold", 0.62))
                if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
                    raise DetectifAPIError("DetectifAI returned an invalid deepfake threshold.", raw_json=raw_json)

                is_synth_val = res_obj.get("is_synthetic")
                if is_synth_val is not None and not isinstance(is_synth_val, bool):
                    raise DetectifAPIError("DetectifAI returned a non-boolean is_synthetic field.", raw_json=raw_json)
                if is_synth_val is not None:
                    is_synthetic = is_synth_val
                elif verdict:
                    is_synthetic = verdict == "fake"
                elif score is not None:
                    is_synthetic = score >= threshold
                else:
                    is_synthetic = False

                # Never manufacture a probability from a categorical verdict.
                if score is None:
                    raise DetectifAPIError(
                        f"DetectifAI response did not contain the numeric deepfake score required for classification: {raw_json}",
                        status_code=resp.status_code,
                        raw_body=resp.text,
                        raw_json=raw_json,
                    )
                if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                    raise DetectifAPIError(
                        "DetectifAI returned a deepfake score outside the valid [0, 1] range.",
                        status_code=resp.status_code,
                        raw_body=resp.text,
                        raw_json=raw_json,
                    )
                score_classification = score >= threshold
                if verdict in ("real", "fake") and (verdict == "fake") != score_classification:
                    raise DetectifAPIError(
                        "DetectifAI returned conflicting deepfake verdict and score fields.",
                        status_code=resp.status_code,
                        raw_body=resp.text,
                        raw_json=raw_json,
                    )
                if verdict != "not_sure" and is_synth_val is not None and is_synth_val != score_classification:
                    raise DetectifAPIError(
                        "DetectifAI returned conflicting is_synthetic and score fields.",
                        status_code=resp.status_code,
                        raw_body=resp.text,
                        raw_json=raw_json,
                    )
                is_synthetic = None if verdict == "not_sure" else (
                    verdict == "fake" if verdict else (is_synth_val if is_synth_val is not None else score >= threshold)
                )

                # Track credits from response
                if "credits" in raw_json:
                    self._update_tracked_credits(raw_json["credits"])
                elif "available" in raw_json:
                    self._update_tracked_credits(raw_json["available"])

                ret_dict = {
                    "verdict": verdict or ("fake" if is_synthetic else "real"),
                    "score": round(score, 4),
                    "threshold": threshold,
                    "is_synthetic": is_synthetic,
                    "synthetic_score": round(score, 4),  # UnClone Gate contract compatibility
                    "decided_by": res_obj.get("decided_by"),
                    "duration_seconds": res_obj.get("duration_seconds"),
                    "segments": res_obj.get("segments", []),
                    "operation_id": raw_json.get("operation_id"),
                    "request_id": raw_json.get("request_id"),
                    "idempotent_replay": raw_json.get("idempotent_replay", False),
                    "credits": raw_json.get("credits"),
                    "model": raw_json.get("model"),
                    "raw": raw_json,
                    "latency_ms": latency_ms,
                }
                return ret_dict
            except requests.RequestException as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(0.2)
                    continue

        raise DetectifAPIError(f"DetectifAI deepfake detection connection failed or timed out: {last_error}")

    # ==========================================================================
    # 4. Speaker Enrollment (POST /v1/speakers/enroll)
    # ==========================================================================
    def enroll_speaker(
        self,
        audio_bytes: bytes,
        speaker_id: Optional[str] = None,
        display_name: Optional[str] = None,
        speaker_name: Optional[str] = None,
        filename: str = "enroll.wav",
        idempotency_key: Optional[str] = None,
        is_demo: bool = False,
    ) -> Dict[str, Any]:
        """POST /v1/speakers/enroll (Eidos Engine).
        Saves a voice sample for a speaker to verify recordings against.

        Parameters:
            audio_bytes: Pristine WAV or audio stream (15-60s recommended).
            speaker_id: Identifier for the speaker (1-64 chars: ^[A-Za-z0-9_.:-]{1,64}$).
            display_name: Optional human-readable label for the speaker (max 128 chars).
            speaker_name: Alias for speaker_id / display_name for backward compatibility.
            filename: Audio file name (e.g. 'enroll.wav').
            idempotency_key: Optional UUID idempotency key; auto-generated if omitted.
            is_demo: Legacy compatibility parameter; it does not bypass the credit reserve.

        Parses strictly per OpenAPI 3.1.0 EnrollResponse:
            speaker.speaker_id: str
            speaker.display_name: str
            speaker.samples: int
            quality: { speech_seconds, duration_seconds }
        """
        if not self.is_configured():
            raise DetectifAPIError(
                "DETECTIF_API_KEY is not configured in environment. "
                "Set your API key in .env to run live speaker enrollment."
            )

        if not audio_bytes:
            raise DetectifAPIError("Empty audio buffer provided for speaker enrollment.")

        sid_raw = (speaker_id or speaker_name or "senior_user_01").strip()
        clean_speaker_id = re.sub(r"[^A-Za-z0-9_.:-]", "_", sid_raw)[:64]
        if not clean_speaker_id:
            clean_speaker_id = "speaker_01"

        clean_display_name = (display_name or speaker_name or sid_raw)[:128]

        # Credit Guardian Circuit Breaker Check
        self._ensure_live_analysis_allowed("speaker enrollment", is_demo=is_demo)

        url = self._url("/speakers/enroll")
        idem_key = idempotency_key or str(uuid.uuid4())
        headers = self._get_headers(idempotency_key=idem_key)
        files = {"file": (filename, audio_bytes, "audio/wav")}
        data: Dict[str, str] = {
            "speaker_id": clean_speaker_id,
            "display_name": clean_display_name,
        }

        start_time = time.perf_counter()
        last_error = None

        for attempt in range(2):
            try:
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=self.timeout)
                latency_ms = int((time.perf_counter() - start_time) * 1000)

                if attempt == 0 and resp.status_code in (502, 503, 504):
                    time.sleep(0.2)
                    continue

                if resp.status_code >= 400:
                    self._raise_for_error(resp)

                raw_json = resp.json()
                speaker_obj = raw_json.get("speaker")
                if isinstance(speaker_obj, dict):
                    ret_id = speaker_obj.get("speaker_id")
                    ret_name = speaker_obj.get("display_name")
                    samples = speaker_obj.get("samples", 1)
                else:
                    ret_id = raw_json.get("speaker_id") or raw_json.get("id")
                    ret_name = raw_json.get("display_name") or raw_json.get("name")
                    samples = 1

                if not ret_id:
                    raise DetectifAPIError(
                        f"DetectifAI enrollment response did not return a valid speaker ID: {raw_json}",
                        status_code=resp.status_code,
                        raw_body=resp.text,
                        raw_json=raw_json,
                    )

                # Track credits from response
                if "credits" in raw_json:
                    self._update_tracked_credits(raw_json["credits"])
                elif "available" in raw_json:
                    self._update_tracked_credits(raw_json["available"])

                ret_dict = {
                    "speaker_id": str(ret_id),
                    "display_name": ret_name or clean_display_name,
                    "name": ret_name or clean_display_name,
                    "samples": samples,
                    "enrolled": True,
                    "quality": raw_json.get("quality", {}),
                    "credits": raw_json.get("credits"),
                    "model": raw_json.get("model"),
                    "operation_id": raw_json.get("operation_id"),
                    "request_id": raw_json.get("request_id"),
                    "idempotent_replay": raw_json.get("idempotent_replay", False),
                    "raw": raw_json,
                    "detectif_raw": raw_json,
                    "latency_ms": latency_ms,
                }
                return ret_dict
            except requests.RequestException as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(0.2)
                    continue

        raise DetectifAPIError(f"DetectifAI speaker enrollment connection failed or timed out: {last_error}")

    # ==========================================================================
    # 5. Speaker Verification (POST /v1/speakers/verify)
    # ==========================================================================
    def verify_speaker(
        self,
        audio_bytes: bytes,
        speaker_id: str,
        filename_or_deepfake: Any = None,
        detect_deepfake: bool = False,
        filename: str = "verify.wav",
        idempotency_key: Optional[str] = None,
        is_demo: bool = False,
    ) -> Dict[str, Any]:
        """POST /v1/speakers/verify (Eidos Engine).
        Checks whether a recording matches an enrolled speaker voiceprint.

        Parameters:
            audio_bytes: WAV or audio stream (3-60s with >= 2s clear speech).
            speaker_id: Claimed identity of enrolled speaker.
            filename_or_deepfake: Disambiguated positional 3rd argument (str for filename, bool for detect_deepfake).
            detect_deepfake: Optional flag to run joint deepfake detection (needs scope deepfake:detect).
            filename: Audio file name (e.g. 'verify.wav').
            idempotency_key: Optional UUID idempotency key; auto-generated if omitted.
            is_demo: Legacy compatibility parameter; it does not bypass the credit reserve.

        Parses strictly per OpenAPI 3.1.0 VerifyResponse:
            result.decision: 'match' | 'no_match'
            result.similarity: float (-1.0 to 1.0)
            result.threshold: float (0.53)
        """
        if not self.is_configured():
            raise DetectifAPIError(
                "DETECTIF_API_KEY is not configured in environment. "
                "Set your API key in .env to run live speaker verification."
            )

        if not audio_bytes:
            raise DetectifAPIError("Empty audio buffer provided for speaker verification.")

        # Disambiguate positional argument variations
        if isinstance(filename_or_deepfake, str):
            filename = filename_or_deepfake
        elif isinstance(filename_or_deepfake, bool):
            detect_deepfake = filename_or_deepfake

        sid_raw = (speaker_id or "senior_user_01").strip()
        clean_speaker_id = re.sub(r"[^A-Za-z0-9_.:-]", "_", sid_raw)[:64]
        if not clean_speaker_id:
            clean_speaker_id = "speaker_01"

        # Credit Guardian Circuit Breaker Check
        self._ensure_live_analysis_allowed("speaker verification", is_demo=is_demo)

        url = self._url("/speakers/verify")
        idem_key = idempotency_key or str(uuid.uuid4())
        headers = self._get_headers(idempotency_key=idem_key)
        files = {"file": (filename, audio_bytes, "audio/wav")}
        data: Dict[str, Any] = {"speaker_id": clean_speaker_id}
        if detect_deepfake:
            data["detect_deepfake"] = "true"

        start_time = time.perf_counter()
        last_error = None

        for attempt in range(2):
            try:
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=self.timeout)
                latency_ms = int((time.perf_counter() - start_time) * 1000)

                if attempt == 0 and resp.status_code in (502, 503, 504):
                    time.sleep(0.2)
                    continue

                if resp.status_code >= 400:
                    self._raise_for_error(resp)

                raw_json = resp.json()
                res_obj = raw_json.get("result")
                if not isinstance(res_obj, dict):
                    res_obj = raw_json

                decision = res_obj.get("decision")  # 'match' | 'no_match'
                if decision not in (None, "match", "no_match"):
                    raise DetectifAPIError("DetectifAI returned an unknown speaker verification decision.", raw_json=raw_json)
                similarity = res_obj.get("similarity")
                if similarity is not None:
                    similarity = float(similarity)
                else:
                    alt_sim = res_obj.get("match", res_obj.get("speaker_match_score", res_obj.get("score")))
                    if alt_sim is not None:
                        similarity = float(alt_sim)

                threshold = float(res_obj.get("threshold", 0.53))
                if not math.isfinite(threshold) or not -1.0 <= threshold <= 1.0:
                    raise DetectifAPIError("DetectifAI returned an invalid speaker-match threshold.", raw_json=raw_json)

                if decision is None and similarity is not None:
                    decision = "match" if similarity >= threshold else "no_match"

                # Never turn a categorical match result into an invented score.
                if similarity is None:
                    raise DetectifAPIError(
                        f"DetectifAI response did not contain a numeric speaker similarity required for verification: {raw_json}",
                        status_code=resp.status_code,
                        raw_body=resp.text,
                        raw_json=raw_json,
                    )
                if not math.isfinite(similarity) or not -1.0 <= similarity <= 1.0:
                    raise DetectifAPIError(
                        "DetectifAI returned speaker similarity outside the valid [-1, 1] range.",
                        status_code=resp.status_code,
                        raw_body=resp.text,
                        raw_json=raw_json,
                    )
                if decision in ("match", "no_match") and (decision == "match") != (similarity >= threshold):
                    raise DetectifAPIError(
                        "DetectifAI returned conflicting speaker decision and similarity fields.",
                        status_code=resp.status_code,
                        raw_body=resp.text,
                        raw_json=raw_json,
                    )

                matched = (decision == "match") if decision else similarity >= threshold

                # Track credits from response
                if "credits" in raw_json:
                    self._update_tracked_credits(raw_json["credits"])
                elif "available" in raw_json:
                    self._update_tracked_credits(raw_json["available"])

                ret_dict = {
                    "decision": decision or ("match" if matched else "no_match"),
                    "similarity": round(similarity, 4),
                    "threshold": threshold,
                    "matched": bool(matched),
                    "match_score": round(similarity, 4),  # UnClone Gate contract compatibility
                    "speaker_id": raw_json.get("speaker_id", clean_speaker_id),
                    "deepfake": raw_json.get("deepfake"),
                    "duration_seconds": res_obj.get("duration_seconds"),
                    "credits": raw_json.get("credits"),
                    "model": raw_json.get("model"),
                    "operation_id": raw_json.get("operation_id"),
                    "request_id": raw_json.get("request_id"),
                    "idempotent_replay": raw_json.get("idempotent_replay", False),
                    "raw": raw_json,
                    "latency_ms": latency_ms,
                }
                return ret_dict
            except requests.RequestException as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(0.2)
                    continue

        raise DetectifAPIError(f"DetectifAI speaker verification connection failed or timed out: {last_error}")

    # ==========================================================================
    # 6. Additional OpenAPI Operations (Speakers, Operations, Feedback, Usage)
    # ==========================================================================
    def list_speakers(self, limit: int = 20, cursor: Optional[str] = None) -> Dict[str, Any]:
        """GET /v1/speakers - Lists account speakers. Requires scope: speakers:read."""
        if not self.is_configured():
            raise DetectifAPIError("DETECTIF_API_KEY is not configured in environment.")

        url = self._url("/speakers")
        params: Dict[str, Any] = {"limit": min(max(1, limit), 100)}
        if cursor:
            params["cursor"] = cursor

        try:
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)
            if resp.status_code >= 400:
                self._raise_for_error(resp)
            return resp.json()
        except requests.RequestException as exc:
            raise DetectifAPIError(f"DetectifAI GET /v1/speakers failed: {exc}")

    def get_speaker(self, speaker_id: str) -> Dict[str, Any]:
        """GET /v1/speakers/{speaker_id} - Returns one speaker. Requires scope: speakers:read."""
        if not self.is_configured():
            raise DetectifAPIError("DETECTIF_API_KEY is not configured in environment.")

        clean_id = re.sub(r"[^A-Za-z0-9_.:-]", "_", speaker_id)[:64]
        url = self._url(f"/speakers/{clean_id}")
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            if resp.status_code >= 400:
                self._raise_for_error(resp)
            return resp.json()
        except requests.RequestException as exc:
            raise DetectifAPIError(f"DetectifAI GET /v1/speakers/{clean_id} failed: {exc}")

    def delete_speaker(self, speaker_id: str) -> Dict[str, Any]:
        """DELETE /v1/speakers/{speaker_id} - Permanently deletes a speaker. Requires scope: speakers:delete."""
        if not self.is_configured():
            raise DetectifAPIError("DETECTIF_API_KEY is not configured in environment.")

        clean_id = re.sub(r"[^A-Za-z0-9_.:-]", "_", speaker_id)[:64]
        url = self._url(f"/speakers/{clean_id}")
        try:
            resp = requests.delete(url, headers=self._get_headers(), timeout=self.timeout)
            if resp.status_code >= 400:
                self._raise_for_error(resp)
            return resp.json()
        except requests.RequestException as exc:
            raise DetectifAPIError(f"DetectifAI DELETE /v1/speakers/{clean_id} failed: {exc}")

    def get_operation(self, operation_id: str) -> Dict[str, Any]:
        """GET /v1/operations/{operation_id} - Retrieves stored outcome of an earlier operation."""
        if not self.is_configured():
            raise DetectifAPIError("DETECTIF_API_KEY is not configured in environment.")

        url = self._url(f"/operations/{operation_id}")
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            if resp.status_code >= 400:
                self._raise_for_error(resp)
            return resp.json()
        except requests.RequestException as exc:
            raise DetectifAPIError(f"DetectifAI GET /v1/operations/{operation_id} failed: {exc}")

    def send_feedback(
        self,
        operation_id: str,
        correct: bool,
        label: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /v1/operations/{operation_id}/feedback - Submits accuracy feedback for deepfake.detect."""
        if not self.is_configured():
            raise DetectifAPIError("DETECTIF_API_KEY is not configured in environment.")

        url = self._url(f"/operations/{operation_id}/feedback")
        payload: Dict[str, Any] = {"correct": bool(correct)}
        if label in ("real", "fake"):
            payload["label"] = label
        if note:
            payload["note"] = note[:500]

        try:
            resp = requests.post(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            if resp.status_code >= 400:
                self._raise_for_error(resp)
            return resp.json()
        except requests.RequestException as exc:
            raise DetectifAPIError(f"DetectifAI POST feedback for {operation_id} failed: {exc}")

    def get_usage(
        self,
        limit: int = 20,
        cursor: Optional[str] = None,
        operation: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GET /v1/usage - Lists API usage events. Requires scope: usage:read."""
        if not self.is_configured():
            raise DetectifAPIError("DETECTIF_API_KEY is not configured in environment.")

        url = self._url("/usage")
        params: Dict[str, Any] = {"limit": min(max(1, limit), 100)}
        if cursor:
            params["cursor"] = cursor
        if operation:
            params["operation"] = operation
        if status:
            params["status"] = status

        try:
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)
            if resp.status_code >= 400:
                self._raise_for_error(resp)
            return resp.json()
        except requests.RequestException as exc:
            raise DetectifAPIError(f"DetectifAI GET /v1/usage failed: {exc}")


# Global client singleton
detectif_client = DetectifClient()
