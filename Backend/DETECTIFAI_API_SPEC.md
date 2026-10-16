# DetectifAI Platform API Specification & UnClone Contract Mapping

> **System Track:** Track 3: UNCLONE Agents — Zero-Trust Voice Agent Security & Cost-Optimization Gateway  
> **Target Gateway:** UnClone Gate (`backend/detectif_client.py`, `backend/gate.py`, `backend/main.py`)  
> **Upstream Platform:** DetectifAI Platform (`https://platform.detectif.ai` / `https://api.detectif.ai/v1`)  
> **Compliance Standard:** Hackathon Rule 5.4 (Zero synthetic score mocking, real live calls, deterministic fail-closed architecture)

---

## 1. Architectural Overview & The 4 DetectifAI Engines

The **DetectifAI Platform** provides state-of-the-art acoustic forensics, biometric speaker verification, and contextual liveness intelligence. UnClone Gate orchestrates these models as a mandatory security pre-gate defending BFSI voice infrastructure (e.g., senior citizen banking hotlines, automated fund transfers, and voice-authenticated customer service).

DetectifAI organizes its detection pipeline into **4 specialized engines**:

```
                                  [ Incoming Audio Stream ]
                                             │
             ┌───────────────────────────────┴───────────────────────────────┐
             ▼                                                               ▼
   ┌───────────────────┐                                           ┌───────────────────┐
   │  Aletheia Engine  │                                           │   Eidos Engine    │
   │ (Deepfake/Synth)  │                                           │  (Voice Biometrics│
   │  /audio/analyze   │                                           │  /speaker/verify  │
   └─────────┬─────────┘                                           └─────────┬─────────┘
             │ synthetic_score (0.0 - 1.0)                                   │ match_score (0.0 - 1.0)
             │                                                               │
             └───────────────────────────────┬───────────────────────────────┘
                                             ▼
                                  ┌────────────────────┐
                                  │   Noesis Engine    │
                                  │ (Acoustic Context, │
                                  │ Replay & Liveness) │
                                  └──────────┬─────────┘
                                             │ liveness & channel metadata
                                             ▼
                                  ┌────────────────────┐
                                  │    Lexis Engine    │
                                  │(Deterministic Gate)│
                                  │  2x2 Policy Matrix │
                                  └──────────┬─────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
            [ APPROVE / UNLOCK ]                        [ SHORT-CIRCUIT & BLOCK ]
             • Execute Banking Tool                      • Drop LLM & TTS computation
             • Invoke NVIDIA Nemotron                    • Save ~₹20 / 120s per call
             • Provide Account Service                   • Log immutable audit record
```

### The 4 Engines in Detail

| Engine | Greek Root & Meaning | Platform Specialization | UnClone Role & Implementation |
| :--- | :--- | :--- | :--- |
| **Aletheia** | Ἀλήθεια (*"Truth / Un-concealment"*) | **Audio Deepfake & Synthetic Speech Detection**. Detects neural vocoder artifacts (HiFi-GAN, MelGAN, BigVGAN), diffusion vocoders, TTS latent traces (ElevenLabs, XTTS v2, VALL-E, DiffSinger, Bark), phase discrepancies, and harmonic distortion. | Called via `detectif_client.detect_deepfake()`. Emits `synthetic_score` ($0.0 \le s \le 1.0$) and `is_synthetic` boolean flag. |
| **Eidos** | Εἶδος (*"Form / Essence / Visible ID"*) | **Speaker Biometrics & 1:1 Voiceprint Recognition**. Deep speaker embeddings (d-vector / x-vector / ECAPA-TDNN) that measure acoustic tract resonances invariant to speech content, background noise, or microphone distance. | Called via `detectif_client.enroll_speaker()` and `verify_speaker()`. Emits `match_score` ($0.0 \le m \le 1.0$) and `matched` boolean flag. |
| **Noesis** | Νόησις (*"Intellect / Cognitive Perception"*) | **Acoustic Context, Anti-Spoofing & Replay Analysis**. Analyzes Room Impulse Response (RIR), loudspeaker non-linear playback distortion (physical speaker replay vs. human vocal tract), acoustic room reflections, and telephony PSTN vs. VoIP transmission artifacts. | Informs channel calibration and anti-replay verification; ensures physical loudspeaker recordings are flagged even if raw vocoder traces are masked. |
| **Lexis** | Λέξις (*"Law / Principle / Code of Rules"*) | **Deterministic Policy Gate & Rules Matrix Engine**. The 100% deterministic decision logic running inside `backend/gate.py`. Evaluates the multi-dimensional output of Aletheia $\times$ Eidos without allowing non-deterministic LLMs to govern security. | Implements the 2x2 decision matrix: `APPROVE`, `BLOCK_ALERT`, `STEP_UP`, `BLOCK`, with strict fail-closed exceptions on network or timeout faults. |

---

## 2. Authentication & Network Specifications

All communication with the DetectifAI platform is encrypted over TLS 1.3 and authenticated via secret API tokens provisioned in the DetectifAI Platform Console.

### Base URLs
- **Production API:** `https://api.detectif.ai/v1`
- **Platform Console:** `https://platform.detectif.ai`
- **Environment Variable:** `DETECTIF_BASE_URL` (in `.env`)

### Request Headers
Every HTTP request dispatched to the DetectifAI platform must provide credentials in both standard bearer and vendor key headers for universal gateway compatibility:

```http
Authorization: Bearer <DETECTIF_API_KEY>
X-API-Key: <DETECTIF_API_KEY>
Accept: application/json
User-Agent: UnClone-Gate-BFSI/1.0
```

### Response Headers
DetectifAI platform responses contain downstream tracking and telemetry headers:

| Header Name | Type | Description |
| :--- | :--- | :--- |
| `Content-Type` | `string` | Always `application/json` |
| `X-Request-ID` | `string` | Unique upstream execution identifier (UUIDv4) |
| `X-Inference-Time-Ms` | `integer` | Processing latency on DetectifAI GPU cluster in milliseconds |
| `X-RateLimit-Limit` | `integer` | Allocated request capacity per sliding minute window |
| `X-RateLimit-Remaining` | `integer` | Remaining request quota in the active sliding window |

### Reliability & Timeout Policy
- **Client Timeout:** `5.0` seconds (`DETECTIF_TIMEOUT_SECONDS`)
- **Retry Policy:** 1 automatic retry on network disconnect or HTTP 5xx before raising `DetectifAPIError`.
- **Fail-Closed Guarantee:** Any timeout, network partition, or non-200 code immediately forces an emergency freeze (`BLOCK` on high-risk transfers; `STEP_UP` on read inquiries).

---

## 3. DetectifAI Endpoint Specifications

### 3.1. Deepfake Detection: `POST /audio/analyze` (Aletheia Engine)

Analyzes an audio file to determine whether it contains synthetic speech, AI-generated cloning artifacts, or natural human vocalization.

- **Primary Path:** `POST /audio/analyze`
- **Alternative/Fallback Path:** `POST /detect`
- **Content-Type:** `multipart/form-data`

#### Request Parameters (Multipart Form-Data)

| Field Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `file` (or `audio`) | `File (Binary)` | **Yes** | WAV audio stream (8kHz telephony PCM or 16kHz linear PCM, 16-bit mono). Minimum duration: 0.5s; recommended duration: 2.0s - 10.0s. |
| `checks` | `string` | Optional | Detection modules requested. Default: `"authenticity"`. Supported: `"authenticity,deepfake,artifacts"`. |

#### cURL Snippet (Deepfake Detection)
```bash
curl -X POST "https://api.detectif.ai/v1/audio/analyze" \
  -H "Authorization: Bearer $DETECTIF_API_KEY" \
  -H "X-API-Key: $DETECTIF_API_KEY" \
  -F "file=@sample_call.wav;type=audio/wav" \
  -F "checks=authenticity"
```

#### Real Sample JSON Responses

##### Scenario A: Authentic Natural Human Voice
```json
{
  "status": "success",
  "request_id": "req_ale_98f12a4b8c",
  "is_synthetic": false,
  "synthetic": 0.0412,
  "synthetic_probability": 0.0412,
  "confidence": 0.9588,
  "authenticity": {
    "human": 0.9588,
    "synthetic": 0.0412
  },
  "metrics": {
    "vocoder_artifacts_detected": false,
    "spectral_flux_anomaly": 0.012,
    "phase_coherence": 0.984
  },
  "audio_metadata": {
    "duration_seconds": 3.42,
    "sample_rate": 16000,
    "channels": 1
  }
}
```

##### Scenario B: AI Voice Clone / Deepfake Detected (ElevenLabs / Neural Vocoder)
```json
{
  "status": "success",
  "request_id": "req_ale_c37d091e21",
  "is_synthetic": true,
  "synthetic": 0.9428,
  "synthetic_probability": 0.9428,
  "confidence": 0.9428,
  "authenticity": {
    "human": 0.0572,
    "synthetic": 0.9428
  },
  "metrics": {
    "vocoder_artifacts_detected": true,
    "vocoder_type_estimated": "neural_hifi_gan",
    "spectral_flux_anomaly": 0.891,
    "phase_coherence": 0.312
  },
  "audio_metadata": {
    "duration_seconds": 4.10,
    "sample_rate": 16000,
    "channels": 1
  }
}
```

---

### 3.2. Speaker Enrollment: `POST /speaker/enroll` (Eidos Engine)

Extracts and registers a reference voice biometric embedding for a legitimate customer/speaker into the platform repository.

- **Primary Path:** `POST /speaker/enroll`
- **Alternative/Fallback Path:** `POST /enroll`
- **Content-Type:** `multipart/form-data`

#### Request Parameters (Multipart Form-Data)

| Field Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `audio` | `File (Binary)` | **Yes** | Pristine WAV audio sample of the customer enrolling their voice (16kHz recommended, $\ge 3.0$ seconds clean speech). |
| `name` | `string` | **Yes** | Identifier or label for the voice profile (e.g. `"senior_user_01"`, `"account_982314"`). |

#### cURL Snippet (Speaker Enrollment)
```bash
curl -X POST "https://api.detectif.ai/v1/speaker/enroll" \
  -H "Authorization: Bearer $DETECTIF_API_KEY" \
  -H "X-API-Key: $DETECTIF_API_KEY" \
  -F "audio=@senior_enrollment_audio.wav;type=audio/wav" \
  -F "name=senior_user_01"
```

#### Real Sample JSON Response
```json
{
  "status": "success",
  "request_id": "req_eid_enroll_41b9",
  "speaker_id": "spk_usr_9021a8f",
  "name": "senior_user_01",
  "voiceprint_id": "vp_emb_8723610991",
  "enrolled_at": "2026-10-16T08:15:22.104Z",
  "quality_score": 0.92,
  "duration_processed": 5.24,
  "embedding_dimensions": 256
}
```

---

### 3.3. Speaker Verification: `POST /speaker/verify` (Eidos Engine)

Performs 1:1 acoustic comparison between an incoming audio clip and an enrolled customer's voiceprint embedding.

- **Primary Path:** `POST /speaker/verify`
- **Alternative/Fallback Path:** `POST /verify`
- **Content-Type:** `multipart/form-data`

#### Request Parameters (Multipart Form-Data)

| Field Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `audio` | `File (Binary)` | **Yes** | Incoming WAV audio from the active call/turn to be authenticated against the stored voiceprint. |
| `speaker_id` | `string` | **Yes** | The registered speaker profile ID or name assigned during enrollment. |
| `speakerReference` | `string` | Optional | Alias parameter accepted by legacy DetectifAI gateway endpoints. |

#### cURL Snippet (Speaker Verification)
```bash
curl -X POST "https://api.detectif.ai/v1/speaker/verify" \
  -H "Authorization: Bearer $DETECTIF_API_KEY" \
  -H "X-API-Key: $DETECTIF_API_KEY" \
  -F "audio=@incoming_caller_audio.wav;type=audio/wav" \
  -F "speaker_id=senior_user_01" \
  -F "speakerReference=senior_user_01"
```

#### Real Sample JSON Responses

##### Scenario A: Enrolled Account Holder Matching Voiceprint
```json
{
  "status": "success",
  "request_id": "req_eid_ver_77180a",
  "speaker_id": "senior_user_01",
  "matched": true,
  "match": 0.9385,
  "speaker_match_score": 0.9385,
  "distance": 0.124,
  "threshold_applied": 0.85,
  "speaker": {
    "id": "senior_user_01",
    "match": 0.9385
  }
}
```

##### Scenario B: Non-Matching Speaker (Impostor / Wrong Caller)
```json
{
  "status": "success",
  "request_id": "req_eid_ver_2083bf",
  "speaker_id": "senior_user_01",
  "matched": false,
  "match": 0.3210,
  "speaker_match_score": 0.3210,
  "distance": 0.789,
  "threshold_applied": 0.85,
  "speaker": {
    "id": "senior_user_01",
    "match": 0.3210
  }
}
```

---

### 3.4. Health Ping & Upstream Telemetry: `GET /health`

Used by UnClone Gate (`detectif_client.check_health()`) to verify network reachability, certificate validity, and platform status before dispatching voice turns.

- **Path:** `GET /health` (Fallback: `HEAD /`)
- **Headers:** `Authorization: Bearer <DETECTIF_API_KEY>`

#### cURL Snippet
```bash
curl -X GET "https://api.detectif.ai/v1/health" \
  -H "Authorization: Bearer $DETECTIF_API_KEY"
```

#### Real Sample JSON Response
```json
{
  "status": "healthy",
  "version": "1.4.2",
  "engines": {
    "aletheia": "operational",
    "eidos": "operational",
    "noesis": "operational",
    "lexis": "operational"
  },
  "server_time": "2026-10-16T08:20:00Z"
}
```

---

## 4. Platform Status & HTTP Response Code Handling

DetectifAI returns standard RFC HTTP status codes. `detectif_client.py` maps all non-2xx responses into structured `DetectifAPIError` exceptions that trigger the deterministic fail-closed gateway:

| HTTP Status | Platform Meaning | Gateway Behavior & Fail-Closed Logic |
| :--- | :--- | :--- |
| **`200 OK`** | Analysis completed successfully. | Parsed into normalized metrics; passed to Lexis 2x2 matrix. |
| **`400 Bad Request`** | Malformed audio header, zero duration, or missing required parameter. | Reject with `400 Bad Request`, `fail_closed: true`. Zero LLM tokens executed. |
| **`401 / 403`** | Missing, expired, or unauthorized `DETECTIF_API_KEY`. | Logs urgent administrative alert. Freezes fund transfer operations safely (`BLOCK`). |
| **`404 Not Found`** | Endpoint variant mismatch on host cluster. | `detectif_client.py` transparently retries fallback route (e.g. `/detect` or `/verify`). |
| **`429 Rate Limit`** | API rate limit exceeded on DetectifAI cluster. | Fast-fails closed to prevent unauthorized operations during quota exhaustion. |
| **`500 / 502 / 503`** | Upstream inference worker crash or outage. | Retries once ($200\text{ms}$ delay); if persistent, locks banking tools and halts turn. |

---

## 5. The Lexis 2x2 Decision Matrix

The **Lexis Engine** (`backend/gate.py`) evaluates the composite findings of Aletheia and Eidos against three strict thresholds defined in `backend/config.py`:
- `MATCH_HIGH = 0.85` (Voice matches enrolled voiceprint)
- `SYNTH_HIGH = 0.50` (Acoustic signals indicate AI vocoder / synthesis)
- `SYNTH_LOW = 0.20` (High-confidence natural human vocal tract)

```
                       ┌─────────────────────────────────────────────────────────┐
                       │               Eidos Biometric Match Score               │
                       ├────────────────────────────┬────────────────────────────┤
                       │      MATCH >= 0.85         │        MATCH < 0.85        │
                       │     (Enrolled Owner)       │       (Wrong Speaker)      │
┌───────────┬──────────┼────────────────────────────┼────────────────────────────┤
│           │          │ [QUADRANT 2: BLOCK_ALERT]  │    [QUADRANT 4: BLOCK]     │
│           │  SYNTH   │ 🚨 CRITICAL CLONE ATTACK!  │    🤖 SYNTHETIC IMPOSTOR   │
│           │  >= 0.50 │ Computer-generated voice   │ Computer-generated voice   │
│           │          │ mimicking account owner.   │ from unverified caller.    │
│           │          │ Tool Locked. Police alert. │ Tool Locked. Call dropped. │
│ Aletheia  ├──────────┼────────────────────────────┼────────────────────────────┤
│ Synthetic │          │    [QUADRANT 1: APPROVE]   │   [QUADRANT 3: STEP_UP]    │
│   Score   │  SYNTH   │  ✅ VERIFIED SAFE HUMAN    │  ⚠️ WRONG HUMAN CALLER     │
│           │  < 0.20  │ Natural vocal tract and    │ Real human voice, but not  │
│           │          │ identity match confirmed.  │ the enrolled account owner.│
│           │          │ Tool Unlocked. Call passed.│ Secondary 2FA/PIN required.│
└───────────┴──────────┴────────────────────────────┴────────────────────────────┘
```

### Deterministic Gating Rules

1. **Quadrant 1 — `APPROVE` (Natural Human + Verified Enrolled Owner):**  
   $\text{synth} < 0.20 \text{ and } \text{match} \ge 0.85$  
   - **Tool Status:** `EXECUTED` (Banking tool unlocks and runs).
   - **Cost Metrics:** $0$ steps skipped; full dialogue processing proceeds.
   - **Senior UX:** Clear confirmation that their identity and transaction are safe.

2. **Quadrant 2 — `BLOCK_ALERT` (Cloned Voice Attack — THE DANGEROUS ZONE):**  
   $\text{synth} \ge 0.50 \text{ and } \text{match} \ge 0.85$  
   - **Attack Signature:** The audio sounds identical to the senior citizen (high biometrics match), but contains neural vocoder synthesis traces.
   - **Tool Status:** `LOCKED` (Fund transfer held immediately).
   - **Action:** Bank anti-fraud team dispatched; audio flagged in audit database.
   - **Cost Savings:** Bypasses LLM tokens and TTS synthesis ($120\text{s}$ saved, $\approx \text{₹}20.00$ saved).

3. **Quadrant 3 — `STEP_UP` (Real Human, Wrong Speaker):**  
   $\text{synth} < 0.20 \text{ and } \text{match} < 0.85$  
   - **Scenario:** A family member or unauthorized third-party is calling from the user's phone.
   - **Tool Status:** `LOCKED`.
   - **Action:** Requests a secondary 4-digit security PIN or mobile push notification before allowing high-risk actions.

4. **Quadrant 4 — `BLOCK` (Synthetic Impostor):**  
   $\text{synth} \ge 0.50 \text{ and } \text{match} < 0.85$  
   - **Scenario:** Automated scam robocall with an un-enrolled synthesized voice.
   - **Tool Status:** `LOCKED`.
   - **Action:** Immediate call drop.

5. **Inconclusive Confidence — `STEP_UP`:**  
   $0.20 \le \text{synth} < 0.50$  
   - Any ambiguous audio in noisy environments triggers safety step-up authentication.

6. **Fail-Closed Guarantee on Network Failure:**  
   If DetectifAI times out ($> 5.0\text{s}$) or returns a non-200 code:
   - For `TRANSFER_FUNDS`: Deterministic `BLOCK` with `fail_closed: true`.
   - For `CHECK_BALANCE`: Deterministic `STEP_UP` with `fail_closed: true`.
   - **Never default to APPROVE under any failure condition.**

---

## 6. How `detectif_client.py` Maps Platform Payloads to UnClone Contract

`detectif_client.py` serves as the **exclusive adapter** bridging the DetectifAI platform responses to the UnClone REST API contract specified in Section 4 of the Hackathon requirements.

### Normalization & Field Mapping Table

| DetectifAI Raw Platform Field | Fallback Keys Handled | `detectif_client.py` Normalized Key | UnClone API Contract Output (`/api/check`, `/api/agent/turn`) |
| :--- | :--- | :--- | :--- |
| `raw_json["synthetic"]` | `synthetic_probability`, `score`, `authenticity.synthetic` | `detection["synthetic_score"]` | `response["detection"]["synthetic_score"]` (`float`, $0.0 - 1.0$) |
| `raw_json["is_synthetic"]` | `synth_score >= SYNTH_HIGH` | `detection["is_synthetic"]` | `response["detection"]["is_synthetic"]` (`bool`) |
| `raw_json["match"]` | `speaker_match_score`, `score`, `speaker.match` | `verification["match_score"]` | `response["verification"]["match_score"]` (`float`, $0.0 - 1.0$) |
| `raw_json["matched"]` | `match_score >= MATCH_HIGH` | `verification["matched"]` | `response["verification"]["matched"]` (`bool`) |
| `raw_json["speaker_id"]` | `id`, `voiceprint_id`, auto-generated fallback | `enrollment["speaker_id"]` | `response["speaker_id"]` (`string`) |
| Total roundtrip duration | Process perf counter | `latency_ms` | `response["detection"]["latency_ms"]` (`integer`) |

### Parallel Engine Execution Architecture (`backend/main.py`)

To meet strict BFSI sub-second voice latency constraints, UnClone Gate executes Aletheia deepfake detection and Eidos biometric verification in **parallel threads** using Python's `ThreadPoolExecutor`:

```python
# From backend/main.py lines 138-154
with ThreadPoolExecutor(max_workers=2) as executor:
    future_detect = executor.submit(detectif_client.detect_deepfake, prep_bytes, filename)
    future_verify = executor.submit(detectif_client.verify_speaker, prep_bytes, speaker_id, filename)

    try:
        detection_res = future_detect.result()
    except DetectifAPIError as err:
        api_error = str(err)
        detection_res = {"is_synthetic": True, "synthetic_score": 1.0, "raw": {"error": str(err)}, "latency_ms": 0}

    try:
        verification_res = future_verify.result()
    except DetectifAPIError as err:
        if not api_error:
            api_error = str(err)
        verification_res = {"matched": False, "match_score": 0.0, "raw": {"error": str(err)}, "latency_ms": 0}
```

### Complete UnClone Response Payload Example (`POST /api/check`)

```json
{
  "request_id": "req_5f2d918c02a1",
  "ts": "2026-10-16T08:30:14.281940+00:00",
  "decision": "BLOCK_ALERT",
  "reason": "CRITICAL WARNING: Computer-generated voice clone detected! Although the voice sounds like the account holder, neural synthesis was identified. All transfers have been frozen and the bank fraud team has been alerted.",
  "detection": {
    "is_synthetic": true,
    "synthetic_score": 0.9428,
    "raw": {
      "status": "success",
      "synthetic": 0.9428,
      "authenticity": { "human": 0.0572, "synthetic": 0.9428 }
    },
    "latency_ms": 382
  },
  "verification": {
    "match_score": 0.9385,
    "matched": true,
    "raw": {
      "status": "success",
      "speaker_id": "senior_user_01",
      "match": 0.9385
    },
    "latency_ms": 412
  },
  "tool": {
    "status": "LOCKED",
    "reason": "Security Gate held the transaction. Voice authenticity or identity verification failed.",
    "result": null
  },
  "cost": {
    "agent_steps_skipped": 1,
    "agent_seconds_avoided": 120.0,
    "est_inr": 20.0,
    "assumption": "Rs 10.00 per min (editable)"
  },
  "audit_id": 42
}
```

---

## 7. Cost-Optimization Model: The Financial Impact of the Pre-Gate

In standard LLM voice agent architectures, incoming speech is transcribed via Automatic Speech Recognition (ASR), dispatched to a large foundation LLM (such as NVIDIA Nemotron), and converted back to speech via Text-to-Speech (TTS). In fraudulent attacks, every single second spent in dialogue processing incurs unnecessary compute fees:

$$\text{Savings Per Block} = \left(\frac{\text{Avoided Call Duration (seconds)}}{60}\right) \times \text{Compute Cost per Minute (INR)}$$

With default parameters in `backend/config.py`:
- `ASSUMED_COST_PER_MIN_INR = 10.0` ($\text{₹}10.00/\text{min}$)
- `EST_CALL_SECONDS_SAVED_PER_BLOCK = 120.0` ($2.0\text{ minutes}$)
- **Net Compute Saved Per Fraudulent Attack:** $\mathbf{₹20.00}$ **INR**

By filtering out AI clones and malicious synthetic robocalls at the **DetectifAI Pre-Gate level**, UnClone eliminates $100\%$ of the downstream LLM token consumption and TTS generation costs, safeguarding both bank capital and customer savings.
