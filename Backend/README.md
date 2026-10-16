# UnClone Gate 🛡️🎙️
> **Zero-Trust Voice Biometric & Agent Security Gateway for BFSI**  
> *Track 3: UNCLONE Agents — DetectifAI Hackathon*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![DetectifAI](https://img.shields.io/badge/DetectifAI-Aletheia%20%2B%20Eidos-6366F1?style=flat)](https://platform.detectif.ai)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron--70B-76B900?style=flat&logo=nvidia&logoColor=white)](https://build.nvidia.com)
[![Zero-Trust](https://img.shields.io/badge/Policy-Fail--Closed%20Deterministic-DC2626?style=flat)](https://github.com)
[![Tests](https://img.shields.io/badge/Unit%20Tests-13%20Passing-brightgreen?style=flat)](tests/test_contract.py)

---

## 📑 Table of Contents
1. [Project Overview](#-project-overview)
2. [Track 3: Problem & Solution](#-track-3-problem--solution)
3. [System Architecture & Diagrams](#-system-architecture--diagrams)
   - [High-Level Processing Pipeline](#1-high-level-processing-pipeline)
   - [DetectifAI 2x2 Decision Matrix](#2-detectifai-2x2-decision-matrix)
   - [Agent-to-Agent (A2A) Handshake Lifecycle](#3-agent-to-agent-a2a-cryptographic-handshake)
4. [Quickstart Instructions (Python 3.12)](#-quickstart-instructions-python-312)
5. [Environment Variable Reference](#-environment-variable-reference)
6. [API Contract Specifications](#-api-contract-specifications)
7. [Testing Instructions](#-testing-instructions)
8. [Day 2 Roadmap](#-day-2-roadmap)

---

## 🌟 Project Overview

**UnClone Gate** is an enterprise-grade voice security and operational cost-optimization gateway tailored for Banking, Financial Services, and Insurance (BFSI) institutions. It safeguards conversational AI pipelines, contact centers, and autonomous voice agents from generative AI voice cloning, deepfake fraud, and unauthorized agent impersonation.

### Core Capabilities:
- **Dual-Gate Voice Biometrics**: Couples **DetectifAI Aletheia** (audio vocoder/deepfake detection) and **DetectifAI Eidos** (speaker voiceprint verification) into a deterministic 2x2 decision policy.
- **Fail-Closed Deterministic Security**: Security policy evaluation is executed **strictly in deterministic Python code**. Large Language Models (LLMs) **NEVER** decide whether an action is allowed or blocked.
- **Agent Compute Short-Circuiting**: Audio is gated *before* invoking costly LLM inference (NVIDIA Nemotron-70B) or speech synthesis. Catching malicious clones early saves **~₹10–20 per call** and preserves GPU bandwidth.
- **Cryptographic A2A Handshake**: Prevents rogue bot injection and replay attacks across autonomous agent workflows via single-use, scoped, expiring JWT credentials registered in SQLite.
- **Auditable & Compliant**: Every gate event, decision reason, latency metric, and cost saving is persisted into an immutable audit ledger compliant with RBI Model Risk Guidelines and DPDP (Digital Personal Data Protection) norms.

---

## 🎯 Track 3: Problem & Solution

### The BFSI Voice Security Crisis
1. **Generative Voice Clones**: Modern zero-shot voice cloning models (e.g., ElevenLabs, XTTS, VALL-E) require as little as 3 seconds of reference audio to synthesize a victim's voice with pitch-perfect acoustic fidelity. Vulnerable seniors are actively targeted by fraud syndicates impersonating relatives or account holders to authorize high-value fund transfers (IMPS/NEFT/RTGS).
2. **The Fatal Flaw of Traditional Biometrics**: Conventional voice authentication only asks: *"Does this audio sound like Sita Ramachandran?"* A cloned voice will match the enrolled voiceprint with an extremely high similarity score (e.g., > 0.90). **Without neural vocoder artifact detection, traditional voice biometrics fail completely against AI clones.**
3. **Runaway IVR Compute Drain**: Malicious actors and automated robocallers burn IVR agent lines. Running 3–5 minutes of LLM inference and TTS responses on fraudulent sessions wastes expensive GPU capacity and inflates operational expenditure.
4. **Agent-to-Agent Trust Deficit**: As BFSI workflows increasingly deploy multi-agent orchestration, rogue autonomous bots can spoof customer identities or peer agents without cryptographic proof of intent.

### The UnClone Gate Solution
| Vulnerability / Challenge | Traditional Approach | UnClone Gate Approach |
| :--- | :--- | :--- |
| **Voice Clone Attack** | Voice match passes; fraud succeeds | Parallel Aletheia + Eidos check detects high speaker match + synthetic vocoder $\rightarrow$ **`BLOCK_ALERT`**, funds frozen, branch notified. |
| **Security Decision Authority** | Non-deterministic LLM prompt judgment | **100% Deterministic Code (Lexis Engine)**; LLM has zero policy veto authority. |
| **Inference Cost Overhead** | LLM runs throughout entire call | **Pre-Gate Short-Circuit**: Deepfake detected $\rightarrow$ call dropped before LLM/TTS $\rightarrow$ ₹20 saved per blocked call. |
| **Agent Impersonation** | Static API keys or no A2A validation | **Single-Use Scoped JWT Handshake**: Prevents replay attacks via persistent JTI tracking in SQLite. |
| **System Outage / Latency** | Fails open or produces random errors | **Deterministic Fail-Closed**: Any timeout or upstream failure immediately locks tools and halts sensitive transactions. |

---

## 🏛️ System Architecture & Diagrams

### 1. High-Level Processing Pipeline

```
 Caller / Audio Stream (.wav / .mp3 / .ogg)
                   │
                   ▼
       ┌──────────────────────┐
       │   FastAPI Gateway    │
       │  (CORS, Audio Prep)  │
       └──────────┬───────────┘
                  │
        Parallel Non-Blocking
         ThreadPool Execution
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│  DetectifAI   │   │  DetectifAI   │
│   Aletheia    │   │     Eidos     │
│ (Deepfake /   │   │   (Speaker    │
│  Synthetic)   │   │ Verification) │
└───────┬───────┘   └───────┬───────┘
        │                   │
        └─────────┬─────────┘
                  ▼
  ┌───────────────────────────────┐
  │   Deterministic 2x2 Gate      │
  │     (Lexis Policy Engine)     │
  └───────────────┬───────────────┘
                  │
        ┌─────────┴─────────┐
        │ Decision Outcome  │
        └─────────┬─────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
      ▼                       ▼
┌───────────────┐       ┌────────────────────────┐
│ BLOCK / ALERT │       │       APPROVE          │
├───────────────┤       ├────────────────────────┤
│ • Tool Locked │       │ • Tool Unlocked        │
│ • No LLM Run  │       │ • NVIDIA Nemotron-70B  │
│ • Save ₹20/call│      │   Extracts Intent      │
│ • Alert Fraud │       │ • Execute Bank Tool    │
└───────┬───────┘       └───────────┬────────────┘
        │                           │
        └─────────────┬─────────────┘
                      ▼
         ┌─────────────────────────┐
         │  SQLite Audit Ledger    │
         │  & Telemetry Analytics  │
         └─────────────────────────┘
```

---

### 2. DetectifAI 2x2 Decision Matrix

```
                      SPEAKER MATCH (Eidos Verification)
                      MATCH_HIGH >= 0.85          MATCH_LOW < 0.85
                 ┌──────────────────────────┬──────────────────────────┐
                 │                          │                          │
SYNTHETIC        │      CASE 2: CLONE       │      CASE 4: SPOOF       │
VOCODER          │       BLOCK_ALERT        │          BLOCK           │
(Aletheia)       │                          │                          │
                 │ • High match + Synthetic │ • Low match + Synthetic  │
SYNTH_HIGH       │ • Tool: HARD-LOCKED      │ • Tool: HARD-LOCKED      │
>= 0.50          │ • Short-circuit: Saved ₹ │ • Call terminated        │
                 │ • Bank Fraud Alert       │                          │
                 ├──────────────────────────┼──────────────────────────┤
                 │                          │                          │
NATURAL          │     CASE 1: AUTHENTIC    │     CASE 3: WRONG SPK    │
HUMAN            │         APPROVE          │         STEP_UP          │
VOICE            │                          │                          │
                 │ • Natural + Enrolled     │ • Natural + Wrong User   │
SYNTH_LOW        │ • Tool: UNLOCKED         │ • Tool: LOCKED           │
< 0.20           │ • Nemotron LLM Invoked   │ • Request 4-digit PIN    │
                 │ • Transfer executed      │   or in-branch 2FA       │
                 └──────────────────────────┴──────────────────────────┘

* Borderline synthetic scores (0.20 <= Synth < 0.50) -> STEP_UP
* Upstream API Errors / Timeouts -> Deterministic FAIL-CLOSED (BLOCK/STEP_UP)
```

---

### 3. Agent-to-Agent (A2A) Cryptographic Handshake

```
Requesting Agent                          UnClone Trust Registry (/api)
       │                                                 │
       │─── 1. POST /api/credential/issue ──────────────>│
       │       {agent_id, org, actions, limit_inr}       │── Generate HMAC-SHA256 JWT
       │                                                 │   with unique JTI & exp
       │<── 2. Signed Expiring Credential ───────────────│
       │                                                 │
       │─── 3. POST /api/handshake/verify ──────────────>│
       │       {credential: "<JWT_TOKEN>"}               │
       │                                                 ├── Check 1: Cryptographic Signature
       │                                                 ├── Check 2: Expiration Window (< 300s)
       │                                                 ├── Check 3: SQLite JTI Replay Check
       │                                                 │            (First use -> Insert)
       │                                                 │            (Replay -> Duplicate key!)
       │                                                 └── Check 4: Scope Authorization
       │                                                 │
       │<── 4. VERIFIED_AGENT Badge or REJECTED ─────────│
```

---

## 🚀 Quickstart Instructions (Python 3.12)

### Prerequisites
- **Python 3.12+** (tested and validated on Python 3.12.x 64-bit).
- **FFmpeg** *(Optional, recommended for automated non-WAV browser audio transcoding)*.

### 1. Clone & Navigate to Backend
```powershell
cd c:\Users\chandan.s\OneDrive\Desktop\Unclone\Backend
```

### 2. Set Up Python Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# (Alternative Command Prompt)
# .\venv\Scripts\activate.bat
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and verify the credentials:
```powershell
Copy-Item .env.example .env
```
Ensure your `DETECTIF_API_KEY` and `NVIDIA_API_KEY` are configured in `.env`.

### 5. Launch the FastAPI REST Server
```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check Endpoint**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## ⚙️ Environment Variable Reference

All configuration variables are defined and validated in [`backend/config.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/config.py):

| Variable | Default Value | Type | Description |
| :--- | :--- | :--- | :--- |
| `DETECTIF_API_KEY` | *None* | `str` | API key from [platform.detectif.ai](https://platform.detectif.ai). Required for live deepfake detection and speaker verification. |
| `DETECTIF_BASE_URL` | `https://api.detectif.ai/v1` | `str` | DetectifAI platform base URL. |
| `DETECTIF_TIMEOUT_SECONDS` | `5.0` | `float` | Maximum timeout before gate safely short-circuits to fail-closed state. |
| `NVIDIA_API_KEY` | *None* | `str` | API key from [build.nvidia.com](https://build.nvidia.com) for Nemotron inference. |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | `str` | NVIDIA NIM endpoint URL. |
| `NEMOTRON_MODEL` | `nvidia/llama-3.1-nemotron-70b-instruct` | `str` | Nemotron model identifier for senior banking dialogue and intent extraction. |
| `JWT_SECRET` | `unclone_secret_key_...` | `str` | Cryptographic secret for signing agent credentials. |
| `JWT_ALGORITHM` | `HS256` | `str` | HMAC signing algorithm used for A2A tokens. |
| `CREDENTIAL_VALIDITY_SECONDS` | `300` | `int` | Credential lifetime (5 minutes default) before automatic expiry. |
| `ALLOWED_ORIGIN` | `*` | `str` | CORS allowed origin (allows Grok frontend integration). |
| `ASSUMED_COST_PER_MIN_INR` | `10.0` | `float` | BFSI telephony + LLM compute cost estimate (₹10.00/min). |
| `EST_CALL_SECONDS_SAVED_PER_BLOCK` | `120.0` | `float` | Estimated call duration saved per blocked clone attack (120 seconds). |
| `MATCH_HIGH` | `0.85` | `float` | Minimum Eidos match score threshold to confirm enrolled user identity. |
| `SYNTH_HIGH` | `0.50` | `float` | Minimum Aletheia synthetic score threshold indicating an AI clone. |
| `SYNTH_LOW` | `0.20` | `float` | Maximum Aletheia synthetic score threshold for confirmed natural human voice. |
| `SQLITE_DB_PATH` | `data/audit.db` | `Path` | Persistent SQLite database for audit records and single-use JTI tokens. |

---

## 📡 API Contract Specifications

All endpoints return a tracking header containing `request_id` (`req_<hex>`) and ISO-8601 UTC timestamp `ts`.

| Method | Endpoint | Description | Input Payload | Response Highlights |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Live service reachability check | *None* | `{"ok": true, "detectif_reachable": bool, "nemotron_configured": bool}` |
| `POST` | `/api/enroll` | Enroll voiceprint into DetectifAI Eidos | `multipart/form-data`: `audio` (file), `name` (str) | `{"speaker_id": "spk_...", "name": str, "detectif_raw": {...}}` |
| `POST` | `/api/check` | Parallel 2x2 audio biometric evaluation | `multipart/form-data`: `audio` (file), `speaker_id` (str), `action` (str), `amount` (float) | `{"decision": "APPROVE"\|"BLOCK_ALERT"\|"STEP_UP", "tool": {...}, "cost": {...}}` |
| `POST` | `/api/agent/turn` | Voice agent turn with pre-gate & Nemotron | `multipart/form-data`: `audio` (file), `speaker_id` (str), `user_text_hint` (str, opt) | `{"decision": str, "transcript": str, "agent_reply_text": str, "tool": {...}}` |
| `POST` | `/api/credential/issue` | Mint single-use scoped JWT token | `application/json`: `agent_id`, `org`, `allowed_actions`, `limit_inr` | `{"credential": "<JWT>", "jti": "<UUID>", "expires_in_seconds": 300}` |
| `POST` | `/api/handshake/verify` | Verify token & prevent replay attacks | `application/json`: `credential` | `{"badge": "VERIFIED_AGENT"\|"REJECTED", "checks": {signature, expiry, unused, scope}}` |
| `GET` | `/api/audit` | Query immutable audit log records | Query param: `limit` (int, default 50) | `{"count": int, "logs": [...]}` |
| `GET` | `/api/stats` | Telemetry & cost savings analytics | *None* | `{"total_checks": int, "total_blocked": int, "est_cost_savings_inr": float}` |

### Detailed Endpoint Payloads

#### 1. `POST /api/check`
**Request (Multipart Form):**
- `audio`: Binary WAV file (16kHz PCM recommended)
- `speaker_id`: `"senior_user_01"`
- `action`: `"TRANSFER_FUNDS"`
- `amount`: `45000.0`

**Response (Clone Attack Detected — Block & Lock):**
```json
{
  "request_id": "req_a1b2c3d4e5f6",
  "ts": "2026-10-16T13:25:00.000000+00:00",
  "decision": "BLOCK_ALERT",
  "reason": "CRITICAL WARNING: Computer-generated voice clone detected! Although the voice sounds like the account holder, neural synthesis was identified. All transfers have been frozen and the bank fraud team has been alerted.",
  "detection": {
    "is_synthetic": true,
    "synthetic_score": 0.8921,
    "latency_ms": 380
  },
  "verification": {
    "matched": true,
    "match_score": 0.9412,
    "latency_ms": 410
  },
  "tool": {
    "name": "transfer_funds",
    "status": "LOCKED",
    "result": null,
    "message": "High-risk transfer is LOCKED by UnClone Gate until voice liveness and identity pass."
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

#### 2. `POST /api/handshake/verify` (Replay Attack Scenario)
**Request (JSON):**
```json
{
  "credential": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (First Call - Success):**
```json
{
  "request_id": "req_789abc012def",
  "ts": "2026-10-16T13:25:05.000000+00:00",
  "badge": "VERIFIED_AGENT",
  "reason": "Cryptographically verified agent from ICICI Bank Voice Ops (agent_icici_voice_01). Safe to interact.",
  "agent_id": "agent_icici_voice_01",
  "org": "ICICI Bank Voice Ops",
  "limit_inr": 50000.0,
  "checks": {
    "signature": true,
    "expiry": true,
    "unused": true,
    "scope": true
  }
}
```

**Response (Replayed Token — Instantly Rejected):**
```json
{
  "request_id": "req_fedcba987654",
  "ts": "2026-10-16T13:25:06.000000+00:00",
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

## 🧪 Testing Instructions

The repository includes a comprehensive, automated test suite covering all contract endpoints, 2x2 matrix logic, fail-closed handling, replay prevention, and banking tools.

### 1. Run Automated Unit Tests
Execute the test suite with Python 3.12:
```powershell
# Using Python 3.12 interpreter
python -m unittest tests/test_contract.py
```
*Expected Result:*
```text
.............
----------------------------------------------------------------------
Ran 13 tests in 0.098s

OK
```

### 2. Generate Synthetic Test Audio Files
To generate test audio samples (`sample_human.wav` and `sample_clone.wav`):
```powershell
python tests/generate_sample_audio.py
```

### 3. Live Endpoint Verification via PowerShell
With the server running on port 8000:

**Check Health:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method GET | ConvertTo-Json
```

**Mint & Verify Agent Credential:**
```powershell
# 1. Mint Credential
$issue = Invoke-RestMethod -Uri "http://localhost:8000/api/credential/issue" `
  -Method POST -ContentType "application/json" `
  -Body '{"agent_id":"bot_hdfc_01","org":"HDFC NetBanking Voice","allowed_actions":["TRANSFER_FUNDS"]}'

# 2. Verify Handshake
Invoke-RestMethod -Uri "http://localhost:8000/api/handshake/verify" `
  -Method POST -ContentType "application/json" `
  -Body (@{ credential = $issue.credential } | ConvertTo-Json) | ConvertTo-Json
```

**Query Telemetry & Cost Savings:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/stats" -Method GET | ConvertTo-Json
```

---

## 🔮 Day 2 Roadmap

Future architectural enhancements for production BFSI enterprise deployments:

1. **Sub-100ms In-Memory Pre-Gating (Redis Cluster)**:
   - Cache recent speaker embeddings and trust score tokens in a distributed Redis cluster to evaluate recurrent conversational turns in under 80 milliseconds.
2. **Streaming WebSocket Audio Verification**:
   - Provide real-time chunked audio streaming over WebSockets/gRPC (`/ws/audio/gate`), analyzing voice authenticity mid-sentence and cutting call audio before sensitive financial tools can even be rendered.
3. **Hardware Security Module (HSM) Cryptography**:
   - Upgrade agent JWT issuance to asymmetric ED25519 signing keys backed by an AWS CloudHSM or Azure Key Vault, meeting RBI guidelines for high-value banking infrastructure.
4. **Decentralized Agent Identity (W3C DID / Verifiable Credentials)**:
   - Replace symmetric tokens with standard W3C DID-based Verifiable Credentials enabling cross-bank voice agent federation without shared secrets.
5. **Pan-India Multilingual Biometric Tuning**:
   - Calibrate Aletheia and Eidos acceptance thresholds across 12 major Indian languages and regional dialects (Hindi, Tamil, Telugu, Kannada, Bengali, Marathi, Gujarati) to eliminate dialectic bias.
6. **Enterprise SIEM & FMS Dispatch**:
   - Real-time webhook emission of `BLOCK_ALERT` incidents directly into bank Fraud Management Systems (FMS), Splunk, and Datadog with automated freeze on netbanking credentials.

---

<p align="center">
  <b>UnClone Gate</b> — Securing Autonomous Voice Agents & Protecting Senior Citizens in Banking.<br>
  <i>Built with ❤️ for Track 3: UNCLONE Agents.</i>
</p>
