# GramPay (BharatVoice Shield): Official Live Judge Demo Guide
**Track 3: UNCLONE Agents — Zero-Trust Voice Payment Gateway for NPCI Hello! UPI & BFSI Voice Bots**  
**Demo Target: Live Hackathon Jury (Tarini, Aayush & Technical Panel)**  
**Target Duration: Exactly 120 Seconds (2:00 Minutes) + 3 Minutes Live Interactive Q&A**

---

## 1. Executive Master Demo Matrix (120-Second Pitch Sync)

This guide provides the second-by-second execution blueprint for the hackathon team. The **Presenter (Speaking)** and the **Demo Operator (Driving the Laptop)** must rehearse in lockstep.

| Timestamp | Pitch Phase & Slide | Demo Step | Operator Action on Screen (`http://localhost:8000`) | Visual Confirmation on UI | Rubric Criteria |
|:---:|:---|:---|:---|:---|:---:|
| **0:00 – 0:25** (25s) | **Slide 1: Problem & User** *(Speaker 1)* | **Step 1: System Status & Credits** | Point to top-right header and giant status card. | Green **"Connected"** badge; **1,750 live DetectifAI credits** visible; **NVIDIA Nemotron** online; Card: `SYSTEM READY`. | **Problem & User (10)** |
| **0:25 – 0:50** (25s) | **Slide 2: Solution Architecture** *(Speaker 1)* | **Step 2: Live Enrollment & Authentic Payment** | Enroll Ramesh Patel (`tests/sample_human.wav`). Select preset **₹5,000 Seeds & Fertilizer** and submit. | Status turns **GREEN (`PAY / APPROVED`)**; Tool status: `EXECUTED`; Balance decrements from **₹28,500 $\to$ ₹23,500**. | **Progress by 18:00 (10)** |
| **0:50 – 1:20** (30s) | **Slide 3: DetectifAI Engine** *(Speaker 2)* | **Step 3: Synthetic Voice Clone Attack** | Upload `tests/sample_clone.wav` and click **Run GramPay Gate Check** for ₹5,000 transfer. | Instant sub-300ms **RED (`🛑 CLONE BLOCKED + ALERT`)**; Vocoder: 92.2%; Tool: **HARD-LOCKED**; Slide 4 counters tick up (+₹20.00). | **Use of DetectifAI (20)** *(Crucial!)* |
| **1:20 – 1:40** (20s) | **Slide 4: Impact & Cost Savings** *(Speaker 3)* | **Step 4: Tier-2 Active Cognitive Challenge** | Click **Launch Tier 2 Active Challenge**. Trigger dynamic 4-word phrase and start latency timer. | Status turns **AMBER (`EXTRA VOICE CHECK`)**; Nemotron phrase `"Golden river seven mango"`; Timer measures human (&lt;2.5s) vs clone lag (&gt;2.5s). | **Real Impact & Cost (10)** |
| **1:40 – 2:00** (20s) | **Slide 5: Scale & Saturday Plan** *(Speaker 3)* | **Step 5: Verified Bank Agent Badge** | Click **Issue Credential** $\to$ **Verify** $\to$ click **Replay Attack (Rejects)**. | Badge: **GREEN `VERIFIED_AGENT`** $\to$ then **ROSE `REJECTED (Replay Attack Detected)`** via SQLite JTI registry. | **Day 2 Roadmap & Team (10)** |

---

## 2. Pre-Demo Setup & Sanity Checklist (T-Minus 10 Minutes)

Before calling the judges to your screen or taking the stage, complete these exact verification steps:

```powershell
# ==============================================================================
# 1. Open Terminal (PowerShell) as Administrator in Backend folder
# ==============================================================================
cd "c:\Users\chandan.s\OneDrive\Desktop\Unclone\Backend"

# 2. Verify Python 3.12 environment & test suite integrity (All 27 must pass)
& "C:\Users\chandan.s\AppData\Local\Programs\Python\Python312\python.exe" -B -m unittest tests/test_contract.py

# 3. Launch Uvicorn Gateway Server on Port 8000
& "C:\Users\chandan.s\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Display & Browser Preparation:
1. **Open Google Chrome** (or Edge) in an **Incognito Window** to prevent aggressive caching.
2. Navigate to: `http://localhost:8000` (or `http://127.0.0.1:8000`).
3. Press `F11` (Fullscreen) and set zoom to **100%** (or **90%** if on a 1080p projector so both panels fit side-by-side).
4. Verify audio files exist in your quick-access file dialog:
   - `C:\Users\chandan.s\OneDrive\Desktop\Unclone\Backend\tests\sample_human.wav`
   - `C:\Users\chandan.s\OneDrive\Desktop\Unclone\Backend\tests\sample_clone.wav`
5. Have a second tab open to `http://localhost:8000/docs` (FastAPI Swagger UI) in case judges ask to inspect the OpenAPI contract directly.

---

## 3. Step-by-Step Live Demo Execution

---

### Step 1: Open `http://localhost:8000` & Show System Status (0:00 – 0:25)
> **Pitch Alignment**: Slide 1 — Problem & Rural Voice Banking Vulnerability  
> **Speaker**: Speaker 1  
> **Objective**: Prove zero-login public accessibility, live platform connectivity, real DetectifAI credits, and active NVIDIA Nemotron reasoning.

#### What the Speaker Says (0:00 – 0:25):
> *"Good afternoon judges. Meet Ramesh Patel, a 62-year-old farmer from Gujarat who pays for agricultural inputs using NPCI Hello! UPI voice calls. But today, a 3-second WhatsApp voice note harvested from Ramesh was converted into a real-time neural clone to siphon his savings. GramPay is the zero-trust gateway stopping this."*

#### What the Operator Does:
1. Show the top navigation bar of `http://localhost:8000`.
2. Hover over the **Health Badge** in the top-right corner.
3. Point out the live telemetry badges:
   - **Badge**: `GramPay Gate & DetectifAI: Reachable` (Vibrant Green Dot).
   - **Live DetectifAI Credits**: Displaying **1,750 live platform credits** authenticated via `DETECTIF_API_KEY` directly from `https://platform.detectif.ai/v1`.
   - **NVIDIA Nemotron Engine**: Configured with `nvidia/llama-3.1-nemotron-70b-instruct` / `nemotron-3.5-super-vl-120b` for dynamic cognitive reasoning.
4. Point to the **Giant Status Card**: Shows `🛡️ SYSTEM READY` with the caption: *"GramPay Voice Shield active for NPCI Hello! UPI & 123Pay."*

#### UI Visual Confirmation:
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ NPCI Hello! UPI & 123Pay Shield  ·  Track 3: Voice Gateway  ·  Powered by DetectifAI   │
│ GramPay UnClone: Voice Payment Security Shield        [ ● Gate & DetectifAI: Reachable ]│
│ 1,750 Live Credits Available  ·  NVIDIA Nemotron 70B Active                            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Step 2: Live Enrollment & Authentic Voice Payment (0:25 – 0:50)
> **Pitch Alignment**: Slide 2 — Defense-in-Depth Solution & Stage A Silent Screening  
> **Speaker**: Speaker 1  
> **Objective**: Show 1-to-1 voiceprint enrollment via DetectifAI Eidos, followed by an authentic voice payment that unlocks banking tools and decrements Ramesh's real simulated balance.

#### What the Speaker Says (0:25 – 0:50):
> *"GramPay introduces defense-in-depth: First, mutual cryptographic agent handshakes. Second, silent passive screening in under 300 milliseconds. Ramesh Patel enrolls his voice once into DetectifAI Eidos. When he issues a voice payment for fertilizer, our gate verifies vocal authenticity, unlocks our banking tools, and executes the UPI transfer."*

#### What the Operator Does:
1. **Enrollment (Right Panel — Speaker Enrollment Box)**:
   - In the "Account Holder Name" input, verify it says: `Ramesh Patel (Kisan Account)`.
   - Click "Choose File" under enroll and select `tests/sample_human.wav`.
   - Click the purple button: **`Enroll Speaker Profile`**.
   - **Visual Proof**: The label updates to `Current Speaker: Ramesh Patel (Kisan Account)` and the raw JSON shows DetectifAI Eidos returning `status: "enrolled"`, `voiceprint_id: "vp_..."`, and `embedding_quality: 0.94`.
2. **Authentic Payment (Left Panel — Voice Shield)**:
   - Click the quick preset button: **`🌱 Seeds & Fertilizer (Send ₹5,000)`**.
   - Notice the Banking Action automatically sets to `Send ₹5,000 for Fertilizer / Seeds (High Risk)` and the Amount sets to `5000`.
   - In the audio file picker, select `tests/sample_human.wav`.
   - Click the big gradient button: **`Run GramPay Gate Check`** (or **`Full Agent Turn`**).

#### UI Visual Confirmation:
- **Giant Status Card**: Flashes vibrant emerald green:
  ```
  ✅ PAY / APPROVED
  Verified Safe: Natural human voice and account holder identity confirmed.
  ```
- **Biometric Gauges**:
  - `Synthetic Vocoder`: **4.1%** (Clean Green — below 0.50 threshold).
  - `Speaker Match`: **94.1%** (Clean Cyan — above 0.53 threshold).
  - `Latency Breakdown`: Total ~**210 ms** (Det: 180ms | Ver: 195ms parallel execution).
- **Tool Status & Balance Deduction**:
  - Banking Tool: **`EXECUTED`** (`pay_merchant`).
  - Transaction Reference: `TXN-NPCI-123PAY-5000-PASS`.
  - **Balance Decrement**: Ramesh's Kisan account balance drops from **₹28,500.00** $\to$ **₹23,500.00** in live telemetry!

---

### Step 3: Trigger Synthetic Voice Clone Attack (0:50 – 1:20) — [CRITICAL 20 MARKS]
> **Pitch Alignment**: Slide 3 — DetectifAI Integration as the Non-Negotiable Core Engine  
> **Speaker**: Speaker 2 (ML Lead)  
> **Objective**: Demonstrate that when a high-quality AI voice clone mimics Ramesh, DetectifAI's Aletheia engine flags vocoder artifacts in &lt;300ms, hard-locks payment tools, sounds a fraud alert, and increments the Slide 4 cost-saving counters.

#### What the Speaker Says (0:50 – 1:20):
> *"Here is our core engine: Take DetectifAI out, and GramPay completely stops functioning. We integrate both of DetectifAI's OpenAPI endpoints: Deepfake Detection via Aletheia, and Speaker Verification via Eidos. Watch what happens when an attacker uses an ElevenLabs voice clone to steal Ramesh's fertilizer subsidy..."*

#### What the Operator Does:
1. Keep the action set to `Send ₹5,000 for Fertilizer / Seeds (High Risk)`.
2. Under "Live Voice Order", choose the attack fixture:
   - File: **`tests/sample_clone.wav`** (neural vocoder synthesis mimicking Ramesh's acoustic pitch).
3. Click: **`Run GramPay Gate Check`**.

#### UI Visual Confirmation (Instantaneous &lt; 300ms):
- **Giant Status Card**: Flashes alarming high-contrast **Red**:
  ```
  🛑 CLONE BLOCKED + ALERT
  CRITICAL WARNING: Computer-generated voice clone detected! Although the voice sounds 
  like the account holder, neural synthesis was identified (synth_score >= 0.62). 
  UPI payout frozen, bank fraud desk alerted, and LLM compute short-circuited.
  ```
- **Biometric Gauges**:
  - `Synthetic Vocoder`: **92.2%** (Blazing Red — exceeds 0.62 high-risk threshold).
  - `Speaker Match`: **93.2%** (Shows attacker successfully cloned Ramesh's vocal timbre, but vocoder artifacts betrayed them!).
- **Hard Tool Lock**:
  - Banking Tool: **`LOCKED`** (`pay_merchant: LOCKED`).
  - Result: `null` — Zero rupees leave the account. Customer funds remain 100% safe.
- **Token Bleed Deflection**:
  - Downstream NVIDIA Nemotron LLM turn is **completely bypassed** (0 tokens burned).
- **Slide 4 Live Demo Counters Increment in Real Time**:
  - `checks_run`: **+1** (e.g. 84 $\to$ 85).
  - `clones_blocked`: **+1** (e.g. 20 $\to$ 21).
  - `agent_steps_skipped`: **+1** (e.g. 32 $\to$ 33).
  - `agent_time_saved_inr`: **+₹20.00** (e.g. ₹640.00 $\to$ ₹660.00).

---

### Step 4: Tier-2 Active Cognitive Challenge (1:20 – 1:40)
> **Pitch Alignment**: Slide 4 — Real-World Impact, Cost Optimization & Cellular 8kHz Defense  
> **Speaker**: Speaker 3  
> **Objective**: Show how GramPay handles borderline or noisy 8kHz audio without false rejections, using NVIDIA Nemotron to generate unpredictable cognitive phrases and measure response buffering delay.

#### What the Speaker Says (1:20 – 1:40):
> *"Indian rural cellular calls use 8kHz G.711 compression, which strips acoustic frequencies above 3.8kHz and creates borderline scores. Instead of blindly blocking legitimate farmers, GramPay triggers Tier 2: an active cognitive challenge powered by NVIDIA Nemotron. Real-time clone engines stutter when forced to synthesize dynamic text, exceeding our 2.5-second latency threshold."*

#### What the Operator Does:
1. In the **Tier 2 Active Challenge Display** box (or by clicking the amber **"⚡ Launch Tier 2 Active Challenge"** button on the status card):
2. Click **`🔄 Generate New Phrase`**:
   - Point to the chips updating dynamically:
   - Example 1: `[Golden]` `[river]` `[seven]` `[mango]`
   - Example 2: `[Blue]` `[orbit]` `[seven]` `[sky]`
   - Emphasize to the judges: *This is generated by NVIDIA Nemotron and cannot be pre-recorded by a scammer.*
3. Click: **`Speak Phrase & Time Latency`** (or **`Verify Liveness`**):
   - Watch the **Response Latency Timer Bar** animate across the screen.
4. Point out the latency comparison:
   - **Human Baseline**: Spoken response begins in **&lt; 2.5 seconds** $\to$ Passes cognitive timing.
   - **Neural Voice Clone Conversion (RVC / Vocoder buffering)**: Conversion latency exceeds **2.85 seconds** $\to$ Gateway flags conversion lag and routes audio to Pass 2 DetectifAI re-scoring.

#### UI Visual Confirmation:
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚡ Tier 2 Active Challenge Display                      [ Anti-Deepfake Liveness ]     │
│ Randomized 4-Word Phrase:                                 [ 🔄 Generate New Phrase ]   │
│   [ Golden ]   [ river ]   [ seven ]   [ mango ]                                       │
│ Response Latency Timer (Max: 5.00s):                                      1.84 s       │
│ [████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Human Baseline: < 2.5s     │
│ Status: Human cognitive response verified within safe threshold                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Step 5: Verified Bank Agent Badge & Anti-Replay Defense (1:40 – 2:00)
> **Pitch Alignment**: Slide 5 — Scale, SBC SIPREC Deployment & Saturday 9-Hour Roadmap  
> **Speaker**: Speaker 3  
> **Objective**: Demonstrate cryptographic mutual agent-to-agent verification, protecting citizens against rogue bots, and proving instantaneous replay rejection via SQLite.

#### What the Speaker Says (1:40 – 2:00):
> *"To protect elderly citizens against rogue scam bots calling them, GramPay establishes a two-way cryptographic mutual handshake. Before the call connects, the bank agent presents a single-use JWT credential. When verified, our Verified Bank Agent Badge lights up. If an attacker intercepts and attempts to replay that credential, our immutable registry rejects it on the spot."*

#### What the Operator Does:
1. Navigate to the **Verified Bank Agent Badge** card on the right panel.
2. Click **`Issue Credential`**:
   - The gateway calls `POST /api/credential/issue` with agent ID `grampay_upi123_voice_bot` and scope `TRANSFER_FUNDS`.
   - The token text field populates with a freshly minted HS256 JWT containing a unique `jti` UUID.
3. Click **`Verify`**:
   - The gateway calls `POST /api/handshake/verify`.
   - **Visual Proof**: Badge label turns bright **Green**: **`VERIFIED_AGENT`**.
   - Reason displays: *"Cryptographically verified agent from GramPay Rural Banking (NPCI Hello! UPI). Safe to interact."*
4. **The Replay Attack Test**:
   - Immediately click: **`Replay Attack (Rejects)`** using the exact same token.
   - **Visual Proof**: Badge turns vivid **Rose/Red**: **`REJECTED`**.
   - Reason displays: *"REPLAY ATTACK DETECTED: This single-use agent credential has already been redeemed."*
   - SQLite table `used_credentials` prevented double-spending of the token!

#### UI Visual Confirmation:
```
First Click (Verify):
  [ 🏦 Verified Bank Agent Badge ]                    [ VERIFIED_AGENT ] (Green)
  Reason: Cryptographically verified agent from GramPay Rural Banking (NPCI Hello! UPI).

Second Click (Replay Attack):
  [ 🏦 Verified Bank Agent Badge ]                    [ REJECTED ] (Red)
  Reason: REPLAY ATTACK DETECTED: This single-use agent credential has already been redeemed.
```

5. **Pitch Conclusion (At Exactly 2:00)**:
   - Speaker 3 concludes on time: *"GramPay is live, zero-login, and running live DetectifAI calls right now. Thank you!"*

---

## 4. Post-Pitch Judge Q&A & Interactive Testing Guide

Judges (especially DetectifAI founders Tarini and Aayush) typically spend 2 to 3 minutes stress-testing your implementation. Use these pre-rehearsed answers and live terminal demonstrations:

### Question 1 (Aayush / Tarini): "Can you prove you are actually calling DetectifAI's live servers and not returning canned mock data?"
> **Team Answer (Speaker 2)**:
> *"Yes, absolutely! We strictly comply with Hackathon Rule 5.4. Notice our live credits counter currently shows 1,750 credits on `platform.detectif.ai`. Let us run a live curl request in the terminal right in front of you."*

**Live Terminal Proof (Run in PowerShell)**:
```powershell
# Live credit balance directly from platform.detectif.ai
Invoke-RestMethod -Uri "http://localhost:8000/api/credits" -Method Get | ConvertTo-Json
```
*Expected Output*:
```json
{
  "status": "ok",
  "plan": "free",
  "unlimited": false,
  "available": 1700,
  "reserved": 0,
  "price_per_operation": 50,
  "latency_ms": 1159
}
```

---

### Question 2: "What happens if DetectifAI's API goes down or network packets drop?"
> **Team Answer (Speaker 2)**:
> *"GramPay enforces a strict **Fail-Closed Security Posture**. If the DetectifAI API times out or returns HTTP 5xx, `gate.py` intercepts the error and flags `fail_closed=True`. Banking tools remain 100% hard-locked, and zero mock scores are ever fabricated."*

**Live Terminal Proof (Simulate Missing Key / Network Drop)**:
```powershell
# Show fail-closed response contract
Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get | ConvertTo-Json
```

---

### Question 3: "Why did you build an active challenge into Tier 2 instead of relying purely on passive acoustic detection?"
> **Team Answer (Speaker 2)**:
> *"Passive acoustic detection is outstanding on 16kHz studio audio, but Indian rural telephony uses 8kHz G.711 $\mu$-law compression. That compression strips spectral cues above 3.8kHz, causing genuine farmer calls to land in the 0.50–0.62 uncertainty zone.
> 
> Furthermore, real-time voice conversion tools (like RVC running on a local GPU) require 150ms to 300ms of buffering when forced to pronounce dynamic, unpredictable text. When Nemotron asks the caller to repeat 'Golden river seven mango', an attacker's pipeline stutters past our 2.5-second threshold, exposing their synthetic nature."*

---

### Question 4: "How does your gateway save ₹20 per call?"
> **Team Answer (Speaker 3)**:
> *"In conversational voice AI architectures (like Bolna, LiveKit, or Twilio Voice), a standard banking call runs 2 to 3 minutes. That burns telephony charges (₹1.50/min), real-time STT (₹0.80/min), LLM tokens (₹5/min), and neural TTS (₹6/min)—totaling ₹10 to ₹20 per call.
> 
> By pre-gating audio with DetectifAI in 300 milliseconds, we drop fraudulent bot swarms before turn 1 of the LLM pipeline ever fires. As our Slide 4 ticker shows, blocking 20 clones saved ₹400 in direct compute costs."*

---

## 5. Emergency Troubleshooting & Rapid Recovery Runbook

| Scenario | Symptom | Immediate Fix (Takes &lt; 5 seconds) |
|:---|:---|:---|
| **Port 8000 conflict** | `error: [Errno 10048] error while attempting to bind on address` | In PowerShell: `Get-Process python \| Stop-Process -Force` then restart `uvicorn backend.main:app --port 8000`. |
| **Microphone blocked** | Browser blocks audio capture permissions | Switch immediately to file upload mode: use `tests/sample_human.wav` and `tests/sample_clone.wav`. They are pre-staged for this exact scenario. |
| **Credits drop to 0** | Upstream DetectifAI returns 402 or 429 quota error | Check `.env` key. If exhausted, point to the fail-closed demonstration: *Show judges that the system safely locks customer funds rather than guessing.* |
| **UI needs fresh counters** | Slide 4 counters need to be cleared or reset | Click **`🔄 Refresh stats`** or restart the server. SQLite database `data/audit.db` persists all transactions. |
| **Replay test fails** | Credential was already used in a previous rehearsal | Click **`Issue Credential`** to mint a brand new token with a fresh `jti`. |

---

## 6. Slide-to-Demo Timeline Synchronization Summary

```
0:00 ──────────────────── 0:25 ──────────────────── 0:50 ──────────────────── 1:20 ──────────────────── 1:40 ──────── 2:00
[ SLIDE 1: Problem ]      [ SLIDE 2: Solution ]     [ SLIDE 3: DetectifAI ]   [ SLIDE 4: Impact ]       [ SLIDE 5: Scale ]
[ STEP 1: Status & Cred ] [ STEP 2: Enroll & Pay ]  [ STEP 3: Clone Attack ]  [ STEP 4: Tier-2 Cog ]    [ STEP 5: Badge ]
• http://localhost:8000   • Enroll Ramesh           • Upload sample_clone.wav • Dynamic 4-word phrase   • Issue JWT
• Green Connected Badge   • Preset: ₹5,000 Seeds    • Red 🛑 BLOCK_ALERT (<300ms)• Latency timer (<2.5s)  • Green VERIFIED
• 1,750 Live Credits      • Green ✅ APPROVE        • Tool HARD-LOCKED        • Defeats vocoder lag     • Replay REJECTED
• Nemotron 70B Online     • Balance: ₹28.5k->₹23.5k • Slide 4 Counters Tick Up• Pass 2 re-scoring      • Saturday Roadmap
```

**Judges will be blown away by the precision, polish, and mathematical rigor of this demonstration. Good luck team!**
