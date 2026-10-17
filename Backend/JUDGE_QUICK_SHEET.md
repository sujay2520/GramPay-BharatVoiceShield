# 🎙️ GramPay (BharatVoice Shield) — 1-Page Judge Quick Sheet
**Track 3: UNCLONE Agents | 120-Second Pitch & Live Demo Presenter Cheat Sheet**  
*Presenter Instructions: Keep this file open on your phone or split screen during the 2-minute judging.*

---

## ⚡ 10-Second Elevator Pitch (The Instant Hook)
> **"GramPay is a zero-trust, language-agnostic voice gateway powered by DetectifAI that blocks AI voice clones in under 300 milliseconds—protecting 40 crore rural senior citizens like Ramesh Patel and saving banks an assumed ₹20 of expensive voice agent compute on every deflected fraud attack."**

---

## ⏱️ 1. Verbatim 2-Minute Pitch (120 Seconds Strictly Timed)

```
[0:00 - 0:25] Slide 1: Problem & User ──────► Speaker 1 (25s) — Ramesh Patel (Age 70+)
[0:00 - 0:50] Slide 2: Solution & Senior UI ─► Speaker 1 (25s) — Spoken ₹1,000 in 3 Languages
[0:50 - 1:20] Slide 3: DetectifAI (20M) ────► Speaker 2 (30s) — CRITICAL SECTION & 4,950 Credits
[1:20 - 1:40] Slide 4: Real Impact ─────────► Speaker 3 (20s) — ₹20/Call Compute Savings
[1:40 - 2:00] Slide 5: Scale & Day 2 ───────► Speaker 3 (20s) — Multilingual + Senior + Multi-Device
```

### [0:00 – 0:25] Slide 1: Problem & User (Speaker 1)
> "Good afternoon judges. Meet **Ramesh Patel**, a 70-year-old farmer in Gujarat paying for fertilizer using **NPCI Hello! UPI** voice commands on a feature phone.  
> An attacker harvests a 3-second WhatsApp voice note, generates a real-time neural voice clone, and calls the bank bot to siphon his Kisan savings.  
> Traditional biometrics fail because clones replicate vocal timbre, while 8kHz cellular compression blinds legacy acoustic filters—forcing NPCI to cap voice payments at ₹5,000.  
> GramPay solves this vulnerability."

### [0:25 – 0:50] Slide 2: Solution & Senior Citizen Mode (Speaker 1)
> "We built **GramPay (BharatVoice Shield)**: an inline, zero-trust gateway defending conversational voice agents.  
> Whether Ramesh speaks in Kannada, Hindi, or English to send ₹1,000:  
> 1. **Mutual Agent Handshake**: Cryptographic JWT verifies the bank bot to Ramesh before any audio flows.  
> 2. **Silent Passive Screening**: DetectifAI evaluates acoustic liveness in under 300 milliseconds.  
> 3. **Senior Citizen Mode**: Built for age 70+ farmers with 80px touch targets, calm fail-closed voice feedback, and agricultural presets.  
> Crucially: all banking tools remain **HARD-LOCKED** until voice liveness is mathematically proven."

### [0:50 – 1:20] Slide 3: DetectifAI Integration — [20 MARKS CRITICAL] (Speaker 2)
> "Here is our core engine: **Take DetectifAI out, and GramPay completely stops functioning.**  
> We integrate both DetectifAI OpenAPI endpoints:  
> • **Aletheia (`/v1/deepfake/detect`)** for synthetic vocoder detection.  
> • **Eidos (`/v1/speakers/verify`)** for 1-to-1 biometric matching.  
> Backed by **4,950 live platform credits** received directly from DetectifAI—including a dedicated **3,000 credit reserve** ring-fenced for our live presentations.  
> Our 3-tier deterministic policy router:  
> • **Tier 1 (Authentic & Matched)**: Silent Pass $\to$ Unlocks Hello! UPI payment tools immediately.  
> • **Tier 2 (Uncertain/8kHz Noise)**: NVIDIA Nemotron triggers a 4-word dynamic phrase and evaluates response latency.  
> • **Tier 3 (Synthetic Clone $\ge$ 0.62)**: Instant Containment $\to$ Drops call in <300ms, alerts fraud desk, and saves ₹20 compute."

### [1:20 – 1:40] Slide 4: Real-World Impact (Speaker 3)
> "The impact is twofold:  
> 1. **Financial Inclusion**: Safely elevates voice UPI limits above ₹5,000 for 40 crore regional feature-phone users across Kannada, Hindi, and English.  
> 2. **85% Voice Agent Cost Optimization**: Voice bots burn ₹10 per minute in telephony and LLM compute. Pre-gating drops clone swarms in 300 milliseconds—saving an assumed baseline of **₹20.00 per deflected call** by cutting 120 seconds of unnecessary GPU compute.  
> As our live compliance ticker shows: every blocked clone saves ₹20 directly."

### [1:40 – 2:00] Slide 5: Scale & Day 2 Deliverables (Speaker 3)
> "We scale via **SIPREC RTP forks** at bank SBCs (ICICI, Regional Rural Banks, Bhashini).  
> On Day 2, we directly delivered all jury recommendations:  
> • **Multilingual Voice Gateway**: Language-agnostic raw acoustic biometrics across Kannada, Hindi, and English.  
> • **Senior Citizen (Age 70+) Mode**: High-contrast, reassuring non-panic voice feedback, and rural agricultural word banks.  
> • **Multi-Device Live Sync**: Phone 1 Farmer, Phone 2 Impostor Clone, and Laptop Judge Console running in synchronized real-time.  
> GramPay is live right now with 4,950 verified credits. Thank you!"

---

## 📱 2. The 3-Device Live Demo Flow (Phone 1, Phone 2, Laptop Console)

The live presentation utilizes a synchronized **3-Device Architecture** proving end-to-end multi-device edge resilience:

```
┌─────────────────────────────────┐      ┌─────────────────────────────────┐
│     PHONE 1 (Farmer / Payer)    │      │    PHONE 2 (Attacker / Clone)   │
│ • Ramesh Patel (Age 70+)        │      │ • Social engineering fraudster  │
│ • Kannada / Hindi / English UI  │      │ • Injects 3s neural voice clone │
│ • Spoken "Send ₹1,000 fertilizer"│     │ • Tries unauthorized UPI drain  │
└────────────────┬────────────────┘      └────────────────┬────────────────┘
                 │                                        │
                 │ Voice Stream (PCM16 / 8kHz)            │ Synthetic Audio Stream
                 ▼                                        ▼
    ┌──────────────────────────────────────────────────────────┐
    │     GRAMPAY INLINE GATEWAY (DetectifAI Aletheia + Eidos)  │
    └─────────────────────────────┬────────────────────────────┘
                                  │ Real-Time Telemetry
                                  ▼
                 ┌─────────────────────────────────┐
                 │   LAPTOP (Judge Telemetry)      │
                 │ • Dual Biometric Gauges         │
                 │ • <300ms Latency Breakdown      │
                 │ • Clones Blocked +1             │
                 │ • ₹20 Saved Compute Ticker      │
                 │ • 4,950 Credits (3,000 Reserve) │
                 └─────────────────────────────────┘
```

### The 3 Live Demo Actions & Screen Feedback

| Step & Device | Action / Trigger | Visual Result on Device Screen | Laptop Judge Console Reaction | Exact Presenter Voice Track |
|:---:|:---|:---|:---|:---|
| **ACTION 1**<br>📱 *Phone 1*<br>🟢 **Green Authentic** | Ramesh taps 80px mic $\to$ speaks ₹1,000 fertilizer in Kannada/Hindi *(or clicks Preset ₹1,000)* | • Card flashes **EMERALD GREEN (✅ Approved)**<br>• Tool Lock flips: `🔒 LOCKED` $\to$ `⚡ UNLOCKED / EXECUTED`<br>• Kisan balance decrements: ₹28,500 $\to$ ₹27,500 | • Synth: **0.08** (Clean)<br>• Match: **0.88** (Authentic Ramesh)<br>• Latency: **268ms**<br>• Tool: **UNLOCKED** | *"Action 1 on Phone 1: Ramesh's authentic voice passes silently in 268 milliseconds. The Hello! UPI payment tool executes with zero senior friction."* |
| **ACTION 2**<br>📱 *Phone 2*<br>🔴 **Red Clone Block** | Attacker calls in on Phone 2 $\to$ injects cloned voice note (`sample_clone.wav`) | • Screen flashes **CRIMSON RED (🛑 Blocked · Synthetic Clone Alert)**<br>• Status: **HARD-LOCKED**<br>• Calming message: *"Namaste, transaction paused for your safety"* | • Synth: **0.94** (Clone Detected!)<br>• Latency: **242ms**<br>• Ticker: **Clones Blocked (+1)**<br>• Savings: **+₹20.00 Added** | *"Action 2 on Phone 2: An attacker mimics Ramesh with an AI voice clone. In 242 milliseconds, DetectifAI catches vocoder artifacts, hard-locks funds, and saves ₹20 of compute."* |
| **ACTION 3**<br>💻 *Laptop*<br>🟡 **Nemotron Challenge** | Click **"Launch Tier 2 Active Challenge"** *(or test latency >800ms buffer)* | • Senior UI displays dynamic agricultural phrase: *'ಬೆಳೆ ಮಳೆ ರಾಗಿ' / 'Fasal Baarish Gehun'*<br>• Latency timer activates | • Latency: **>800ms Voice Changer Lag Flagged**<br>• Catches neural vocoder buffering delay | *"Action 3: On borderline 8kHz lines, NVIDIA Nemotron prompts localized agricultural words. Real-time voice changers incur buffering lag over 800ms and are instantly dropped."* |

---

## 👴 3. Senior Citizen (Age 70+) Mode — Designed for Rural Farmers

Elderly rural citizens like **Ramesh Patel (Age 70+)** are the prime targets of voice clone syndicates due to acoustic isolation, non-literacy, and reliance on feature-phone IVR. GramPay provides a tailored **Senior Citizen Accessibility Architecture**:

1. **Accessibility-First Physical UI (WCAG 2.1 AAA Compliant)**:
   - **Giant Touch Targets**: Minimum `80px–96px` circular tactile microphone button.
   - **High-Legibility Typography**: Headers `≥ 28px`, body labels `≥ 20px`, high-contrast color scheme (7:1 contrast ratio against cream background).
   - **One-Touch Rural Presets**: Instant pre-fills for daily farming transactions:
     - 🌱 **₹1,000 Fertilizer** (IFFCO Urea & Seeds)
     - 🚜 **₹2,500 Fuel** (Tractor Diesel)
     - 🔍 **Check Balance** (₹0 Kisan Credit Account Inquiry)

2. **Multilingual Regional Voice Gateway**:
   - Ingests natural spoken commands in **Kannada (`kn-IN`)**, **Hindi (`hi-IN`)**, and **Indian English (`en-IN`)**.
   - Powered by DetectifAI's raw acoustic feature representations (WavLM/spectral distance), ensuring **100% language-agnostic biometric accuracy** without speech-to-text translation distortion.

3. **Reassuring, Non-Panic Fail-Closed Audio Feedback**:
   - In high-risk or blocked states, avoids technical error codes that trigger panic in elderly citizens.
   - Browser / telephony TTS speaks calmly at **0.9x speed** in the user's chosen language:
     > *"Namaste Ramesh-ji. To protect your hard-earned Kisan savings, we have safely paused this transaction. Our manager at your local branch has been informed."*

4. **Culturally Grounded Tier-2 Agricultural Word Bank**:
   - Replaced complex urban phrases with familiar farming terms for Tier-2 cognitive challenges:
     - **Kannada**: `ಬೆಳೆ` (*Bele* - Crop), `ಮಳೆ` (*Male* - Rain), `ರಾಗಿ` (*Ragi* - Millet), `ಹಸು` (*Hasu* - Cow).
     - **Hindi**: `फसल` (*Fasal* - Crop), `बारिश` (*Baarish* - Rain), `गेहूं` (*Gehun* - Wheat), `किसान` (*Kisan* - Farmer).
   - **Adaptive Latency Threshold**: Calibrated to distinguish natural senior cognitive pauses from neural voice changer buffering (>800ms).

---

## 🔢 4. Key Numbers to Memorize (Glance Card)

| Number | Metric Name | Exact Meaning & Hackathon Significance |
|:---:|:---|:---|
| **`4,950`** | **Live DetectifAI Credits** | Verified live API credits on `platform.detectif.ai`, with a **3,000 credit reserve** dedicated strictly for live presentations to guarantee 0 quota drops. |
| **`0.62`** | **Deepfake Threshold** | Aletheia (`/v1/deepfake/detect`): Score $\ge 0.62$ triggers immediate **Tier 3 BLOCK & HARD-LOCK** in <300ms. |
| **`0.53`** | **Speaker Match Threshold** | Eidos (`/v1/speakers/verify`): Cosine similarity $\ge 0.53$ mathematically confirms authentic 1:1 voiceprint match. |
| **`> 800ms`** | **Latency Buffer Flag** | Human cognitive response is $\le 800$ms. Real-time neural voice conversion (RVC / ElevenLabs STS) buffers >800ms. |
| **`₹20.00`** | **Saved per Blocked Call** | **Explicitly labeled assumed baseline**: $(120\text{s conversation avoided} / 60\text{s}) \times ₹10/\text{min}$ conversational compute rate. |
| **`< 300ms`** | **Pre-Gate Latency** | Inline acoustic screening terminates fraudulent calls before Turn 1 of LLM inference is triggered. |
| **`40 Crore`** | **Target Population** | Indian regional feature-phone users protected across Kannada, Hindi, and English voice banking. |

---

## 🥊 5. Rapid Answers to Top 3 Judge Trap Questions

### ⚠️ Trap Q1: "Why build an active cognitive challenge into Tier 2 instead of relying purely on passive acoustic detection?"
> **Rapid Answer (20s)**:  
> "Indian cellular telephony runs on 8kHz G.711 compression, which strips high-frequency spectral cues above 3.8kHz, pushing borderline noisy audio into the 0.50–0.62 uncertainty zone.  
> Furthermore, real-time voice conversion tools (RVC) require 150 to 300ms of computational buffering. When NVIDIA Nemotron prompts an unpredictable rural phrase like *'Fasal Baarish Gehun'*, human callers respond naturally within 600ms, while voice changers exceed our 800ms latency threshold and introduce phase anomalies caught on DetectifAI Pass 2."

### ⚠️ Trap Q2: "What happens if DetectifAI's API is down, rate-limited, or has a network timeout?"
> **Rapid Answer (15s)**:  
> "We enforce a strict **Fail-Closed Security Posture** under Hackathon Rule 5.4.  
> If DetectifAI returns a 5xx error, timeout, or missing scores, `gate.py` intercepts the exception and immediately defaults to `BLOCK` for fund transfers or `STEP_UP` for balance checks. Banking tools remain 100% hard-locked, customer funds are never exposed, and zero mock scores are fabricated.  
> Additionally, we have **4,950 live credits** on DetectifAI with **3,000 credits held in reserve**, ensuring zero rate-limiting during live judging."

### ⚠️ Trap Q3: "What happens if we remove DetectifAI from your architecture?" *(20 Marks Rubric Check)*
> **Rapid Answer (15s)**:  
> "**GramPay stops functioning completely.**  
> Our banking execution tools (`pay_merchant`, `execute_transfer_funds`) are instantiated in a hard-locked state with zero independent execution logic. They strictly query the deterministic gate driven by DetectifAI's Aletheia and Eidos scores. Without DetectifAI, every call fails closed and no payment can ever move."

---

### 💡 Bonus Lightning Rebuttals

* **Judge asks about ₹20 savings derivation**:  
  *"A standard conversational voice bot costs ₹10/min (Telephony ₹1.50, STT ₹0.80, LLM ₹4.00, TTS ₹3.70). Pre-gating in 300ms drops fraudulent bot swarms before turn 1 fires—saving 120 seconds of compute, or exactly ₹20 per blocked call."*
* **Judge asks about replay attacks / fake bank bots**:  
  *"We use single-use, scoped JWT credentials verified against an SQLite replay store. If an attacker replays a captured token, the second attempt is rejected instantly."*
* **Judge asks if acoustic detection works on Kannada/Hindi dialects**:  
  *"DetectifAI operates on raw audio spectrograms and acoustic glottal pulse physics (WavLM neural representations). It evaluates vocoder phase discontinuities, which are universal physical artifacts independent of human dialect or vocabulary."*
