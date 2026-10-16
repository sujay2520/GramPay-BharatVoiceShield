# UnClone Gate: Frontend Integration Specification
> **For Frontend Developers & Grok**  
> **Target Gateway:** `http://localhost:8000` (FastAPI REST Backend)  
> **Track:** Track 3 (UNCLONE Agents - Zero-Trust Voice Security & Cost Gateway)  
> **Key Technologies:** DetectifAI (Aletheia & Eidos) + NVIDIA Nemotron-3.5 + Single-Use JWT Handshake + SQLite Audit

---

## 1. System Overview & Architecture

UnClone Gate is a high-assurance, zero-trust security and cost-optimization gateway for BFSI (Banking, Financial Services, and Insurance) voice agents. It sits between incoming customer voice streams and downstream Large Language Models (LLMs) or Core Banking tools.

### Architecture Data Flow
```
[User Mic / Audio Blob]
         │
         ▼
[Frontend: Senior UI / Judge Console]
         │  multipart/form-data
         ▼
[FastAPI Gateway: http://localhost:8000]
         │
         ├───► 1. Pre-Gate: Parallel DetectifAI Evaluation
         │        ├── Aletheia Engine (Deepfake / Synthetic Vocoder Detection)
         │        └── Eidos Engine (Biometric Speaker Voiceprint Match)
         │
         ├───► 2. Deterministic 2x2 Policy Gate (gate.py)
         │        ├── APPROVE     ──► Unlocks Tool + Invokes NVIDIA Nemotron (₹ saved: 0)
         │        ├── BLOCK_ALERT ──► HARD-LOCK Tool + Short-circuit LLM (Saves ₹10-20/call)
         │        ├── STEP_UP     ──► HARD-LOCK Tool + Ask Senior for 4-digit PIN
         │        └── BLOCK       ──► HARD-LOCK Tool + Terminate Call
         │
         ├───► 3. Cryptographic Handshake Registry (credentials.py)
         │        └── Single-Use JWT Replay Protection
         │
         └───► 4. Immutable SQLite Audit Table & INR Telemetry (audit.py)
```

### The Two Frontend Consoles
1. **Senior Citizen Voice Banking UI**:
   - Designed for elderly users with large typography (>= 20px), ultra-high contrast, oversized touch targets (>= 64px), and reassuring plain-language voice feedback.
   - **Zero-Jargon Guarantee**: Never show terms like "synthetic vocoder", "Aletheia", "JWT", or "cosine similarity".
   - Shows clear status cards: **Green** (Safe & Verified), **Amber** (PIN Required), or **Red** (Call Protected & Frozen).

2. **Judge & Compliance Telemetry Console**:
   - Designed for hackathon judges, fraud analysts, and security auditors.
   - Shows real-time 2x2 decision scatter plot (`synthetic_score` vs `match_score`).
   - Displays live latency metrics, audit stream, tool execution states, and an **accumulated INR cost savings counter** calculated from short-circuited LLM calls.
   - Provides an interactive Agent Handshake & Replay Simulator.

---

## 2. Global Configuration & Client Utilities

### Base URL Configuration
Create an environment file or config constant in your frontend:
```javascript
// config.js or .env
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 
                            process.env.VITE_API_BASE_URL || 
                            "http://localhost:8000";
```

### Audio Recording Helper (Browser MediaRecorder)
Modern browsers record WebM or OGG audio. The UnClone backend automatically accepts WAV, WebM, MP3, OGG, or MP4, converting via `ffmpeg` if needed. However, sending standard WAV or WebM blobs via `FormData` works out-of-the-box:

```javascript
/**
 * Records user audio from microphone for `durationMs` milliseconds.
 * Returns a Promise resolving to a Blob.
 */
export async function recordMicrophoneAudio(durationMs = 3000) {
  const stream = await navigator.mediaDevices.getUserMedia({ 
    audio: {
      channelCount: 1,
      sampleRate: 16000,
      echoCancellation: true,
      noiseSuppression: true
    } 
  });
  
  return new Promise((resolve, reject) => {
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") 
      ? "audio/webm;codecs=opus" 
      : "audio/webm";
    
    const mediaRecorder = new MediaRecorder(stream, { mimeType });
    const chunks = [];

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    };

    mediaRecorder.onstop = () => {
      // Stop all tracks to release hardware microphone
      stream.getTracks().forEach(track => track.stop());
      const audioBlob = new Blob(chunks, { type: mimeType });
      resolve(audioBlob);
    };

    mediaRecorder.onerror = (err) => {
      stream.getTracks().forEach(track => track.stop());
      reject(err);
    };

    mediaRecorder.start();
    setTimeout(() => {
      if (mediaRecorder.state === "recording") {
        mediaRecorder.stop();
      }
    }, durationMs);
  });
}
```

> **CRITICAL FETCH RULE FOR FORMDATA:**  
> When sending `FormData` via `fetch()`, **DO NOT** explicitly set `'Content-Type': 'multipart/form-data'` in headers. The browser must automatically inject the `multipart/form-data; boundary=----WebKitFormBoundary...` header.

---

## 3. Complete Endpoint Reference & Code Snippets

### Summary Matrix
| Endpoint | Method | Content-Type | Primary Use Case |
| :--- | :--- | :--- | :--- |
| `/api/health` | `GET` | `application/json` | System readiness & DetectifAI ping |
| `/api/enroll` | `POST` | `multipart/form-data` | Enroll customer's baseline voiceprint |
| `/api/check` | `POST` | `multipart/form-data` | Fast dual-gate check & mock tool execution |
| `/api/agent/turn` | `POST` | `multipart/form-data` | Full voice turn: Gate -> Nemotron -> Tool |
| `/api/credential/issue` | `POST` | `application/json` | Issue single-use signed agent JWT |
| `/api/handshake/verify` | `POST` | `application/json` | Verify agent handshake & prevent replay |
| `/api/audit` | `GET` | `application/json` | Fetch recent immutable audit logs |
| `/api/stats` | `GET` | `application/json` | Real-time security counts & INR savings |

---

### 3.1. Health & Reachability (`GET /api/health`)
Verifies reachability of the DetectifAI platform and configuration of the NVIDIA Nemotron LLM.

#### JavaScript Fetch Snippet
```javascript
export async function checkGatewayHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`, {
      method: "GET",
      headers: { "Accept": "application/json" }
    });
    if (!res.ok) throw new Error(`Health check failed with status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("UnClone Gate Unreachable:", err);
    return { ok: false, detectif_reachable: false, nemotron_configured: false };
  }
}
```

#### Response JSON Shape (200 OK)
```json
{
  "request_id": "req_84ad902e8d91",
  "ts": "2026-10-16T07:54:12.839120+00:00",
  "ok": true,
  "detectif_reachable": true,
  "detectif_details": {
    "reachable": true,
    "status_code": 200,
    "latency_ms": 142
  },
  "nemotron_configured": true
}
```

---

### 3.2. Customer Voice Enrollment (`POST /api/enroll`)
Enrolls a customer's reference voice into the DetectifAI Eidos engine.

#### Request `FormData` Format
- `audio`: File/Blob (WAV, WebM, MP3)
- `name`: String (e.g. `"senior_user_01"` or `"Sita Ramachandran"`)

#### JavaScript Fetch Snippet
```javascript
export async function enrollSpeaker(audioBlob, speakerName = "senior_user_01") {
  const formData = new FormData();
  formData.append("audio", audioBlob, "enrollment.wav");
  formData.append("name", speakerName);

  const response = await fetch(`${API_BASE_URL}/api/enroll`, {
    method: "POST",
    body: formData
    // NOTE: Leave headers empty so browser populates boundary!
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Enrollment failed");
  }
  return data;
}
```

#### Response JSON Shape (200 OK)
```json
{
  "request_id": "req_c34120df01bc",
  "ts": "2026-10-16T07:55:00.102381+00:00",
  "enrolled": true,
  "speaker_id": "senior_user_01",
  "latency_ms": 284,
  "raw": {
    "status": "success",
    "voiceprint_id": "vp_9023184912"
  }
}
```

---

### 3.3. Dual-Gate Security Check (`POST /api/check`)
Performs parallel Deepfake Detection (Aletheia) and Speaker Verification (Eidos), applies the deterministic 2x2 decision gate, locks/unlocks the requested banking tool, and records an immutable audit log.

#### Request `FormData` Format
- `audio`: File/Blob (The voice audio payload)
- `speaker_id`: String (Defaults to `"senior_user_01"`)
- `action`: String (`"TRANSFER_FUNDS"` or `"CHECK_BALANCE"`)
- `amount`: Number (e.g. `45000.0` for transfers)

#### JavaScript Fetch Snippet
```javascript
export async function checkVoiceSecurity({
  audioBlob,
  speakerId = "senior_user_01",
  action = "TRANSFER_FUNDS",
  amount = 45000.0
}) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "voice_check.wav");
  formData.append("speaker_id", speakerId);
  formData.append("action", action);
  formData.append("amount", String(amount));

  const response = await fetch(`${API_BASE_URL}/api/check`, {
    method: "POST",
    body: formData
  });

  const data = await response.json();
  if (!response.ok) {
    // Fail-closed handling
    return {
      decision: "BLOCK",
      reason: data.error || "Gateway connection error. Transaction held safely.",
      tool: { status: "LOCKED" },
      fail_closed: true
    };
  }

  return data;
}
```

#### Response JSON Shape (200 OK - Approved Transfer Example)
```json
{
  "request_id": "req_a983bca9810f",
  "ts": "2026-10-16T07:56:10.512903+00:00",
  "decision": "APPROVE",
  "reason": "Verified Safe: Natural human voice and account holder identity confirmed.",
  "detection": {
    "is_synthetic": false,
    "synthetic_score": 0.04,
    "latency_ms": 110,
    "raw": { "model": "aletheia-v2" }
  },
  "verification": {
    "matched": true,
    "match_score": 0.94,
    "latency_ms": 135,
    "raw": { "cosine_distance": 0.06 }
  },
  "tool": {
    "name": "transfer_funds",
    "status": "EXECUTED",
    "result": {
      "transaction_id": "TXN-UNCLONE-45000-PASS",
      "from_account": "SB-8920194821",
      "recipient": "Rahul Sharma (Grandson)",
      "amount_inr": 45000.0,
      "remaining_balance_inr": 200000.0
    },
    "message": "Successfully transferred ₹45,000.00 to Rahul Sharma (Grandson)."
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

#### Response JSON Shape (200 OK - Voice Clone Attack Caught Example)
```json
{
  "request_id": "req_ff01239845da",
  "ts": "2026-10-16T07:56:45.192834+00:00",
  "decision": "BLOCK_ALERT",
  "reason": "CRITICAL WARNING: Computer-generated voice clone detected! Although the voice sounds like the account holder, neural synthesis was identified. All transfers have been frozen and the bank fraud team has been alerted.",
  "detection": {
    "is_synthetic": true,
    "synthetic_score": 0.96,
    "latency_ms": 115,
    "raw": { "vocoder_artifacts": true }
  },
  "verification": {
    "matched": true,
    "match_score": 0.91,
    "latency_ms": 130,
    "raw": { "speaker_match": true }
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
  "audit_id": 43
}
```

---

### 3.4. Full Voice Agent Turn (`POST /api/agent/turn`)
The complete Track 3 voice turn endpoint. DetectifAI pre-gates the turn before invoking NVIDIA Nemotron. If blocked, it immediately short-circuits to avoid LLM token consumption and TTS costs.

#### Request `FormData` Format
- `audio`: File/Blob (Audio command from customer)
- `speaker_id`: String (e.g. `"senior_user_01"`)
- `user_text_hint`: Optional String (Simulated ASR transcript if testing without audio speech-to-text)

#### JavaScript Fetch Snippet
```javascript
export async function executeAgentTurn({
  audioBlob,
  speakerId = "senior_user_01",
  userTextHint = "Transfer forty-five thousand rupees to Rahul."
}) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "turn.wav");
  formData.append("speaker_id", speakerId);
  if (userTextHint) {
    formData.append("user_text_hint", userTextHint);
  }

  const response = await fetch(`${API_BASE_URL}/api/agent/turn`, {
    method: "POST",
    body: formData
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Turn execution failed");
  }

  return data;
}
```

#### Response JSON Shape (200 OK)
```json
{
  "request_id": "req_45b91a27e90c",
  "ts": "2026-10-16T07:58:20.120934+00:00",
  "decision": "APPROVE",
  "reason": "Verified Safe: Natural human voice and account holder identity confirmed.",
  "detection": {
    "is_synthetic": false,
    "synthetic_score": 0.03,
    "latency_ms": 112
  },
  "verification": {
    "matched": true,
    "match_score": 0.95,
    "latency_ms": 138
  },
  "tool": {
    "name": "transfer_funds",
    "status": "EXECUTED",
    "result": {
      "transaction_id": "TXN-UNCLONE-45000-PASS",
      "from_account": "SB-8920194821",
      "recipient": "Rahul Sharma (Grandson)",
      "amount_inr": 45000.0,
      "remaining_balance_inr": 155000.0
    },
    "message": "Successfully transferred ₹45,000.00 to Rahul Sharma (Grandson)."
  },
  "cost": {
    "agent_steps_skipped": 0,
    "agent_seconds_avoided": 0.0,
    "est_inr": 0.0,
    "assumption": "Rs 10.00 per min (editable)"
  },
  "transcript": "Transfer forty-five thousand rupees to Rahul.",
  "agent_reply_text": "Namaste Sita-ji. Your voice identity is verified. I have safely transferred ₹45,000 to Rahul.",
  "intent": "TRANSFER_FUNDS",
  "audit_id": 44
}
```

---

### 3.5. Issue Agent Credential (`POST /api/credential/issue`)
Issues a cryptographically signed, single-use, scoped JWT credential for inter-agent banking operations.

#### Request JSON Body
```json
{
  "agent_id": "icici_voice_agent_04",
  "org": "ICICI Senior Citizen Care",
  "allowed_actions": ["TRANSFER_FUNDS", "CHECK_BALANCE"],
  "limit_inr": 50000.0
}
```

#### JavaScript Fetch Snippet
```javascript
export async function issueAgentCredential({
  agentId = "icici_voice_agent_04",
  org = "ICICI Senior Citizen Care",
  allowedActions = ["TRANSFER_FUNDS", "CHECK_BALANCE"],
  limitInr = 50000.0
}) {
  const response = await fetch(`${API_BASE_URL}/api/credential/issue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      agent_id: agentId,
      org: org,
      allowed_actions: allowedActions,
      limit_inr: limitInr
    })
  });

  return await response.json();
}
```

#### Response JSON Shape (200 OK)
```json
{
  "request_id": "req_318df920bc71",
  "ts": "2026-10-16T08:00:10.091240+00:00",
  "credential": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "agent_id": "icici_voice_agent_04",
  "org": "ICICI Senior Citizen Care",
  "jti": "5a22d733-4f93-4a1d-b6eb-bb1e0892f021",
  "expires_in_seconds": 300,
  "allowed_actions": ["TRANSFER_FUNDS", "CHECK_BALANCE"],
  "limit_inr": 50000.0
}
```

---

### 3.6. Verify Agent Handshake & Replay Check (`POST /api/handshake/verify`)
Verifies cryptographic signature, expiry, authorized scope, and single-use status (replay attack prevention).

#### Request JSON Body
```json
{
  "credential": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### JavaScript Fetch Snippet
```javascript
export async function verifyAgentHandshake(credentialJwt) {
  const response = await fetch(`${API_BASE_URL}/api/handshake/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential: credentialJwt })
  });

  return await response.json();
}
```

#### Response JSON Shape (200 OK - Successful Verification)
```json
{
  "request_id": "req_8812af092bc1",
  "ts": "2026-10-16T08:01:00.540129+00:00",
  "badge": "VERIFIED_AGENT",
  "reason": "Cryptographically verified agent from ICICI Senior Citizen Care (icici_voice_agent_04). Safe to interact.",
  "agent_id": "icici_voice_agent_04",
  "org": "ICICI Senior Citizen Care",
  "limit_inr": 50000.0,
  "checks": {
    "signature": true,
    "expiry": true,
    "unused": true,
    "scope": true
  }
}
```

#### Response JSON Shape (200 OK - Replay Attack Prevented)
```json
{
  "request_id": "req_9921bc8201fa",
  "ts": "2026-10-16T08:01:05.109240+00:00",
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

### 3.7. Audit Log Telemetry (`GET /api/audit?limit=50`)
Returns the latest verified audit records for display in the Judge Telemetry Console.

#### JavaScript Fetch Snippet
```javascript
export async function fetchAuditLogs(limit = 50) {
  const response = await fetch(`${API_BASE_URL}/api/audit?limit=${limit}`, {
    method: "GET",
    headers: { "Accept": "application/json" }
  });
  return await response.json();
}
```

#### Response JSON Shape (200 OK)
```json
{
  "request_id": "req_ee910248ab12",
  "ts": "2026-10-16T08:02:15.192019+00:00",
  "count": 2,
  "logs": [
    {
      "id": 43,
      "request_id": "req_ff01239845da",
      "ts": "2026-10-16T07:56:45.192834+00:00",
      "speaker_id": "senior_user_01",
      "action": "TRANSFER_FUNDS",
      "decision": "BLOCK_ALERT",
      "reason": "CRITICAL WARNING: Computer-generated voice clone detected!...",
      "synthetic_score": 0.96,
      "match_score": 0.91,
      "is_synthetic": 1,
      "matched": 1,
      "latency_ms": 245,
      "tool_status": "LOCKED",
      "steps_skipped": 1,
      "seconds_avoided": 120.0,
      "est_inr": 20.0
    },
    {
      "id": 42,
      "request_id": "req_a983bca9810f",
      "ts": "2026-10-16T07:56:10.512903+00:00",
      "speaker_id": "senior_user_01",
      "action": "TRANSFER_FUNDS",
      "decision": "APPROVE",
      "reason": "Verified Safe: Natural human voice and account holder identity confirmed.",
      "synthetic_score": 0.04,
      "match_score": 0.94,
      "is_synthetic": 0,
      "matched": 1,
      "latency_ms": 245,
      "tool_status": "EXECUTED",
      "steps_skipped": 0,
      "seconds_avoided": 0.0,
      "est_inr": 0.0
    }
  ]
}
```

---

### 3.8. Telemetry & Cost Savings Analytics (`GET /api/stats`)
Returns aggregate security metrics and estimated financial savings in Indian Rupees (₹).

#### JavaScript Fetch Snippet
```javascript
export async function fetchTelemetryStats() {
  const response = await fetch(`${API_BASE_URL}/api/stats`, {
    method: "GET",
    headers: { "Accept": "application/json" }
  });
  return await response.json();
}
```

#### Response JSON Shape (200 OK)
```json
{
  "request_id": "req_22891fc091a1",
  "ts": "2026-10-16T08:03:00.812903+00:00",
  "total_checks": 142,
  "total_approved": 98,
  "total_blocked": 34,
  "total_step_up": 10,
  "agent_steps_skipped": 44,
  "agent_seconds_avoided": 5280.0,
  "est_cost_savings_inr": 880.0,
  "assumption": "Rs 10.00 per min (editable)"
}
```

---

## 4. Status Badge Mapping & Decision Matrix

### The 2x2 Decision Matrix
| Quadrant | Synthetic Score | Match Score | Decision | Meaning | Tool Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Q1 (Safe)** | `< 0.20` (Human) | `>= 0.85` (Owner) | **`APPROVE`** | Real Enrolled Customer | **`EXECUTED`** |
| **Q2 (Attack)** | `>= 0.50` (Synth) | `>= 0.85` (Owner) | **`BLOCK_ALERT`** | Deepfake Clone Attack | **`LOCKED`** |
| **Q3 (Impostor)**| `>= 0.50` (Synth) | `< 0.85` (Wrong) | **`BLOCK`** | Synthetic Bot Call | **`LOCKED`** |
| **Q4 (Mismatch)**| `< 0.20` (Human) | `< 0.85` (Wrong) | **`STEP_UP`** | Human, but Wrong Speaker| **`LOCKED`** |
| **Borderline** | `0.20 <= S < 0.50` | Any | **`STEP_UP`** | Inconclusive Confidence | **`LOCKED`** |

### Complete Frontend Badge Mapping Table
Use this exact visual mapping across all frontend views:

| Gate Decision | Badge Color | Hex / Tailwind | Icon | Display Text (Senior Citizen UI) | Display Text (Judge Console) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`APPROVE`** | **GREEN** | `#10B981`<br>`bg-emerald-500` | Shield Check `✓` | **"Safe & Verified"**<br>"Your identity is confirmed." | **`APPROVE (SAFE)`**<br>Natural Voice + Enrolled Match |
| **`BLOCK_ALERT`**| **RED** | `#EF4444`<br>`bg-red-500` *(Pulsing)* | Warning Siren `🚨` | **"Account Protected"**<br>"Artificial voice detected. Transfers frozen." | **`BLOCK_ALERT (CLONE ATTACK)`**<br>High Vocoder Synth + High Match |
| **`STEP_UP`** | **AMBER** | `#F59E0B`<br>`bg-amber-500` | Key / PIN `🔑` | **"Verification Needed"**<br>"Please provide your 4-digit PIN." | **`STEP_UP (AUTH REQUIRED)`**<br>Speaker Mismatch or Inconclusive |
| **`BLOCK`** | **DARK RED**| `#DC2626`<br>`bg-rose-700` | Cross / Stop `⛔` | **"Call Ended"**<br>"Unable to confirm caller authenticity." | **`BLOCK (IMPOSTOR)`**<br>Synthetic Vocoder + Unknown Caller |

### JavaScript Badge Styling Helper
```javascript
export function getStatusBadgeConfig(decision) {
  switch (decision) {
    case "APPROVE":
      return {
        label: "Safe & Verified",
        judgeLabel: "APPROVE",
        badgeColor: "bg-emerald-100 text-emerald-800 border-emerald-300",
        icon: "ShieldCheck",
        colorHex: "#10B981",
        seniorHeadline: "Voice Verified Safe",
        seniorSubtext: "Your request is processing safely."
      };
    case "BLOCK_ALERT":
      return {
        label: "Security Alert: Clone Detected",
        judgeLabel: "BLOCK_ALERT",
        badgeColor: "bg-red-100 text-red-800 border-red-500 animate-pulse",
        icon: "AlertOctagon",
        colorHex: "#EF4444",
        seniorHeadline: "Account Frozen for Your Safety",
        seniorSubtext: "Computer-generated voice detected. Bank fraud team notified."
      };
    case "STEP_UP":
      return {
        label: "Secondary Check Needed",
        judgeLabel: "STEP_UP",
        badgeColor: "bg-amber-100 text-amber-800 border-amber-300",
        icon: "KeyRound",
        colorHex: "#F59E0B",
        seniorHeadline: "PIN Verification Required",
        seniorSubtext: "Voice could not be confirmed. Please enter your 4-digit PIN."
      };
    case "BLOCK":
    default:
      return {
        label: "Call Blocked",
        judgeLabel: "BLOCK",
        badgeColor: "bg-rose-100 text-rose-800 border-rose-300",
        icon: "Ban",
        colorHex: "#DC2626",
        seniorHeadline: "Call Safely Disconnected",
        seniorSubtext: "Unrecognized caller authenticity."
      };
  }
}
```

---

## 5. Verified Agent Badge Display Logic

When an agent or service presents a cryptographic credential to `/api/handshake/verify`, render the Trust Badge according to the response:

```
[Agent Handshake Token] ──► /api/handshake/verify
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
  [badge: "VERIFIED_AGENT"]                       [badge: "REJECTED"]
  • Blue/Emerald Glowing Pill                     • Red Warning Border
  • Shield-Checkmark Icon                         • Alert Triangle Icon
  • Org: "ICICI Senior Care"                      • Subtext: "[Reason]"
  • Limit: "₹50,000 / call"                       • Replay Attack Warning
  • 4 Checkmarks:                                 • Failed Check Highlight:
    [✓] Cryptographic Signature                     [✗] Single-Use (Replay!)
    [✓] Expiration Window                           [✗] Expired
    [✓] Single-Use Nonce (Unused)                   [✗] Scope Violation
    [✓] Authorized Action Scope
```

### React Component for Verified Agent Badge
```jsx
import React from 'react';

export function VerifiedAgentBadge({ handshakeResult }) {
  if (!handshakeResult) return null;

  const isVerified = handshakeResult.badge === "VERIFIED_AGENT";
  const checks = handshakeResult.checks || {};

  return (
    <div className={`p-4 rounded-xl border transition-all ${
      isVerified 
        ? "bg-slate-900 border-emerald-500 text-white shadow-lg shadow-emerald-500/10" 
        : "bg-slate-900 border-red-500 text-white shadow-lg shadow-red-500/10"
    }`}>
      {/* Header Pill */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-700">
        <div className="flex items-center space-x-2">
          {isVerified ? (
            <span className="flex h-3 w-3 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
          ) : (
            <span className="inline-block h-3 w-3 rounded-full bg-red-500"></span>
          )}
          <span className="font-bold text-lg">
            {isVerified ? "VERIFIED BANK AGENT" : "AGENT HANDSHAKE REJECTED"}
          </span>
        </div>
        <span className={`px-2.5 py-1 text-xs font-semibold rounded-full uppercase tracking-wider ${
          isVerified ? "bg-emerald-950 text-emerald-400 border border-emerald-800" : "bg-red-950 text-red-400 border border-red-800"
        }`}>
          {handshakeResult.badge}
        </span>
      </div>

      {/* Agent Metadata */}
      {isVerified && (
        <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-slate-300">
          <div><span className="text-slate-500">Organization:</span> <span className="font-semibold text-white">{handshakeResult.org}</span></div>
          <div><span className="text-slate-500">Agent ID:</span> <code className="text-emerald-400">{handshakeResult.agent_id}</code></div>
          <div><span className="text-slate-500">Max Transaction:</span> <span className="font-semibold text-white">₹{handshakeResult.limit_inr?.toLocaleString('en-IN')}</span></div>
          <div><span className="text-slate-500">Protocol:</span> <span className="font-mono text-xs">UnClone Single-Use JWT</span></div>
        </div>
      )}

      {/* Error Message for Rejections */}
      {!isVerified && (
        <div className="mt-3 p-3 bg-red-950/60 border border-red-800/80 rounded-lg text-sm text-red-200">
          <strong>Security Warning:</strong> {handshakeResult.reason}
        </div>
      )}

      {/* 4-Point Cryptographic Checklist */}
      <div className="mt-4 pt-3 border-t border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        <CheckItem label="Signature" passed={checks.signature} />
        <CheckItem label="Timestamp" passed={checks.expiry} />
        <CheckItem label="Single-Use" passed={checks.unused} failLabel="REPLAY" />
        <CheckItem label="Action Scope" passed={checks.scope} />
      </div>
    </div>
  );
}

function CheckItem({ label, passed, failLabel = "FAIL" }) {
  return (
    <div className={`flex items-center space-x-1.5 px-2 py-1.5 rounded ${
      passed ? "bg-emerald-950/40 text-emerald-300 border border-emerald-800/50" : "bg-red-950/40 text-red-300 border border-red-800/50"
    }`}>
      <span>{passed ? "✓" : "✗"}</span>
      <span className="font-medium">{label}:</span>
      <span className="font-bold">{passed ? "PASS" : failLabel}</span>
    </div>
  );
}
```

---

## 6. Senior Citizen Voice Banking UI Guide

### Design Requirements for Senior Accessibility
1. **Minimum Font Sizes**: Body text `>= 20px`, headers `>= 28px`, button labels `>= 24px`.
2. **Color Contrast**: Compliant with WCAG 2.1 AAA (minimum contrast ratio 7:1 against background).
3. **Generous Touch Targets**: Big round mic button (minimum `96px x 96px`).
4. **Reassuring Voice Feedback**: Always read aloud the `agent_reply_text` using the browser's native `window.speechSynthesis`.
5. **Fail-Closed Protection**: In case of server error or timeout, present a calm, reassuring screen: *"Namaste Sita-ji. To protect your money, we have safely paused this transaction. Our manager at Indira Nagar branch has been informed."*

### Senior Voice Dial Component
```jsx
import React, { useState } from 'react';
import { recordMicrophoneAudio } from './audio';
import { executeAgentTurn } from './api';

export function SeniorVoiceBanking() {
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState("IDLE"); // IDLE, RECORDING, CHECKING, RESULT
  const [result, setResult] = useState(null);
  const [pinRequired, setPinRequired] = useState(false);

  const handleStartVoiceCommand = async () => {
    try {
      setIsRecording(true);
      setStatus("RECORDING");
      
      // Record 3.5 seconds of customer voice
      const audioBlob = await recordMicrophoneAudio(3500);
      setIsRecording(false);
      setStatus("CHECKING");

      // Send to UnClone Gate Turn endpoint
      const turnResponse = await executeAgentTurn({
        audioBlob,
        speakerId: "senior_user_01",
        userTextHint: "Transfer forty-five thousand rupees to Rahul."
      });

      setResult(turnResponse);
      setStatus("RESULT");

      // Voice playback for senior accessibility
      if (turnResponse.agent_reply_text && 'speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(turnResponse.agent_reply_text);
        utterance.rate = 0.9; // Speak slightly slower and clearer
        utterance.lang = 'en-IN';
        window.speechSynthesis.speak(utterance);
      }

      if (turnResponse.decision === "STEP_UP") {
        setPinRequired(true);
      }
    } catch (err) {
      console.error(err);
      setStatus("ERROR");
      setResult({
        decision: "BLOCK",
        agent_reply_text: "Namaste. We have paused this transaction safely to protect your funds. Please contact your branch."
      });
    }
  };

  return (
    <div className="max-w-xl mx-auto p-8 bg-amber-50 rounded-3xl border-4 border-amber-200 shadow-2xl text-slate-900 font-sans">
      {/* Account Header */}
      <div className="flex items-center justify-between pb-6 border-b-2 border-amber-200">
        <div>
          <h1 className="text-3xl font-extrabold text-amber-950">Namaste, Sita-ji</h1>
          <p className="text-xl text-amber-800">Account: SB-8920194821</p>
        </div>
        <div className="text-right">
          <span className="text-sm font-semibold uppercase text-amber-700">Available Balance</span>
          <p className="text-2xl font-bold text-emerald-800">₹2,45,000</p>
        </div>
      </div>

      {/* Main Microphone Action Area */}
      <div className="py-10 text-center">
        <button
          onClick={handleStartVoiceCommand}
          disabled={status === "RECORDING" || status === "CHECKING"}
          className={`w-36 h-36 rounded-full mx-auto flex items-center justify-center text-5xl shadow-2xl transition-all transform active:scale-95 ${
            status === "RECORDING"
              ? "bg-red-600 text-white animate-pulse ring-8 ring-red-300"
              : status === "CHECKING"
              ? "bg-amber-500 text-white animate-spin"
              : "bg-emerald-600 text-white hover:bg-emerald-700 ring-8 ring-emerald-200"
          }`}
          aria-label="Tap to speak your banking request"
        >
          {status === "RECORDING" ? "🎙️" : status === "CHECKING" ? "⏳" : "🎤"}
        </button>

        <p className="mt-6 text-2xl font-bold text-amber-950">
          {status === "RECORDING" && "Listening to your voice... Please speak."}
          {status === "CHECKING" && "Verifying your voice safety..."}
          {status === "IDLE" && "Tap the microphone and speak your request."}
          {status === "RESULT" && result?.agent_reply_text}
          {status === "ERROR" && result?.agent_reply_text}
        </p>
      </div>

      {/* Result Status Banner */}
      {result && (
        <div className={`p-6 rounded-2xl text-center border-2 ${
          result.decision === "APPROVE"
            ? "bg-emerald-100 border-emerald-400 text-emerald-950"
            : result.decision === "BLOCK_ALERT"
            ? "bg-red-100 border-red-500 text-red-950 animate-bounce"
            : "bg-amber-100 border-amber-400 text-amber-950"
        }`}>
          <div className="text-4xl mb-2">
            {result.decision === "APPROVE" && "✅"}
            {result.decision === "BLOCK_ALERT" && "🚨"}
            {result.decision === "STEP_UP" && "🔐"}
          </div>
          <h2 className="text-2xl font-extrabold">{result.reason}</h2>
          
          {result.tool?.status === "EXECUTED" && (
            <p className="mt-2 text-xl font-medium text-emerald-800">
              ₹45,000 sent to Rahul. New Balance: ₹2,00,000.
            </p>
          )}

          {pinRequired && (
            <div className="mt-4 p-4 bg-white rounded-xl border border-amber-300">
              <label className="block text-xl font-bold mb-2">Enter 4-Digit Security PIN</label>
              <input
                type="password"
                maxLength={4}
                placeholder="• • • •"
                className="text-center text-3xl tracking-widest w-40 p-2 border-2 border-amber-400 rounded-lg mx-auto block"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## 7. Judge & Compliance Telemetry Console Guide

### Real-Time Live Stream Architecture
The Judge Console should poll `/api/audit?limit=25` and `/api/stats` every 2.5 seconds or provide a manual "Refresh Telemetry" button.

### Key Console Dashboard Widgets
1. **Accumulated INR Savings Counter**:
   - `est_cost_savings_inr` (Formula: `(seconds_avoided / 60) * ₹10.00`).
   - Displays how much bank compute budget was saved by stopping synthetic clone bots before invoking NVIDIA Nemotron.
2. **2x2 Decision Matrix Scatter Visualizer**:
   - Plots X: `match_score` (0.0 to 1.0) against Y: `synthetic_score` (0.0 to 1.0).
   - Highlighting Thresholds:
     - Vertical Line: `MATCH_HIGH = 0.85`
     - Horizontal Lines: `SYNTH_LOW = 0.20`, `SYNTH_HIGH = 0.50`
   - Animates a radar dot to the exact coordinates of the latest turn.
3. **Cryptographic Agent Handshake Test Harness**:
   - Buttons:
     1. *"Issue ICICI Bot Credential"* (`POST /api/credential/issue`)
     2. *"Verify Valid Handshake"* (`POST /api/handshake/verify` -> Passes with `VERIFIED_AGENT`)
     3. *"Simulate Replay Attack"* (Submits same token again -> Rejection with `REPLAY ATTACK DETECTED`)

### Judge Telemetry Dashboard Snippet
```jsx
import React, { useEffect, useState } from 'react';
import { fetchAuditLogs, fetchTelemetryStats, issueAgentCredential, verifyAgentHandshake } from './api';
import { VerifiedAgentBadge } from './VerifiedAgentBadge';

export function JudgeConsole() {
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [testJwt, setTestJwt] = useState("");
  const [handshakeResult, setHandshakeResult] = useState(null);

  const loadData = async () => {
    try {
      const [statsData, auditData] = await Promise.all([
        fetchTelemetryStats(),
        fetchAuditLogs(20)
      ]);
      setStats(statsData);
      setLogs(auditData.logs || []);
    } catch (e) {
      console.error("Telemetry load failed", e);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 2500);
    return () => clearInterval(interval);
  }, []);

  const handleIssueCredential = async () => {
    const res = await issueAgentCredential({
      agent_id: "agent_sbi_voice_09",
      org: "SBI Senior Citizens Gateway",
      allowed_actions: ["TRANSFER_FUNDS"],
      limitInr: 50000.0
    });
    setTestJwt(res.credential);
    setHandshakeResult(null);
  };

  const handleVerifyCredential = async () => {
    if (!testJwt) return;
    const res = await verifyAgentHandshake(testJwt);
    setHandshakeResult(res);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-mono">
      {/* Top Bar */}
      <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <span className="h-3 w-3 rounded-full bg-emerald-500 animate-pulse"></span>
            UNCLONE GATE: JUDGE & TELEMETRY CONSOLE
          </h1>
          <p className="text-sm text-slate-400">Zero-Trust BFSI Voice Gating & Cost Optimization Gateway</p>
        </div>
        <button onClick={loadData} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700">
          ↻ REFRESH TELEMETRY
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <MetricCard title="TOTAL VOICE CHECKS" value={stats?.total_checks || 0} sub="Dual-Gate Eidos + Aletheia" />
        <MetricCard title="VERIFIED APPROVALS" value={stats?.total_approved || 0} color="text-emerald-400" sub="Human + Enrolled Voice" />
        <MetricCard title="ATTACKS BLOCKED" value={stats?.total_blocked || 0} color="text-red-400" sub="Clones & Impostors Stopped" />
        <MetricCard title="COST SAVINGS (INR)" value={`₹${stats?.est_cost_savings_inr?.toFixed(2) || "0.00"}`} color="text-amber-400" sub={`${stats?.agent_steps_skipped || 0} LLM Steps Avoided`} highlight />
      </div>

      {/* Two Column: Handshake Simulator & Live Audit Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Replay Simulator */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl">
          <h2 className="text-lg font-bold text-white mb-4">Agent-to-Agent Cryptographic Handshake</h2>
          <p className="text-xs text-slate-400 mb-4">
            Demonstrates single-use JWT verification and SQLite replay protection.
          </p>

          <div className="space-y-3">
            <button onClick={handleIssueCredential} className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-bold">
              1. ISSUE SINGLE-USE CREDENTIAL
            </button>
            <button onClick={handleVerifyCredential} disabled={!testJwt} className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded text-xs font-bold">
              2. VERIFY HANDSHAKE
            </button>
            <button onClick={handleVerifyCredential} disabled={!testJwt} className="w-full py-2.5 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white rounded text-xs font-bold">
              3. SIMULATE REPLAY ATTACK (RESEND TOKEN)
            </button>
          </div>

          <div className="mt-6">
            <VerifiedAgentBadge handshakeResult={handshakeResult} />
          </div>
        </div>

        {/* Right Column: Immutable Audit Stream */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 p-6 rounded-xl overflow-hidden">
          <h2 className="text-lg font-bold text-white mb-4">Live Immutable Incident Stream (SQLite)</h2>
          <div className="overflow-x-auto max-h-96">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800 text-slate-400 sticky top-0">
                <tr>
                  <th className="p-2">ID</th>
                  <th className="p-2">DECISION</th>
                  <th className="p-2">SYNTH SCORE</th>
                  <th className="p-2">MATCH SCORE</th>
                  <th className="p-2">TOOL</th>
                  <th className="p-2">INR SAVED</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/50">
                    <td className="p-2 text-slate-500">#{log.id}</td>
                    <td className="p-2 font-bold">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        log.decision === "APPROVE" ? "bg-emerald-950 text-emerald-400 border border-emerald-800" :
                        log.decision === "BLOCK_ALERT" ? "bg-red-950 text-red-400 border border-red-800" :
                        "bg-amber-950 text-amber-400 border border-amber-800"
                      }`}>
                        {log.decision}
                      </span>
                    </td>
                    <td className="p-2">{log.synthetic_score?.toFixed(2)}</td>
                    <td className="p-2">{log.match_score?.toFixed(2)}</td>
                    <td className="p-2 text-slate-300">{log.tool_status}</td>
                    <td className="p-2 text-emerald-400">₹{log.est_inr?.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, sub, color = "text-white", highlight = false }) {
  return (
    <div className={`p-5 rounded-xl border ${highlight ? "bg-amber-950/20 border-amber-500/50" : "bg-slate-900 border-slate-800"}`}>
      <div className="text-xs text-slate-400 mb-1">{title}</div>
      <div className={`text-3xl font-extrabold ${color}`}>{value}</div>
      <div className="text-[11px] text-slate-500 mt-2">{sub}</div>
    </div>
  );
}
```

---

## 8. Fail-Closed Error Handling & Edge Cases

### Fail-Closed Principle
Per Track 3 security guidelines, **under no circumstances will the system allow an action if an error or timeout occurs**. If the DetectifAI platform is unreachable, returns HTTP 502, or times out (> 5.0 seconds), the gateway automatically defaults to:
- `decision: "BLOCK"` (for transfers) or `"STEP_UP"` (for balance checks)
- `tool_allowed: false`
- `tool.status: "LOCKED"`
- `fail_closed: true`

### HTTP Error Codes Reference
| Code | Error Meaning | Gateway Fail-Closed Response |
| :--- | :--- | :--- |
| **`400 Bad Request`** | Audio file corrupted or header missing | `{"fail_closed": true, "error": "Audio format error: Empty audio buffer received."}` |
| **`502 Bad Gateway`** | DetectifAI API returned error or unreachable | `{"fail_closed": true, "error": "DetectifAI enrollment error: Connection refused"}` |
| **`500 Server Error`** | Unhandled server exception | `{"fail_closed": true, "error": "Server error: ...", "fail_closed": true}` |

### Client-Side Error Interceptor Pattern
```javascript
export async function safeGatewayFetch(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        ...(options.headers || {})
      }
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      // Deterministic client fail-closed fallback
      return {
        ok: false,
        status: res.status,
        decision: "BLOCK",
        tool: { status: "LOCKED" },
        reason: data?.error || "Gateway connection error. Transaction safely secured.",
        fail_closed: true
      };
    }

    return { ok: true, data };
  } catch (networkErr) {
    // Network offline / connection refused
    console.error("Network Failure:", networkErr);
    return {
      ok: false,
      decision: "BLOCK",
      tool: { status: "LOCKED" },
      reason: "Network connection lost. All banking actions frozen safely.",
      fail_closed: true
    };
  }
}
```

---

## 9. Frontend Integration Checklist

- [ ] **Configure API Origin**: Confirm backend runs at `http://localhost:8000` with CORS enabled (`ALLOWED_ORIGIN="*"`).
- [ ] **Do Not Force Content-Type**: Ensure `fetch()` calls with `FormData` do NOT set `'Content-Type': 'multipart/form-data'` manually.
- [ ] **Implement Color Badges**:
  - `APPROVE` -> Green (`#10B981`)
  - `BLOCK_ALERT` -> Red (`#EF4444`) with pulsing visual alert
  - `STEP_UP` -> Amber (`#F59E0B`) with 4-digit PIN input
- [ ] **Verified Agent Trust Shield**: Render the 4-point verification pills (`signature`, `expiry`, `unused`, `scope`).
- [ ] **Fail-Closed Safeguard**: Ensure UI locks tools and shows protective messages on any 4xx/5xx or network drop.
- [ ] **Senior Accessibility**: Ensure font size >= 20px and hook `window.speechSynthesis` to `agent_reply_text`.
- [ ] **Judge Telemetry Polling**: Poll `/api/audit` and `/api/stats` every 2.5 seconds to showcase real-time INR savings.
