# 🎙️ GramPay (BharatVoice Shield) — 1-Page Judge Quick Sheet
**Track 3: UNCLONE Agents | 120-Second Pitch & Live Demo Presenter Cheat Sheet**  
*Presenter Instructions: Keep this file open on your phone or split screen during the 2-minute judging.*

---

## ⏱️ 1. Verbatim 2-Minute Pitch (120 Seconds Strictly Timed)

```
[0:00 - 0:25] Slide 1: Problem & User ──► Speaker 1 (25s)
[0:25 - 0:50] Slide 2: Solution ────────► Speaker 1 (25s)
[0:50 - 1:20] Slide 3: DetectifAI (20M) ► Speaker 2 (30s) — CRITICAL SECTION
[1:20 - 1:40] Slide 4: Real Impact ─────► Speaker 3 (20s)
[1:40 - 2:00] Slide 5: Scale & Day 2 ───► Speaker 3 (20s)
```

### [0:00 – 0:25] Slide 1: Problem & User (Speaker 1)
> "Good afternoon judges. Meet **Ramesh Patel**, a 62-year-old farmer in Gujarat paying ₹5,000 for fertilizer using **NPCI Hello! UPI** voice commands on a feature phone.  
> An attacker harvests a 3-second WhatsApp voice note, generates a real-time neural voice clone, and calls the bank bot to drain his savings.  
> Traditional biometrics fail because clones replicate timbre, while 8kHz cellular compression blinds legacy filters—forcing NPCI to cap voice payments at ₹5,000.  
> GramPay solves this vulnerability."

### [0:25 – 0:50] Slide 2: Solution (Speaker 1)
> "We built **GramPay (BharatVoice Shield)**: an inline, zero-trust gateway defending conversational voice agents.  
> 1. **Mutual Agent Handshake**: Cryptographic JWT verifies the bank bot to Ramesh before the call connects.  
> 2. **Silent Passive Screening**: Evaluates biometric liveness in under 300 milliseconds.  
> 3. **Dynamic Active Challenge**: Catches neural vocoder conversion lag on noisy lines.  
> Crucially: all banking tools remain **HARD-LOCKED** until voice liveness is mathematically proven."

### [0:50 – 1:20] Slide 3: DetectifAI Integration — [20 MARKS CRITICAL] (Speaker 2)
> "Here is our core engine: **Take DetectifAI out, and GramPay completely stops functioning.**  
> We integrate both DetectifAI OpenAPI endpoints:  
> • **Aletheia (`/v1/deepfake/detect`)** for synthetic vocoder detection.  
> • **Eidos (`/v1/speakers/verify`)** for 1-to-1 biometric matching.  
> Our 3-tier deterministic policy router:  
> • **Tier 1 (Authentic & Matched)**: Silent Pass $\to$ Unlocks Hello! UPI payment tools immediately.  
> • **Tier 2 (Uncertain/8kHz Noise)**: NVIDIA Nemotron triggers a 4-word dynamic phrase and evaluates response latency.  
> • **Tier 3 (Synthetic Clone $\ge$ 0.62)**: Instant Containment $\to$ Kills call in <300ms, alerts fraud desk, and saves ₹20 compute.  
> Fully disclosed: DetectifAI APIs, MCP Server, FastAPI, and NVIDIA Nemotron."

### [1:20 – 1:40] Slide 4: Real-World Impact (Speaker 3)
> "The impact is twofold:  
> 1. **Financial Inclusion**: Safely elevates voice UPI limits above ₹5,000 for 500 million rural citizens.  
> 2. **85% Voice Agent Cost Optimization**: Voice bots burn ₹10 to ₹20 per call in LLM tokens and telephony compute. Pre-gating drops clone swarms in 300 milliseconds—saving 120 seconds of expensive GPU compute on every deflected call.  
> As our live compliance ticker shows: every blocked clone saves ₹20 directly."

### [1:40 – 2:00] Slide 5: Scale & Saturday Roadmap (Speaker 3)
> "We scale via **SIPREC RTP forks** at bank SBCs (ICICI, Regional Rural Banks, Bhashini).  
> For tomorrow's finals, our focused **9-hour Saturday roadmap** is strictly prioritized:  
> • **08:00–11:00 (Hours 1–3)**: WebSocket sliding-window audio streaming with WebRTC VAD for 8kHz G.711 compression.  
> • **11:00–14:00 (Hours 4–6)**: Full Tier 2 active cognitive latency timer (>2.5s) with Pass 2 re-scoring.  
> • **14:00–17:00 (Hours 7–9)**: DetectifAI MCP Server for two-way agent verification + Kannada & Hindi voice prompts.  
> GramPay is live right now with zero-login public access. Thank you!"

---

## 🖱️ 2. The Exact 3 Demo Clicks (30-Second Live Action)

| Click | Target UI Element | Visual Result on Screen | Exact Voice Track to Say |
|:---:|:---|:---|:---|
| **CLICK 1**<br>🟢 *Green Authentic* | Select `sample_human.wav` *(or click Preset ₹5,000)* $\to$ Click **"Check this voice"** | • Card flashes **EMERALD GREEN (✅ Approved)**<br>• Tool Lock flips: `🔒 LOCKED` $\to$ `⚡ UNLOCKED / EXECUTED`<br>• Telemetry: Synth ~0.08, Match >0.85, Latency <300ms | *"Click 1: Ramesh's authentic voice passes silently. Hello! UPI payment tool unlocks instantly with zero user friction."* |
| **CLICK 2**<br>🔴 *Red Clone Block* | Select `sample_clone.wav` $\to$ Click **"Check this voice"** | • Card flashes **CRIMSON RED (🛑 Blocked · Synthetic Clone Alert)**<br>• Tool status: **HARD-LOCKED**<br>• Telemetry Counters increment: **Clones Blocked +1**, **Rupee Savings +₹20.00** | *"Click 2: An AI voice clone attacks. DetectifAI flags vocoder synthesis artifacts in 280ms. The gate hard-locks funds and saves ₹20 of agent compute."* |
| **CLICK 3**<br>🟡 *Nemotron Challenge* | Click **"Launch Tier 2 Active Challenge"** *(or test latency >800ms / New Nemotron Phrase)* | • Modal displays dynamic 4-word phrase: *'Golden river seven mango'*<br>• Latency timer flags red: `>800ms Voice Changer Lag`<br>• Shows anti-buffering defense | *"Click 3: On noisy or borderline lines, NVIDIA Nemotron prompts a dynamic 4-word phrase. Real-time voice changers incur buffering lag over 800ms and get flagged immediately."* |

---

## 🔢 3. Key Numbers to Memorize (Glance Card)

| Number | Name | Exact Meaning & Significance |
|:---:|:---|:---|
| **`1,750`** | **Live Credits** | Active DetectifAI platform credits shown in top-right live status badge (`platform.detectif.ai`). |
| **`0.62`** | **Deepfake Threshold** | Aletheia (`/v1/deepfake/detect`): Score $\ge$ 0.62 triggers immediate **Tier 3 BLOCK & ALERT** (<300ms). |
| **`0.53`** | **Speaker Threshold** | Eidos (`/v1/speakers/verify`): Cosine similarity $\ge$ 0.53 confirms authentic 1:1 voiceprint match. |
| **`> 800ms`** | **Latency Buffer Flag** | Human cognitive response is $\le$ 800ms. Real-time neural voice conversion (RVC/vocoder) buffers >800ms. |
| **`₹20`** | **Saved per Blocked Call** | Deflecting a clone in 300ms avoids 120s of telephony (₹3), STT (₹1.60), LLM tokens (₹8), and TTS (₹7.40). |

---

## 🥊 4. Rapid Answers to Top 3 Judge Trap Questions

### ⚠️ Trap Q1: "Why build an active challenge into Tier 2 instead of relying purely on passive acoustic detection?"
> **Rapid Answer (20s)**:  
> "Indian cellular telephony runs on 8kHz G.711 compression, which strips high-frequency spectral cues above 3.8kHz, pushing borderline audio into the 0.50–0.62 uncertainty zone.  
> Furthermore, real-time voice conversion tools (RVC) require 150 to 300ms of computational buffering. When NVIDIA Nemotron prompts an unpredictable phrase like *'Golden river seven mango'*, human callers respond naturally, while voice changers exceed our 800ms latency threshold and introduce phase anomalies caught on DetectifAI Pass 2."

### ⚠️ Trap Q2: "What happens if DetectifAI's API is down, rate-limited, or has a network timeout?"
> **Rapid Answer (15s)**:  
> "We enforce a strict **Fail-Closed Security Posture** under Hackathon Rule 5.4.  
> If DetectifAI returns a 5xx error, timeout, or missing scores, `gate.py` intercepts the exception and immediately defaults to `BLOCK` for fund transfers or `STEP_UP` for balance checks. Banking tools remain 100% hard-locked, customer funds are never exposed, and zero mock scores are fabricated."

### ⚠️ Trap Q3: "What happens if we remove DetectifAI from your architecture?" *(20 Marks Rubric Check)*
> **Rapid Answer (15s)**:  
> "**GramPay stops functioning completely.**  
> Our banking execution tools (`pay_merchant`, `execute_transfer_funds`) are instantiated in a locked state with zero execution logic. They strictly query the deterministic gate driven by DetectifAI's Aletheia and Eidos scores. Without DetectifAI, every call fails closed and no payment can ever move."

---

### 💡 Bonus Lightning Rebuttals

* **Judge asks about ₹20 savings derivation**:  
  *"A standard conversational voice AI call lasts 2 minutes. Telephony is ₹1.50/min, STT ₹0.80/min, LLM ₹5/min, and neural TTS ₹6/min. Pre-gating in 300ms drops fraudulent bot swarms before turn 1 fires—saving ₹20 per call."*
* **Judge asks about replay attacks / fake bank bots**:  
  *"We use single-use, scoped JWT credentials verified against an SQLite replay store. If an attacker replays a captured token, the second attempt is rejected instantly."*
