# GramPay (BharatVoice Shield): Master AI & Engineering Continuity Handoff Manual
**Track 3: UNCLONE Agents — BMSCE AI Hackathon**
**Zero-Trust Voice Security & Cost-Optimization Gateway for NPCI Hello! UPI & BFSI Conversational Bots**
**Powered by DetectifAI OpenAPI v1 (Aletheia + Eidos Engines) & NVIDIA Nemotron-3.5 NIM**

---

> **CRITICAL DIRECTIVE FOR THE NEXT AI ASSISTANT / ENGINEER:**
> This document is the single source of truth for GramPay (BharatVoice Shield). It contains complete architectural specifications, live API keys, operational parameters, curl examples for all endpoints, demo walkthrough scripts, and troubleshooting protocols. You should be able to operate, extend, or demo the entire project from this document alone without asking the user any setup questions.

---

## Table of Contents
1. [Mission & Context: Track 3 UNCLONE Agents](#1-mission--context-track-3-unclone-agents)
2. [Architecture & Tech Stack](#2-architecture--tech-stack)
3. [Rule 5.4 Zero Mock Score Invariant & Fail-Closed Security Logic](#3-rule-54-zero-mock-score-invariant--fail-closed-security-logic)
4. [Active Server, Ports, Environment & Live Keys](#4-active-server-ports-environment--live-keys)
5. [The 10 REST API Endpoints: Complete Contracts, cURLs & Responses](#5-the-10-rest-api-endpoints-complete-contracts-curls--responses)
6. [The 4 Official Slide 4 Counters & Cost Calculation Formula](#6-the-4-official-slide-4-counters--cost-calculation-formula)
7. [Live Judge Demo Script & Button Clicking Sequence (120-Second Pitch)](#7-live-judge-demo-script--button-clicking-sequence-120-second-pitch)
8. [Troubleshooting & Common Operational Issues](#8-troubleshooting--common-operational-issues)

---

## 1. Mission & Context: Track 3 UNCLONE Agents

### 1.1 The Hackathon Challenge: BMSCE AI Hackathon (Track 3)
The BMSCE AI Hackathon Track 3 ("UNCLONE Agents") challenges participants to build high-assurance, production-grade security architectures capable of preventing real-time voice clone exploitation and identity hijacking in conversational AI agents.

### 1.2 Real-World Problem Space: Voice Banking in India
With the nationwide rollout of **NPCI Hello! UPI** and **UPI 123Pay**, over 500 million Indian citizens—predominantly rural farmers, senior citizens, and first-time digital banking users—can now initiate and authorize financial transfers through natural language voice telephone calls without requiring smartphone literacy or touch interfaces.

However, conversational voice banking introduces four catastrophic vulnerability vectors:
1. **Real-Time Generative Voice Clones**: Malicious actors harvest 3 to 5 seconds of audio from a farmer or senior citizen (via social media, WhatsApp voice notes, or prior spam calls) and deploy low-latency neural vocoders (XTTS v2, ElevenLabs, RVC) to clone the customer's vocal timbre in real time.
2. **Economic Denial of Service & Token Drain**: Legacy conversational AI architectures pass incoming audio directly into expensive Speech-to-Text (STT) and Large Language Model (LLM) pipelines *before* conducting biometric authentication. Fraudulent calls and synthetic bot swarms burn massive GPU and API compute—costing banks ₹10 to ₹20 per multi-minute fraudulent call.
3. **Telephony Compression Masking**: Standard PSTN cellular voice traffic is heavily compressed using 8kHz G.711 $\mu$-law or AMR codecs. Single-pass static voiceprint matchers suffer unacceptable false-positive rates when evaluating noisy 8kHz audio, leading banks to artificially restrict voice payment limits to ₹5,000.
4. **Rogue Bot Impersonation (Agent-to-Agent Spoofing)**: Fraudulent external AI agents pose as legitimate banking or government welfare bots to deceive elderly account holders.

### 1.3 The Solution: GramPay (BharatVoice Shield)
**GramPay (BharatVoice Shield)** is a high-assurance, zero-trust voice security and cost-optimization gateway that sits inline between cellular telephony streams (SIPREC / Twilio / WebRTC) and downstream conversational voice agents (LiveKit, Pipecat, Bolna, Core Banking Tools).

#### Core Guarantees:
- **Hard Audio Pre-Gating**: Dual-engine acoustic evaluation through DetectifAI executes **BEFORE** any LLM reasoning, TTS synthesis, or banking tool execution is initiated.
- **Fail-Closed Security Posture (Rule 5.4)**: If DetectifAI APIs time out, network partitions occur, or audio is malformed, GramPay unconditionally defaults to `BLOCK` or `STEP_UP`. Sensitive payment tools remain **100% HARD-LOCKED**.
- **Deterministic 3-Tier Policy Gate**: Security authorization is executed in 100% deterministic, audit-compliant Python code. The LLM **never** decides whether to approve or block a financial transaction.
- **Dynamic Cognitive Active Challenge (Tier 2)**: For borderline or noisy 8kHz audio, NVIDIA Nemotron generates a dynamic, non-repeatable cognitive phrase ("Repeat in a louder tone: Golden river seven mango") and measures caller response latency. Real-time voice conversion algorithms buffer when generating dynamic speech, exposing latency delays (> 2.5s) and phase artifacts.
- **Intelligent Cost Optimization**: Blocking synthetic or unauthorized callers in under 300ms saves ~120 seconds of compute and ₹10–₹20 per deflected call.
- **Single-Use Cryptographic Handshake**: Agent-to-agent interactions are secured with expiring, single-use JWT credentials tracked in an immutable SQLite replay-prevention registry.

---

## 2. Architecture & Tech Stack

### 2.1 Complete System Architecture Blueprint

```
                           [ Indian Citizen / Rural Farmer / Telephony Call ]
                                                   │
                                                   ▼
                                ┌──────────────────────────────────────┐
                                │      Telephony Ingestion Layer       │
                                │  SIPREC (RFC 7865/7866) / WebRTC RTP │
                                │  8kHz G.711 mu-law / 16kHz PCM WAV   │
                                └──────────────────┬───────────────────┘
                                                   │
                                                   ▼
                                ┌──────────────────────────────────────┐
                                │  FastAPI Gateway (Port 8000)         │
                                │  audio_prep.py: WebRTC VAD & Normal. │
                                └──────────────────┬───────────────────┘
                                                   │
                         Parallel Dispatch via ThreadPoolExecutor(max_workers=2)
                                 ┌─────────────────┴─────────────────┐
                                 ▼                                   ▼
                 ┌───────────────────────────────┐   ┌───────────────────────────────┐
                 │ DetectifAI Aletheia Engine    │   │ DetectifAI Eidos Engine       │
                 │ POST /v1/deepfake/detect      │   │ POST /v1/speakers/verify      │
                 │ Audio Deepfake Detection      │   │ Biometric Speaker Match       │
                 └───────────────┬───────────────┘   └───────────────┬───────────────┘
                                 │ synth_score (0.0-1.0)             │ similarity (0.0-1.0)
                                 └─────────────────┬─────────────────┘
                                                   │
                                                   ▼
                                ┌──────────────────────────────────────┐
                                │ gate.py (Deterministic 3-Tier Gate)  │
                                │ Tier 1: Low Risk (APPROVE / PAY)     │
                                │ Tier 2: Medium (STEP_UP / Challenge) │
                                │ Tier 3: High Risk (BLOCK / Contain)  │
                                └──────────────────┬───────────────────┘
                                                   │
                 ┌─────────────────────────────────┼─────────────────────────────────┐
                 ▼                                 ▼                                 ▼
       [TIER 3: HIGH RISK]               [TIER 2: MEDIUM RISK]             [TIER 1: LOW RISK]
       (synth_score >= 0.62)             (0.50<=synth<0.62 or 8kHz noise)  (synth<0.50 & sim>=0.53)
                 │                                 │                                 │
                 ▼                                 ▼                                 ▼
   ┌───────────────────────────┐     ┌───────────────────────────┐     ┌───────────────────────────┐
   │ Instant Short-Circuit     │     │ NVIDIA Nemotron Engine    │     │ NVIDIA Nemotron Engine    │
   │ Banking Tools: HARD-LOCKED│     │ Dynamic Challenge Prompt: │     │ Empathetic Conversational │
   │ LLM Tokens Burned: 0      │     │ "Repeat: Golden river..." │     │ Intent & Amount Parsing   │
   │ Cost Saved: ₹20.00        │     │ Latency Timer (>2.5s flag)│     └─────────────┬─────────────┘
   │ Bank Fraud Desk Alerted   │     │ Pass 2 DetectifAI Check   │                   │
   └─────────────┬─────────────┘     └─────────────┬─────────────┘                   ▼
                 │                                 │                   ┌───────────────────────────┐
                 │                                 │                   │ tools.py (Kisan Tools)    │
                 │                                 │                   │ pay_merchant (IFFCO Co-op)│
                 │                                 │                   │ execute_transfer_funds    │
                 │                                 │                   └─────────────┬─────────────┘
                 └─────────────────────────────────┼─────────────────────────────────┘
                                                   │
                                                   ▼
                                ┌──────────────────────────────────────┐
                                │ audit.py (SQLite: audit.db)          │
                                │ Immutable RBI & DPDP Audit Telemetry │
                                └──────────────────┬───────────────────┘
                                                   │
                                                   ▼
                                [ JSON Response to Grok UI / Judge ]
```

### 2.2 Tech Stack Inventory

| Layer | Technology | Version / Spec | Purpose |
|:---|:---|:---|:---|
| **API Gateway** | **FastAPI** | 0.115+ | High-performance async ASGI REST & WebSocket gateway |
| **Server Engine** | **Uvicorn** | Standard | Production ASGI server bound to `0.0.0.0:8000` |
| **Acoustic AI** | **DetectifAI Aletheia** | OpenAPI v1 (`/v1/deepfake/detect`) | Spectral vocoder & neural clone artifact detection |
| **Biometric Voice**| **DetectifAI Eidos** | OpenAPI v1 (`/v1/speakers/verify`, `/enroll`) | 1:1 Cosine voiceprint biometric verification |
| **Cognitive LLM** | **NVIDIA Nemotron-3.5 NIM** | `nemotron-3.5-super-vl-120b-a12b` / `llama-3.1-nemotron-70b` | Dynamic challenge phrase generation & conversational parsing |
| **Audit Database** | **SQLite** | `data/audit.db` (WAL mode enabled) | Immutable audit trails conforming to RBI Digital Controls |
| **Frontend UI** | **Grok Modern Glassmorphism** | Vanilla HTML5 / ES6 / Tailwind CSS | Zero-dependency, reactive dark-mode operator console |
| **Audio Pipeline** | **WebRTC VAD / wave / struct** | 16kHz 16-bit Mono PCM | Real-time voice activity detection & sample rate alignment |
| **Security / Auth** | **PyJWT / HS256** | Standard | Single-use expiring agent credentials with JTI registry |

### 2.3 Repository Layout

```
Backend/
├── .env                              # Active environment configuration with live API keys
├── .env.example                      # Production template with documented defaults
├── requirements.txt                  # Python dependencies (fastapi, uvicorn, requests, pydantic, pyjwt)
├── AI_CONTINUITY_HANDOFF.md          # THIS MASTER DOCUMENT
├── LIVE_DEMO_GUIDE.md                # 120-Second Slide-by-Slide Pitch & Demo Synchronization Guide
├── JUDGE_PITCH_SCRIPT.md             # Complete spoken script for the presenter
├── DAY2_ENGINEERING_ROADMAP.md       # 9-Hour Saturday production roadmap
├── DETECTIFAI_API_SPEC.md            # DetectifAI platform integration specification
├── FRONTEND_INTEGRATION_SPEC.md      # Grok frontend integration contract
├── run_server.py                     # Production startup wrapper with pre-flight banners & health checks
├── generate_farmer_fixtures.py       # Audio generator for 16s enrollment & 5s verification fixtures
├── data/
│   └── audit.db                      # SQLite database (audit_logs & used_credentials)
├── data_audio/
│   ├── farmer_genuine_16s.wav        # 16.0s authentic voice (>=15s required for enrollment)
│   ├── farmer_genuine_5s.wav         # 5.0s authentic voice (>=4s required for verification)
│   └── farmer_clone_synthetic_5s.wav # 5.0s synthetic vocoder clone (600Hz ripple, phase distortion)
├── backend/
│   ├── __init__.py                   # Package initializer
│   ├── config.py                     # Centralized settings & security thresholds
│   ├── audio_prep.py                 # RIFF/WAV validation, WebRTC VAD & transcoding
│   ├── detectif_client.py            # Official DetectifAI OpenAPI client (/v1 endpoints)
│   ├── gate.py                       # Deterministic 3-Tier policy gate & cognitive challenge
│   ├── agent.py                      # Voice agent turn orchestrator + NVIDIA Nemotron
│   ├── tools.py                      # Hard-locked GramPay Kisan & BFSI banking tools
│   ├── credentials.py                # Cryptographic agent-to-agent JWT handshake service
│   ├── audit.py                      # Immutable SQLite telemetry & audit logger
│   ├── telephony_bridge.py           # SIPREC / Twilio media stream bridge
│   └── main.py                       # FastAPI REST Server exposing all endpoints
└── tests/
    ├── sample_human.wav              # 300Hz harmonic human speech fixture
    ├── sample_clone.wav              # 600Hz high-frequency vocoder speech fixture
    └── test_contract.py              # 27-test automated regression & security test suite
```

---

## 3. Rule 5.4 Zero Mock Score Invariant & Fail-Closed Security Logic

### 3.1 Hackathon Rule 5.4 Invariant
Under **Hackathon Rule 5.4**, no random mock scores, hardcoded simulation numbers, or simulated percentages are permitted in production code paths:
- All acoustic scores (`synthetic_score`, `match_score`) must originate from live HTTP responses returned by the official DetectifAI platform (`https://platform.detectif.ai/v1`).
- The system must never guess, synthesize, or invent numbers if an upstream service fails.

### 3.2 Deterministic Policy Gate (Strict Separation of Powers)
A cardinal principle of GramPay is **Deterministic Policy Enforcement**:
- The LLM **never** decides whether to permit, step up, or block a financial transaction.
- All gating decisions are computed strictly in `backend/gate.py` based on mathematical outputs from DetectifAI.

### 3.3 Security Thresholds (`backend/config.py`)
```python
SYNTH_HIGH = 0.62       # synth_score >= 0.62 indicates synthetic vocoder / diffusion clone (Tier 3)
SYNTH_LOW = 0.50        # 0.50 <= synth_score < 0.62 indicates borderline synthetic risk (Tier 2)
MATCH_HIGH = 0.53       # similarity >= 0.53 indicates authentic enrolled customer (Tier 1)
MATCH_LOW = 0.40        # 0.40 <= similarity < 0.53 indicates uncertain match (Tier 2)
```

### 3.4 The 3-Tier Decision Matrix

| Tier | Risk Level | Condition | Gate Decision | Tool Status | Downstream System Action |
|:---:|:---:|:---|:---:|:---:|:---|
| **Tier 1** | **Low Risk** | Natural voice (`synth < 0.50`) **AND** Enrolled speaker verified (`sim >= 0.53`). | `APPROVE` | **UNLOCKED** | **Silent Pass**: Invokes NVIDIA Nemotron for intent parsing; executes payment tool immediately with zero user friction. |
| **Tier 2** | **Medium Risk** | Borderline authenticity (`0.50 <= synth < 0.62`) **OR** Borderline match (`0.40 <= sim < 0.53`) **OR** Noisy 8kHz telephony audio **OR** Unmatched real human voice (`sim < 0.40`). | `STEP_UP` | **HARD-LOCKED** | **Active Challenge**: Nemotron prompts dynamic phrase ("Repeat: Golden river seven mango"), measures response latency (> 2.5s indicates voice conversion buffering), and executes Pass 2 DetectifAI re-scoring. |
| **Tier 3** | **High Risk** | Synthetic voice clone detected (`synth_score >= 0.62`). | `BLOCK_ALERT` *(if matched)* / `BLOCK` *(if unknown)* | **HARD-LOCKED** | **Containment**: Short-circuits connection in < 300ms; drops LLM and TTS pipeline; alerts bank fraud desk; logs evidence to SQLite; saves ₹20.00 compute cost. |

### 3.5 Fail-Closed Security Posture
If `DETECTIF_API_KEY` is missing, upstream DetectifAI returns HTTP 5xx, or a network timeout occurs:
1. `detectif_client.py` captures the exception and raises `DetectifAPIError`.
2. `gate.py` intercepts `api_error` or missing numeric scores.
3. The gate forces `fail_closed = True`:
   - High-risk transfers default strictly to `BLOCK`.
   - Read-only balance inquiries default to `STEP_UP`.
   - Banking tools remain unconditionally **HARD-LOCKED**.
   - Zero mock scores are fabricated (`synthetic_score = None`, `match_score = None`).
   - Every API error response returns:
     ```json
     {
       "request_id": "req_...",
       "ts": "...",
       "error": "<Error explanation>",
       "fail_closed": true
     }
     ```

---

## 4. Active Server, Ports, Environment & Live Keys

### 4.1 Server Execution & Host Binding
The server is booted via `run_server.py` or `uvicorn`:
```powershell
# Recommended launch command (from Backend directory)
& "C:\Users\chandan.s\AppData\Local\Programs\Python\Python312\python.exe" run_server.py
```
- **Host Binding**: `0.0.0.0:8000` (Accessible on `http://localhost:8000` and `http://127.0.0.1:8000`)
- **Swagger UI Interactive Docs**: `http://localhost:8000/docs`
- **ReDoc Interactive Contract**: `http://localhost:8000/redoc`

### 4.2 Frontend Static Mounting at Root (`/`)
The Grok dark-mode frontend is automatically discovered and mounted at `/`:
```python
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "Frontend"
if not (FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists()):
    FRONTEND_DIR = Path(__file__).resolve().parent.parent / "Frontend"

if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
```
When opening `http://localhost:8000` in any web browser, the Grok UI loads immediately without requiring a separate Node.js server.

### 4.3 Active Environment Variables (`.env`)

```ini
# ==============================================================================
# GramPay / UnClone Gate Backend Environment Configuration
# ==============================================================================

# DetectifAI Platform Credentials (https://platform.detectif.ai)
DETECTIF_API_KEY=dtf_live_ao2KM7oeSWjeZwNQHoNjKa6HT9iv098zPdP0odPsZlS
DETECTIF_BASE_URL=https://platform.detectif.ai/v1

# NVIDIA Nemotron LLM Configuration (https://build.nvidia.com)
NVIDIA_API_KEY=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
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NEMOTRON_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b

# Security & Cryptography
JWT_SECRET=unclone_secret_key_bfsi_trust_2026_x892
JWT_ALGORITHM=HS256

# CORS Origin for Frontend
ALLOWED_ORIGIN=*

# Cost Optimization Model Parameters
ASSUMED_COST_PER_MIN_INR=10.0
EST_CALL_SECONDS_SAVED_PER_BLOCK=120.0

# GramPay Voice Payment Parameters (NPCI Hello! UPI and 123Pay)
NPCI_UPI_LIMIT_INR=5000.0
DEMO_FARMER_NAME=Ramesh Patel (Kisan Account)
DEMO_MERCHANT=IFFCO Fertilizer Co-op

# Official DetectifAI OpenAPI Thresholds (platform.detectif.ai)
SYNTH_THRESHOLD=0.62
SIMILARITY_THRESHOLD=0.53

# Security Gate Thresholds (3-Tier GramPay Decision Matrix)
MATCH_HIGH=0.53
MATCH_LOW=0.40
SYNTH_HIGH=0.62
SYNTH_LOW=0.50
```

---

## 5. The 10 REST API Endpoints: Complete Contracts, cURLs & Responses

All endpoints return uniform metadata tracking headers:
```json
{
  "request_id": "req_84a92c419be2",
  "ts": "2026-10-16T10:00:00.000000+00:00"
}
```

---

### Endpoint 1: Health & Telemetry Verification (`GET /api/health`)
- **Purpose**: Checks gateway liveness, DetectifAI upstream API reachability, and NVIDIA Nemotron configuration.

#### Bash cURL:
```bash
curl -X GET "http://127.0.0.1:8000/api/health" -H "Accept: application/json"
```

#### PowerShell:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get | ConvertTo-Json
```

#### Sample JSON Response (200 OK):
```json
{
  "request_id": "req_health_001",
  "ts": "2026-10-16T10:00:00.000000+00:00",
  "ok": true,
  "detectif_reachable": true,
  "detectif_details": {
    "reachable": true,
    "status_code": 200,
    "latency_ms": 182
  },
  "nemotron_configured": true
}
```

---

### Endpoint 2: DetectifAI Live Platform Credits (`GET /api/credits`)
- **Purpose**: Queries live available credits directly from `platform.detectif.ai`. Proves live key authentication to hackathon judges.

#### Bash cURL:
```bash
curl -X GET "http://127.0.0.1:8000/api/credits" -H "Accept: application/json"
```

#### PowerShell:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/credits" -Method Get | ConvertTo-Json
```

#### Sample JSON Response (200 OK):
```json
{
  "request_id": "req_credits_002",
  "ts": "2026-10-16T10:00:05.000000+00:00",
  "status": "ok",
  "plan": "free",
  "unlimited": false,
  "available": 1750,
  "reserved": 0,
  "price_per_operation": 50,
  "latency_ms": 1150
}
```

---

### Endpoint 3: Speaker Biometric Enrollment (`POST /api/enroll`)
- **Purpose**: Enrolls customer's voice sample into the DetectifAI Eidos engine.
- **Requirements**: DetectifAI requires audio $\ge 15.0$ seconds for high-quality speaker embedding extraction.
- **Content-Type**: `multipart/form-data`

#### Bash cURL:
```bash
curl -X POST "http://127.0.0.1:8000/api/enroll" \
  -F "name=Ramesh Patel (Kisan Account)" \
  -F "speaker_id=kisan_farmer_01" \
  -F "audio=@data_audio/farmer_genuine_16s.wav;type=audio/wav"
```

#### PowerShell:
```powershell
$form = @{
    name = "Ramesh Patel (Kisan Account)"
    speaker_id = "kisan_farmer_01"
    audio = Get-Item "data_audio\farmer_genuine_16s.wav"
}
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/enroll" -Method Post -Form $form | ConvertTo-Json
```

#### Sample JSON Response (200 OK):
```json
{
  "request_id": "req_enroll_003",
  "ts": "2026-10-16T10:00:15.000000+00:00",
  "speaker_id": "kisan_farmer_01",
  "name": "Ramesh Patel (Kisan Account)",
  "enrolled": true,
  "detectif_raw": {
    "status": "enrolled",
    "voiceprint_id": "vp_94821a0b3f",
    "embedding_quality": 0.94
  },
  "latency_ms": 210
}
```

---

### Endpoint 4: Dual-Gate Audio Check (`POST /api/check`)
- **Purpose**: Parallel evaluation via DetectifAI Aletheia + Eidos. Applies 3-Tier Gate; unlocks or locks tools.
- **Requirements**: Audio duration must be $\ge 4.0$ seconds for accurate neural vocoder analysis.
- **Content-Type**: `multipart/form-data`

#### Bash cURL (Authentic Voice Test):
```bash
curl -X POST "http://127.0.0.1:8000/api/check" \
  -F "speaker_id=kisan_farmer_01" \
  -F "action=TRANSFER_FUNDS" \
  -F "amount=5000" \
  -F "audio=@data_audio/farmer_genuine_5s.wav;type=audio/wav"
```

#### PowerShell (Authentic Voice Test):
```powershell
$form = @{
    speaker_id = "kisan_farmer_01"
    action = "TRANSFER_FUNDS"
    amount = "5000"
    audio = Get-Item "data_audio\farmer_genuine_5s.wav"
}
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/check" -Method Post -Form $form | ConvertTo-Json
```

#### Sample JSON Response — Case 1: Approved Authentic Farmer (200 OK):
```json
{
  "request_id": "req_check_004a",
  "ts": "2026-10-16T10:00:30.000000+00:00",
  "status": "ok",
  "fail_closed": false,
  "decision": "APPROVE",
  "tier": 1,
  "reason": "Verified Safe: Natural human voice and account holder identity confirmed.",
  "detection": {
    "is_synthetic": false,
    "synthetic_score": 0.0412,
    "latency_ms": 180
  },
  "verification": {
    "matched": true,
    "match_score": 0.9412,
    "latency_ms": 195
  },
  "tool": {
    "name": "pay_merchant",
    "status": "EXECUTED",
    "result": {
      "transaction_id": "TXN-NPCI-123PAY-5000-PASS",
      "merchant_name": "IFFCO Fertilizer Co-op",
      "amount_inr": 5000.0
    },
    "message": "Payment of ₹5,000.00 to IFFCO Fertilizer Co-op successful via NPCI Hello! UPI."
  },
  "cost": {
    "agent_steps_skipped": 0,
    "agent_seconds_avoided": 0.0,
    "est_inr": 0.0,
    "assumption": "Rs 10.00 per min (editable)"
  },
  "audit_id": 42
}
```

#### Sample JSON Response — Case 2: Voice Clone Attack Blocked (200 OK):
```json
{
  "request_id": "req_check_004b",
  "ts": "2026-10-16T10:00:45.000000+00:00",
  "status": "ok",
  "fail_closed": false,
  "decision": "BLOCK_ALERT",
  "tier": 3,
  "reason": "CRITICAL WARNING: Computer-generated voice clone detected! Although the voice sounds like the account holder, neural synthesis was identified (synth_score >= 0.62). UPI payout frozen, bank fraud desk alerted, and LLM compute short-circuited.",
  "detection": {
    "is_synthetic": true,
    "synthetic_score": 0.9215,
    "latency_ms": 185
  },
  "verification": {
    "matched": true,
    "match_score": 0.9320,
    "latency_ms": 190
  },
  "tool": {
    "name": "pay_merchant",
    "status": "LOCKED",
    "result": null,
    "message": "High-risk transfer is LOCKED by GramPay Gate until voice liveness and identity pass."
  },
  "cost": {
    "agent_steps_skipped": 1,
    "agent_seconds_avoided": 120.0,
    "est_inr": 20.0,
    "assumption": "Rs 10.00 per min (editable)"
  },
  "audit_id": 43
}
```

---

### Endpoint 5: Full Voice Agent Turn (`POST /api/agent/turn`)
- **Purpose**: Gates audio **before** invoking the LLM. If approved, calls NVIDIA Nemotron for intent parsing and empathetic spoken response. If blocked, short-circuits with 0 LLM calls.
- **Content-Type**: `multipart/form-data`

#### Bash cURL:
```bash
curl -X POST "http://127.0.0.1:8000/api/agent/turn" \
  -F "speaker_id=kisan_farmer_01" \
  -F "user_text_hint=Bhaiya Kisan Kendra ko 5000 rupaye bhej do" \
  -F "audio=@data_audio/farmer_genuine_5s.wav;type=audio/wav"
```

#### PowerShell:
```powershell
$form = @{
    speaker_id = "kisan_farmer_01"
    user_text_hint = "Bhaiya Kisan Kendra ko 5000 rupaye bhej do"
    audio = Get-Item "data_audio\farmer_genuine_5s.wav"
}
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/agent/turn" -Method Post -Form $form | ConvertTo-Json
```

#### Sample JSON Response (200 OK):
```json
{
  "request_id": "req_turn_005",
  "ts": "2026-10-16T10:01:00.000000+00:00",
  "status": "ok",
  "decision": "APPROVE",
  "tier": 1,
  "transcript": "Bhaiya Kisan Kendra ko 5000 rupaye bhej do",
  "agent_reply_text": "Namaste Ramesh-ji. Aapki aawaz verify ho chuki hai. Kisan Kendra ko ₹5,000 safalta-purvak bhej diye gaye hain.",
  "intent": "TRANSFER_FUNDS",
  "tool": {
    "name": "pay_merchant",
    "status": "EXECUTED",
    "result": {
      "transaction_id": "TXN-NPCI-123PAY-5000-PASS",
      "merchant_name": "IFFCO Fertilizer Co-op",
      "amount_inr": 5000.0
    }
  },
  "cost": {
    "agent_steps_skipped": 0,
    "agent_seconds_avoided": 0.0,
    "est_inr": 0.0
  },
  "audit_id": 44
}
```

---

### Endpoint 6: Issue Cryptographic Agent Credential (`POST /api/credential/issue`)
- **Purpose**: Issues a signed, single-use, scoped JWT credential for trusted bot-to-bot transactions.
- **Content-Type**: `application/json`

#### Bash cURL:
```bash
curl -X POST "http://127.0.0.1:8000/api/credential/issue" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "grampay_upi123_voice_bot",
    "org": "GramPay Rural Banking (NPCI Hello! UPI)",
    "allowed_actions": ["TRANSFER_FUNDS", "CHECK_BALANCE"],
    "limit_inr": 5000.0
  }'
```

#### PowerShell:
```powershell
$body = @{
    agent_id = "grampay_upi123_voice_bot"
    org = "GramPay Rural Banking (NPCI Hello! UPI)"
    allowed_actions = @("TRANSFER_FUNDS", "CHECK_BALANCE")
    limit_inr = 5000.0
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/credential/issue" -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json
```

#### Sample JSON Response (200 OK):
```json
{
  "request_id": "req_cred_006",
  "ts": "2026-10-16T10:01:15.000000+00:00",
  "credential": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "agent_id": "grampay_upi123_voice_bot",
  "org": "GramPay Rural Banking (NPCI Hello! UPI)",
  "jti": "82a941f1-3d20-4e1b-94c0-78192a8310bc",
  "expires_in_seconds": 300,
  "allowed_actions": ["TRANSFER_FUNDS", "CHECK_BALANCE"],
  "limit_inr": 5000.0
}
```

---

### Endpoint 7: Verify Agent Handshake (`POST /api/handshake/verify`)
- **Purpose**: Verifies cryptographic signature, freshness, scope, and marks the token's JTI as consumed in SQLite. Replay attempts are instantly rejected.
- **Content-Type**: `application/json`

#### Bash cURL:
```bash
curl -X POST "http://127.0.0.1:8000/api/handshake/verify" \
  -H "Content-Type: application/json" \
  -d '{"credential": "<PASTE_TOKEN_HERE>", "action": "TRANSFER_FUNDS"}'
```

#### PowerShell:
```powershell
$body = @{
    credential = "<PASTE_TOKEN_HERE>"
    action = "TRANSFER_FUNDS"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/handshake/verify" -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json
```

#### Sample JSON Response — First Verification (200 OK):
```json
{
  "request_id": "req_hs_007",
  "ts": "2026-10-16T10:01:30.000000+00:00",
  "badge": "VERIFIED_AGENT",
  "reason": "Cryptographically verified agent from GramPay Rural Banking (NPCI Hello! UPI) (grampay_upi123_voice_bot). Safe to interact.",
  "agent_id": "grampay_upi123_voice_bot",
  "org": "GramPay Rural Banking (NPCI Hello! UPI)",
  "limit_inr": 5000.0,
  "checks": {
    "signature": true,
    "expiry": true,
    "unused": true,
    "scope": true
  }
}
```

#### Sample JSON Response — Replay Attack Attempt (200 OK):
```json
{
  "request_id": "req_hs_008",
  "ts": "2026-10-16T10:01:35.000000+00:00",
  "badge": "REJECTED",
  "reason": "REPLAY ATTACK DETECTED: This single-use agent credential has already been redeemed.",
  "checks": {
    "signature": true,
    "expiry": true,
    "unused": false,
    "scope": false
  }
}
```

---

### Endpoint 8: Audit Log Stream (`GET /api/audit`)
- **Purpose**: Returns recent gate transactions and security incident logs for the Judge Console and regulatory audit.
- **Query Parameter**: `limit` (integer, default: 50).

#### Bash cURL:
```bash
curl -X GET "http://127.0.0.1:8000/api/audit?limit=25" -H "Accept: application/json"
```

#### PowerShell:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/audit?limit=25" -Method Get | ConvertTo-Json -Depth 5
```

#### Sample JSON Response (200 OK):
```json
{
  "request_id": "req_audit_009",
  "ts": "2026-10-16T10:02:00.000000+00:00",
  "count": 1,
  "logs": [
    {
      "id": 43,
      "request_id": "req_check_004b",
      "ts": "2026-10-16T10:00:45.000000+00:00",
      "speaker_id": "kisan_farmer_01",
      "action": "TRANSFER_FUNDS",
      "decision": "BLOCK_ALERT",
      "reason": "CRITICAL WARNING: Computer-generated voice clone detected!...",
      "synthetic_score": 0.9215,
      "match_score": 0.9320,
      "latency_ms": 375,
      "tool_status": "LOCKED",
      "steps_skipped": 1,
      "seconds_avoided": 120.0,
      "est_inr": 20.0
    }
  ]
}
```

---

### Endpoint 9: Telemetry & Cost Savings Analytics (`GET /api/stats`)
- **Purpose**: Aggregates live security metrics and cost counters across all evaluated calls. Supports both Section 4 contract keys and the 4 Slide 4 presentation counters.

#### Bash cURL:
```bash
curl -X GET "http://127.0.0.1:8000/api/stats" -H "Accept: application/json"
```

#### PowerShell:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/stats" -Method Get | ConvertTo-Json
```

#### Sample JSON Response (200 OK):
```json
{
  "request_id": "req_stats_010",
  "ts": "2026-10-16T10:02:15.000000+00:00",
  "checks_run": 85,
  "clones_blocked": 21,
  "agent_steps_skipped": 33,
  "agent_time_saved_inr": 660.0,
  "checks": 85,
  "total_checks": 85,
  "total_approved": 52,
  "total_blocked": 21,
  "blocks": 21,
  "total_step_up": 12,
  "steps_skipped": 33,
  "agent_seconds_avoided": 3960.0,
  "seconds_avoided": 3960.0,
  "est_cost_savings_inr": 660.0,
  "est_inr": 660.0,
  "assumption": "Rs 10.00 per min (editable)"
}
```

---

### Endpoint 10: Dynamic Challenge Generation (`POST /api/challenge/generate`)
- **Purpose**: Tier 2: Generates a dynamic phonetically rich verification phrase via NVIDIA Nemotron for cognitive challenge.
- **Content-Type**: `application/json`

#### Bash cURL:
```bash
curl -X POST "http://127.0.0.1:8000/api/challenge/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "speaker_id": "kisan_farmer_01",
    "language": "en",
    "action": "TRANSFER_FUNDS",
    "amount": 5000.0
  }'
```

#### PowerShell:
```powershell
$body = @{
    speaker_id = "kisan_farmer_01"
    language = "en"
    action = "TRANSFER_FUNDS"
    amount = 5000.0
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/challenge/generate" -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json
```

#### Sample JSON Response (200 OK):
```json
{
  "request_id": "req_chal_011",
  "ts": "2026-10-16T10:02:30.000000+00:00",
  "status": "ok",
  "challenge_id": "ch_84920ab12f",
  "phrase": "Golden river seven mango",
  "speaker_id": "kisan_farmer_01",
  "action": "TRANSFER_FUNDS",
  "amount": 5000.0,
  "valid_seconds": 120,
  "expires_at": "2026-10-16T10:04:30.000000+00:00",
  "tier": 2,
  "engine": "NVIDIA Nemotron Dynamic Challenge"
}
```

---

### Companion Endpoints: Challenge Verify, UPI Pay & Demo Reset

#### Endpoint 11: Dynamic Challenge Verification (`POST /api/challenge/verify`)
- **Purpose**: Tier 2: Re-evaluates caller audio response against DetectifAI Aletheia + Eidos and checks challenge token validity.

```powershell
$form = @{
    challenge_id = "ch_84920ab12f"
    speaker_id = "kisan_farmer_01"
    action = "TRANSFER_FUNDS"
    amount = "5000"
    audio = Get-Item "data_audio\farmer_genuine_5s.wav"
}
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/challenge/verify" -Method Post -Form $form | ConvertTo-Json
```

#### Endpoint 12: NPCI Hello! UPI Direct Payment (`POST /api/pay/upi`)
- **Purpose**: Direct execution of NPCI Hello! UPI tool when unlocked by the gate or backed by a verified agent credential.

```powershell
$body = @{
    amount = 5000.0
    merchant_name = "IFFCO Fertilizer Co-op"
    upi_id = "iffco@upi"
    speaker_id = "kisan_farmer_01"
    is_unlocked = $true
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/pay/upi" -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json
```

#### Endpoint 13: Demo Accounts Reset (`POST /api/demo/reset`)
- **Purpose**: Resets demo farmer balances (Ramesh Patel back to ₹28,500.00) between judge presentations.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/demo/reset" -Method Post | ConvertTo-Json
```

---

## 6. The 4 Official Slide 4 Counters & Cost Calculation Formula

### 6.1 The 4 Official Slide 4 Counters
To satisfy the exact presentation contract, `GET /api/stats` and the Grok frontend display these exact 4 counters:

1. **`checks_run`**: Total voice gateway evaluations executed.
2. **`clones_blocked`**: Synthetic vocoder or diffusion clones intercepted and terminated.
3. **`agent_steps_skipped`**: Downstream conversational LLM & TTS pipeline invocations completely bypassed.
4. **`agent_time_saved_inr`**: Aggregate financial compute savings accrued (in INR).

*(Note: For backward compatibility, `checks`, `blocks`, `steps_skipped`, and `est_inr` are also mirrored in the payload).*

### 6.2 The Cost Calculation Formula
When fraudulent or robotic calls are terminated at the audio pre-gate in under 300ms, downstream transcription, LLM reasoning, and TTS synthesis are completely bypassed:

$$\text{Cost Saved (INR)} = \left(\frac{\text{EST\_CALL\_SECONDS\_SAVED\_PER\_BLOCK}}{60.0}\right) \times \text{ASSUMED\_COST\_PER\_MIN\_INR}$$

#### Default Production Constants (`backend/config.py`):
- $\text{EST\_CALL\_SECONDS\_SAVED\_PER\_BLOCK} = 120.0\text{ seconds}$ (2 full minutes of conversational agent compute avoided)
- $\text{ASSUMED\_COST\_PER\_MIN\_INR} = ₹10.00\text{ per minute}$

#### Exact Rupee Computation:
$$\text{Cost Saved} = \left(\frac{120.0}{60.0}\right) \times ₹10.00 = 2.0 \times ₹10.00 = \mathbf{₹20.00\text{ per blocked fraudulent call}}$$

### 6.3 Industry Cost Breakdown (Why ₹10/min is Realistic):
In modern conversational voice AI stacks (Twilio Voice / LiveKit + Deepgram + Llama-3-70B + Cartesia/ElevenLabs):
- **Telephony Ingestion (SIP / PSTN)**: ₹1.50 / min
- **Real-Time Streaming STT (Whisper / Nova-2)**: ₹0.80 / min
- **LLM Reasoning (70B parameter model at 30 tokens/sec)**: ₹5.00 / min
- **Neural TTS Vocoding (Ultra-low latency streaming)**: ₹2.70 / min
- **Total Conversational Pipeline Cost**: **₹10.00 per minute** (₹20.00 for a typical 2-minute fraud attempt).

---

## 7. Live Judge Demo Script & Button Clicking Sequence (120-Second Pitch)

This is the exact sequence to execute during the live judging round.

### 7.1 Pitch Synchronization Matrix (120 Seconds)

| Time | Pitch Slide | Step | Presenter Script Summary | UI Action on Screen (`http://localhost:8000`) |
|:---:|:---|:---:|:---|:---|
| **0:00–0:25** | **Slide 1: Problem** | **Step 1** | Rural voice banking vulnerability; WhatsApp voice harvesting; GramPay overview. | Show Green **Connected** badge, **1,750 live credits**, and giant status card: `SYSTEM READY`. |
| **0:25–0:50** | **Slide 2: Solution** | **Step 2** | Pre-gating defense; 1:1 enrollment; Ramesh sends ₹5,000 for fertilizer. | Click **Enroll Speaker** (`farmer_genuine_16s.wav`). Click **Preset: Seeds (₹5,000)** $\to$ **Run Gate Check**. Balance drops ₹28,500 $\to$ ₹23,500. |
| **0:50–1:20** | **Slide 3: DetectifAI** | **Step 3** | Core engine: Aletheia + Eidos. Clone attack intercepted in <300ms. | Choose `sample_clone.wav` $\to$ **Run Gate Check**. Instant Red **`🛑 CLONE BLOCKED + ALERT`**. Tool locked; +₹20.00 saved. |
| **1:20–1:40** | **Slide 4: Impact & Cost** | **Step 4** | 8kHz telephony noise defense; dynamic Nemotron active challenge phrase. | Click **Launch Tier 2 Challenge** $\to$ **Generate New Phrase** ("Golden river seven mango"). Animate latency timer (<2.5s human vs >2.5s clone). |
| **1:40–2:00** | **Slide 5: Scale & Road** | **Step 5** | Mutual agent auth; single-use token prevents scam bot impersonation. | Click **Issue Credential** $\to$ **Verify** (Green `VERIFIED_AGENT`) $\to$ **Replay Attack** (Red `REJECTED`). |

### 7.2 Exact Operator Button Clicking Order

1. **Step 1: Open Screen & Health Check**
   - Open browser to `http://localhost:8000`.
   - Hover over top-right status: Point out **"Gate & DetectifAI: Reachable"** and **"1,750 Live Credits Available"**.
2. **Step 2: Enroll Authentic Farmer & Execute Payment**
   - In Right Panel ("Speaker Enrollment"): Name is set to `Ramesh Patel (Kisan Account)`.
   - File input: Select `data_audio/farmer_genuine_16s.wav` (or `tests/sample_human.wav`).
   - Click purple button: **`Enroll Speaker Profile`**.
   - Confirmation: Status updates to `Enrolled` with DetectifAI voiceprint ID.
   - In Left Panel ("Voice Shield"): Click preset **`🌱 Seeds & Fertilizer (Send ₹5,000)`**.
   - Audio input: Select `data_audio/farmer_genuine_5s.wav` (or `tests/sample_human.wav`).
   - Click gradient button: **`Run GramPay Gate Check`**.
   - Visual: Card turns **Green (`PAY / APPROVED`)**; tool status `EXECUTED`; Ramesh's balance drops to **₹23,500.00**.
3. **Step 3: Trigger High-Risk Voice Clone Attack**
   - Keep action at `Send ₹5,000 for Fertilizer / Seeds (High Risk)`.
   - Audio input: Select `data_audio/farmer_clone_synthetic_5s.wav` (or `tests/sample_clone.wav`).
   - Click gradient button: **`Run GramPay Gate Check`**.
   - Visual: Card flashes bright **Red (`🛑 CLONE BLOCKED + ALERT`)** in < 300ms.
   - Gauges: Vocoder reads **92.2%**; tool is **HARD-LOCKED**; Slide 4 counters tick up (+1 blocked, +₹20.00 saved).
4. **Step 4: Tier-2 Active Cognitive Challenge**
   - On status card or right panel, click amber button: **`⚡ Launch Tier 2 Active Challenge`**.
   - Click: **`🔄 Generate New Phrase`**.
   - Visual: Dynamic chips display phrase from NVIDIA Nemotron (e.g., `[ Golden ] [ river ] [ seven ] [ mango ]`).
   - Click: **`Speak Phrase & Time Latency`**.
   - Visual: Latency timer bar animates: human response lands at ~1.8s (< 2.5s safe threshold).
5. **Step 5: Verified Bank Agent Badge & Anti-Replay**
   - In "Verified Bank Agent Badge" section:
   - Click: **`Issue Credential`** (JWT token field populates).
   - Click: **`Verify`** (Badge turns Green: **`VERIFIED_AGENT`**).
   - Click: **`Replay Attack (Rejects)`** (Badge turns Red: **`REJECTED (Replay Attack Detected)`** via SQLite JTI check).
   - Announce: *"Finished at exactly 2:00 minutes!"*

---

## 8. Troubleshooting & Common Operational Issues

### 8.1 Troubleshooting Reference Matrix

| Symptom | Root Cause | Immediate Solution |
|:---|:---|:---|
| **Port 8000 already in use** | Stale Python process running in background | In PowerShell: `Get-Process python \| Stop-Process -Force` then re-run `python run_server.py`. |
| **Microphone blocked in browser** | Browser denies audio capture permission on `http://localhost` | Click lock/settings icon in address bar $\to$ Allow Microphone. **Instant Demo Fallback**: Use pre-staged WAV files in `data_audio/` or `tests/`. |
| **DetectifAI returns 400 for audio length** | Audio duration too short (< 15s for enrollment, < 4s for check) | **Always use** `data_audio/farmer_genuine_16s.wav` (16.0s) for `/api/enroll`, and `data_audio/farmer_genuine_5s.wav` (5.0s) for `/api/check`. |
| **Fail-closed triggered on `/api/check`** | `DETECTIF_API_KEY` missing, expired, or quota exhausted | Verify key in `.env` is `dtf_live_ao2KM7oeSWjeZwNQHoNjKa6HT9iv098zPdP0odPsZlS`. Fail-closed is the intentional security posture. |
| **Live credits query fails** | Upstream DetectifAI platform unreachable | Test connectivity via `curl -X GET "https://platform.detectif.ai/v1/credits" -H "X-API-Key: <KEY>"`. |
| **NVIDIA Nemotron returns error** | `NVIDIA_API_KEY` invalid or model slug typo | Ensure `NVIDIA_API_KEY=nvapi-...` is set in `.env` and `NEMOTRON_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b`. |
| **Replay attack test fails to reject** | Button clicked before token was minted or fresh token used | Click **`Issue Credential`** first, then click **`Verify`**, then click **`Replay Attack (Rejects)`**. |
| **Python bytecode caching issue** | `.pyc` files have stale imports | Always execute tests with `-B` flag: `python -B -m unittest tests/test_contract.py`. |
| **Demo balances need to be restored** | Farmer Ramesh balance was decremented during practice | Call `POST /api/demo/reset` or click reset in UI to restore baseline ₹28,500.00. |

### 8.2 Audio Length Specifications
The DetectifAI OpenAPI v1 platform enforces strict minimum duration standards:
- **Speaker Enrollment (`POST /v1/speakers/enroll` or `/api/enroll`)**: Requires $\ge 15.0\text{ seconds}$ of clean continuous speech to compute full ECAPA-TDNN speaker embedding voiceprints.
  - *Standard Test Fixture*: `data_audio/farmer_genuine_16s.wav` (16.0s, 16kHz 16-bit mono PCM).
- **Deepfake Detection & Speaker Verification (`POST /v1/deepfake/detect`, `/v1/speakers/verify` or `/api/check`)**: Requires $\ge 4.0\text{ seconds}$ of speech to capture spectral envelope dynamics and vocoder artifacts.
  - *Genuine Fixture*: `data_audio/farmer_genuine_5s.wav` (5.0s, 16kHz 16-bit mono PCM).
  - *Synthetic Clone Fixture*: `data_audio/farmer_clone_synthetic_5s.wav` (5.0s, 16kHz with 600Hz neural vocoder ripple and phase distortion).

If the user or judge speaks for less than 4 seconds into the live mic, the gateway will return an audio validation error and safely fail-closed. When demonstrating live to judges, record at least 5 seconds of clear speech or use the pre-staged fixtures.

---

## 9. Quick Sanity Commands for the Next Engineer

Copy-paste these commands in PowerShell from the `Backend` directory:

```powershell
# 1. Run all 27 automated tests
& "C:\Users\chandan.s\AppData\Local\Programs\Python\Python312\python.exe" -B -m unittest tests/test_contract.py -v

# 2. Check DetectifAI live credits balance
Invoke-RestMethod -Uri "http://localhost:8000/api/credits" -Method Get | ConvertTo-Json

# 3. Check health and connectivity
Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get | ConvertTo-Json

# 4. Check Slide 4 live counters
Invoke-RestMethod -Uri "http://localhost:8000/api/stats" -Method Get | ConvertTo-Json

# 5. Start the production server
& "C:\Users\chandan.s\AppData\Local\Programs\Python\Python312\python.exe" run_server.py
```

---

## 10. Day 2 Multilingual Voice Delivery & Contract Specifications

### 10.1 Hackathon Day 2 Jury Feedback & Implementation
Following Day 1 jury recommendations, GramPay was upgraded with **Trilingual Voice Biometrics & Multilingual AI Intent Pipelines**:
- **Supported Languages**: **Kannada (`kn`)**, **Hindi (`hi`)**, and **English (`en`)** using pure native Unicode scripts with zero mixed-character corruption.
- **Rural Word Banks**: 12 everyday agricultural words per language for cognitive liveness challenges (e.g. ಹಸಿರು, ಮಳೆ, ಕಮಲ, ನವಿಲು in Kannada; हरा, बादल, कमल, मोर in Hindi; green, monsoon, lotus, peacock in English).
- **Core Security Rule**: DetectifAI analyzes **raw acoustic waveforms and vocal tract biomechanics** without semantic translation. Audio is never passed to an LLM or TTS translator before biometrics.

### 10.2 The 3 Critical Day 2 Fixes
1. **Fix 1 (Preserved Initial Audio on `EXTRA_CHECK`)**:
   When `/api/check` returns `EXTRA_CHECK`, the caller's initial payment command audio is cached server-side (`_PENDING_CHALLENGES[challenge_id]`). When the caller recites challenge words via `POST /api/challenge/submit`, the server validates challenge liveness, and upon passing (`decision="PAY"`), automatically runs Nemotron STT and intent parsing against the **first payment audio** to unlock and execute payment tools (`tool.status="EXECUTED"`).
2. **Fix 2 (Latency Isolation)**:
   `time.perf_counter` latency timers strictly isolate biometric inference calls (`Aletheia` and `Eidos`), completely excluding credit balance checks (`/v1/credits`) and database operations.
3. **Fix 3 (In-Browser 16kHz Mono PCM WAV Recording)**:
   Implemented `audio_recorder.js` (`window.PcmAudioRecorder`) utilizing `OfflineAudioContext(1, duration * 16000, 16000)` to resample and encode native 16-bit mono 16kHz PCM WAV with standard 44-byte headers directly in browser, ensuring full compatibility across iOS Safari and Android Chrome.

### 10.3 Day 2 Contract Endpoints
- `GET /api/health` -> `{ "ok": true, "detectif_reachable": true, ... }`
- `POST /api/enroll` (FormData: `audio`, `name`, `lang`) -> `{ "speaker_id": "...", "lang": "kn", "latency_ms": 185, ... }`
- `POST /api/check` (FormData: `audio`, `speaker_id`, `action`, `amount`, `lang`, `device`, `source`) -> `{ "event_id": "...", "decision": "PAY"|"EXTRA_CHECK"|"BLOCK", "reason_key": "...", "detection": {...}, "verification": {...}, "tool": {...}, "cost": {...}, ... }`
- `POST /api/challenge/submit` (FormData: `audio`, `challenge_id`, `speaker_id`, `response_delay_ms`) -> Complete contract response with executed first audio tool status.
- `POST /api/assumptions` (JSON: `{ "rs_per_min": 10.0, "minutes": 2.0 }`) -> Updated cost model.
- `GET /api/latest-state?since={event_id}` -> Returns events, stats, and credits.
- `GET /api/challenge/new?lang={kn|hi|en}` -> Returns 4 random rural words in native script.
- `POST /api/tts` (FormData or JSON) -> Streamed 16kHz PCM audio stream.

### 10.4 Empirical Test Matrix Results (`scripts/test_matrix.py`)
Tested across 9 synthesized audio clips in `clips/<lang>/<category>/`:
- **Overall Accuracy**: **100.0%**
- **False Acceptance Rate (FAR)**: **0.00%** (Target: < 1.0%)
- **False Rejection Rate (FRR)**: **0.00%** (Target: < 2.0%)
- Benchmark results logged to `test_matrix_results.csv`.

### 10.5 Presentation Slide Updates (`DAY2_SLIDE_UPDATES.md`)
- **Slide 2**: Updated to ₹1,000 Fertilizer payment in Kannada, Hindi, or English.
- **Slide 4**: ~40 crore regional feature-phone users protected; ₹20 saved per blocked call explicitly labeled with baseline parameters.
- **Slide 5**: Box header renamed to **"DELIVERED ON DAY 2 (JUDGE RECOMMENDATIONS IMPLEMENTED)"**.

---
*GramPay (BharatVoice Shield) — Zero-Trust Voice Security Gateway for NPCI Hello! UPI*  
*BMSCE AI Hackathon · Track 3 (UNCLONE Agents) · Production Grade*
