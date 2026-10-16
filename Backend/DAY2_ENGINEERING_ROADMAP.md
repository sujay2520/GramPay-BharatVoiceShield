# UnClone Gate: Day 2 Engineering Roadmap & Execution Specification
**Track 3: UNCLONE Agents — Zero-Trust Voice Biometric & Agent Security Gateway**  
**Saturday Execution Schedule: 08:00 – 17:00 IST (Slide 5 Reference Architecture)**

---

## Executive Summary & Slide 5 Alignment

The **UnClone Gate** architecture secures high-consequence Banking, Financial Services, and Insurance (BFSI) voice channels by decoupling raw audio ingestion from downstream Large Language Model (LLM) agents. Day 1 established the core deterministic **2x2 Lexis Policy Engine** ([`backend/gate.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/gate.py)), dual-model **DetectifAI (Aletheia + Eidos)** verification ([`backend/detectif_client.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/detectif_client.py)), **NVIDIA Nemotron-70B** intent reasoning ([`backend/agent.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/agent.py)), single-use cryptographic JWT credential issuance ([`backend/credentials.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/credentials.py)), and an immutable SQLite audit trail ([`backend/audit.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/audit.py)).

This engineering roadmap outlines the **exact 9-hour execution plan for Saturday (08:00 – 17:00 IST)** specified in **Slide 5** of the UnClone architecture presentation. It translates the theoretical pre-gating concept into a hardened, production-grade streaming telephony pipeline built on [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py).

```
========================================================================================
                      SATURDAY 9-HOUR ENGINEERING SPRINT (SLIDE 5)
========================================================================================
 [08:00 - 11:00]  PHASE 1: Real-Time WebSocket Streaming & Phone-Quality Audio Hardening
                  - Sliding-window ring buffering (1.0s - 2.0s)
                  - ITU-T G.711 mu-law decoding & 8kHz -> 16kHz linear upsampling
                  - PSTN narrowband acoustic impairment validation
----------------------------------------------------------------------------------------
 [11:00 - 14:00]  PHASE 2: Active Challenge Engine & Latency Timing Buffer Analysis
                  - Dynamic challenge phrase generation via NVIDIA Nemotron-70B
                  - Precise millisecond response latency tracking (>800ms threshold)
                  - Real-Time Voice Changer (RVC) detection & DetectifAI re-scoring
----------------------------------------------------------------------------------------
 [14:00 - 17:00]  PHASE 3: Verified-Agent Handshake, Bhashini Indic Pipeline & Demo Polish
                  - Single-use scoped JWT token issuance & replay prevention
                  - Bhashini integration for Hindi (hi-IN) and Kannada (kn-IN) prompts
                  - End-to-end live demo choreography with Grok UI visual sync
========================================================================================
```

---

## Detailed System Architecture: Zero-Trust Telephony Pre-Gate

Traditional voice AI setups in BFSI connect callers directly to Speech-to-Text (STT) and LLM dialogue managers before identity authentication. This opens institutions to severe financial fraud and **Economic Denial of Service (token bleed)**, wasting ₹10–₹20 per fraudulent call.

UnClone Gate intercepts raw telephony media streams (Twilio Media Streams, SIP RTP, WebRTC) at the boundary, enforcing a strict **fail-closed pre-gate** before conversational voice agents (LiveKit, Pipecat, Bolna) or banking execution tools are triggered.

```mermaid
flowchart TD
    subgraph INGESTION["Phase 1: Ingestion & Sliding Window (08:00-11:00)"]
        Caller["Caller / SIP / PSTN / Twilio"] -->|"8kHz G.711 mu-law (20ms frames)"| WS["TwilioMediaStreamBridge (/ws/twilio)"]
        WS --> Codec["TelephonyAudioCodec: mu-law -> PCM16"]
        Codec --> RingBuf["TelephonyAudioBuffer: 1.5s Sliding Window"]
    end

    subgraph PRE_GATE["Deterministic Pre-Gate (Lexis Engine)"]
        RingBuf -->|"1.5s Audio Ready"| Dispatch{"Parallel Dispatch"}
        Dispatch --> Aletheia["DetectifAI Aletheia: Synthetic Vocoder Artifacts"]
        Dispatch --> Eidos["DetectifAI Eidos: 1:1 Enrolled Voiceprint Match"]
        Aletheia --> GateMatrix["evaluate_gate: Deterministic 2x2 Matrix"]
        Eidos --> GateMatrix
    end

    subgraph ACTIVE_CHALLENGE["Phase 2: Active Challenge Engine (11:00-14:00)"]
        GateMatrix -->|"Borderline / High-Risk"| Challenge["Dynamic Challenge Engine"]
        Challenge --> PromptGen["Nemotron-70B: Dynamic Nonce Phrase"]
        PromptGen --> Playback["Twilio 'mark' TTS Playback"]
        Playback --> Timer["Latency Timing Buffer: Measure Δt"]
        Timer -->|"Δt > 800ms (RVC Detected)"| RejectRVC["BLOCK_ALERT: Neural Voice Changer"]
        Timer -->|"Δt <= 800ms (Human Reaction)"| Rescore["DetectifAI Re-Score + VAD Verification"]
    end

    subgraph FEDERATION["Phase 3: Agent Handshake & Indic Handoff (14:00-17:00)"]
        GateMatrix -->|"APPROVED"| Handshake["CredentialService: Mint Single-Use JWT"]
        Rescore -->|"APPROVED"| Handshake
        Handshake --> Indic["Bhashini Indic Adapter (Hindi / Kannada)"]
        Indic --> Downstream["Downstream Agents: LiveKit / Pipecat / Bolna"]
        Downstream --> Tools["BankingTools: Funds Transfer / Balance Check"]
    end

    subgraph REJECTION["Instant Short-Circuit (Zero Token Bleed)"]
        GateMatrix -->|"BLOCK / BLOCK_ALERT"| Hangup["Twilio <Hangup> / Clear Event"]
        RejectRVC --> Hangup
        Hangup --> Audit["SQLite Audit Ledger: Save ₹20/call"]
    end
```

---

## Saturday Sprint Breakdown (08:00 – 17:00)

```
========================================================================================================================
 TIME BLOCK         MODULE & MILESTONE          KEY DELIVERABLES & CODE TARGETS             ACCEPTANCE CRITERIA
========================================================================================================================
 08:00 - 09:00      Sliding Window Buffer       TelephonyAudioBuffer sliding window         1.5s buffer gate triggers;
                                                drain_chunks() context preservation         zero dropped audio frames
------------------------------------------------------------------------------------------------------------------------
 09:00 - 10:00      Narrowband Codec Engine     TelephonyAudioCodec.mulaw_to_pcm16          Bit-exact G.711 conversion;
                                                resample_8k_to_16k linear upsampling        16kHz WAV header valid
------------------------------------------------------------------------------------------------------------------------
 10:00 - 11:00      WebSocket Stress Test       TwilioMediaStreamBridge (/ws/twilio)        13 unit tests pass;
                                                tests/test_telephony_bridge.py              sub-400ms gate decision
------------------------------------------------------------------------------------------------------------------------
 11:00 - 12:00      Dynamic Challenge Engine    LLM nonce generation via Nemotron-70B       Unpredictable phrase;
                                                /api/telephony/challenge/generate           phonetically rich tokens
------------------------------------------------------------------------------------------------------------------------
 12:00 - 13:00      Latency Timing Buffer       Twilio 'mark' to VAD onset timer            Accurate millisecond tracking;
                                                Delta t > 800ms neural lag detector         flags RVC pipeline latency
------------------------------------------------------------------------------------------------------------------------
 13:00 - 14:00      DetectifAI Re-Scoring       /api/telephony/challenge/verify             Composite trust score;
                                                Secondary Aletheia + Eidos inference        fail-closed IVR PIN fallback
------------------------------------------------------------------------------------------------------------------------
 14:00 - 15:00      Verified-Agent Handshake    CredentialService single-use JWT            Single-use JTI replay check;
                                                X-UnClone-Credential LiveKit header         scoped to banking limits
------------------------------------------------------------------------------------------------------------------------
 15:00 - 16:00      Bhashini Indic Pipeline     Hindi (hi-IN) & Kannada (kn-IN) TTS/ASR     Natural Indic prompts;
                                                Vernacular biometric calibration            regional dialect tolerance
------------------------------------------------------------------------------------------------------------------------
 16:00 - 17:00      Live Demo Polish & Sync     Grok UI WebSocket telemetry synchronization 3 end-to-end scenarios rehearsed;
                                                Cost-savings counter in INR                 judges presentation verified
========================================================================================================================
```

---

## Phase 1: 08:00 – 11:00 | Real-Time WebSocket Streaming & Phone-Quality Codec Hardening

### 1. The Engineering Challenge: Phone-Quality Audio vs. Deepfake Detection
Standard cellular and PSTN telephony networks transmit audio using the **ITU-T G.711 $\mu$-law** companding algorithm sampled at **8,000 Hz** with 8-bit quantization (64 kbps). The analog voiceband is strictly bandpass-filtered between **300 Hz and 3,400 Hz**.

This introduces two distinct architectural challenges:
1. **High-Frequency Attenuation**: State-of-the-art neural vocoders (e.g., HiFi-GAN, WaveGlow, BigVGAN) leave subtle phase discontinuities and synthetic artifacts in the $4\text{ kHz} - 8\text{ kHz}$ frequency spectrum. When processed through 8kHz narrowband telephony, carrier downsampling truncates all frequencies above $4\text{ kHz}$ (Nyquist limit), potentially masking synthetic signatures.
2. **Logarithmic Quantization Noise**: G.711 $\mu$-law companding applies non-linear logarithmic quantization ($y = \text{sgn}(x) \frac{\ln(1 + \mu |x|)}{\ln(1 + \mu)}$, with $\mu=255$). This introduces subtle harmonic distortion that naive deepfake detectors might misclassify as synthetic noise.

### 2. Implementation Specifications in [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py)

#### A. ITU-T G.711 $\mu$-Law Decoding Table (Lines 82–100)
Python 3.12+ deprecated the standard library `audioop` module. To guarantee zero external C-dependencies, portability across Windows/Linux, and high decoding throughput, [`_build_g711_mulaw_table()`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L82-L99) creates an immutable 256-element integer lookup table:

```python
def _build_g711_mulaw_table() -> Tuple[int, ...]:
    table = []
    for b in range(256):
        u = ~b & 0xFF
        sign = u & 0x80
        exponent = (u >> 4) & 0x07
        mantissa = u & 0x0F
        sample = ((mantissa << 3) + 0x84) << exponent
        sample -= 0x84
        table.append(-sample if sign == 0 else sample)
    return tuple(table)
```
Each incoming 20ms chunk (160 bytes) is unpacked into 16-bit linear PCM in **$< 0.05\text{ ms}$** via `struct.pack`.

#### B. Linear Interpolation Upsampling: 8kHz $\rightarrow$ 16kHz (Lines 128–146)
DetectifAI Aletheia and Eidos models require 16kHz linear PCM16 input. [`TelephonyAudioCodec.resample_8k_to_16k`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L128-L146) performs linear interpolation without introducing phase artifacts:
$$y[2n] = x[n], \quad y[2n+1] = \frac{x[n] + x[n+1]}{2}$$

#### C. Sliding Window Buffer (`TelephonyAudioBuffer`, Lines 162–215)
- Standard telephony packetization emits **20ms frames** (160 bytes of $\mu$-law $\rightarrow$ 320 bytes of PCM16).
- Target evaluation duration: **1.5 seconds** ($75 \text{ chunks} = 12,000 \text{ samples} = 24,000 \text{ bytes}$).
- **Sliding Ring Mechanism**: Once 1.5s of audio accumulates, [`is_gate_ready()`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L195-L198) triggers parallel inference. If the speaker continues, old chunks slide out while retaining recent acoustic context for ongoing re-evaluation.
- When `APPROVED`, [`drain_chunks()`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L211-L215) flushes the entire buffered 1.5s PCM stream downstream to LiveKit/Pipecat/Bolna STT, ensuring **zero dropped words** from the caller's greeting.

### 3. Deliverables & Verification Checklist (08:00 – 11:00)
- [x] Pure Python G.711 codec benchmarked with bit-exact PCM16 output.
- [x] Sliding window buffer verified at 75 chunks ($1.50\text{s}$) with 8kHz and 16kHz export.
- [x] WebSocket `/api/telephony/ws/twilio` tested under simulated packet jitter and base64 payloads.
- [x] Automated test suite [`tests/test_telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/tests/test_telephony_bridge.py) passing all 13 test cases:
  ```powershell
  & "C:\Users\chandan.s\AppData\Local\Programs\Python\Python312\python.exe" -m unittest tests/test_telephony_bridge.py
  # Result: Ran 13 tests in 0.093s -> OK
  ```

---

## Phase 2: 11:00 – 14:00 | Active Liveness Challenge Engine & Latency Timing Buffer (>800ms Neural Voice Changer Detection)

### 1. The Threat Model: Real-Time Neural Voice Changers (RVC)
In a zero-trust BFSI setting, passive biometric verification alone is vulnerable to **man-in-the-middle real-time voice conversion**:
1. An attacker places a telephone call to the bank's conversational IVR.
2. The attacker speaks naturally into their microphone.
3. Software like **RVC (Retrieval-based Voice Conversion)**, **ElevenLabs Speech-to-Speech (STS)**, or **Seed-VC** converts the attacker's acoustic timbre into the victim's enrolled voiceprint in real time.
4. If the attacker simply says standard greetings ("Hello, I want to transfer money"), the converted audio might pass passive voiceprint similarity checks.

### 2. Physical & Computational Bottleneck: The >800ms Voice Changer Latency Buffer
Real-time neural voice conversion pipelines inherently incur cumulative pipeline latencies:
- **Audio Chunking & Buffering**: 150ms – 250ms (required by STT or acoustic feature extractors).
- **Pitch & Formant Extraction (CREPE / Harvest / PM)**: 50ms – 100ms.
- **Deep Neural Network Conversion Inference**: 200ms – 400ms.
- **Neural Vocoder Waveform Synthesis**: 100ms – 200ms.
- **Telephony & Network RTT**: 100ms – 200ms.
- **Total End-to-End Latency Buffer**: **600ms – 1,150ms** beyond standard cognitive human response time.

Conversely, a real human reacting to an auditory prompt has a cognitive reaction time of **250ms – 450ms**.

```
Human Response:        [ Prompt Ends ] ---> (250ms - 450ms) ---> [ Human Voice Starts ]
RVC Attacker:          [ Prompt Ends ] ---> (Human hears) ---> [ Attacker speaks ] ---> (600ms-1100ms RVC Pipeline) ---> [ Cloned Audio Starts ]
                                           |<---------------- Total Latency: > 800ms - 1500ms ------------------>|
```

> [!IMPORTANT]
> Any response latency buffer exceeding **800 milliseconds** ($\Delta t > 800\text{ms}$) on a randomized, context-dependent challenge prompt provides strong evidence of an intermediary neural voice changer or pipeline synthesis buffer.

### 3. Active Challenge Technical Protocol

```mermaid
sequenceDiagram
    autonumber
    actor Caller as Caller / Attacker (RVC)
    participant Bridge as Twilio Media Streams Bridge
    participant Agent as NVIDIA Nemotron-70B
    participant VAD as Telephony Energy VAD
    participant Gate as UnClone Gate
    participant Detectif as DetectifAI (Aletheia + Eidos)

    Bridge->>Gate: Initial 1.5s Greeting Audio
    Gate->>Detectif: Analyze & Verify
    Detectif-->>Gate: Borderline Score (Synth 0.35, Match 0.88)
    Gate-->>Bridge: Trigger Active Liveness Challenge
    
    Bridge->>Agent: Generate Dynamic Challenge Nonce
    Agent-->>Bridge: "Please repeat: 'Mysore palace lights glow bright tonight'"
    Bridge->>Caller: Stream Audio + Send Twilio <mark name="challenge_end">
    
    Note over Bridge,Caller: Twilio emits mark event at t = t_prompt_end
    
    Caller->>Bridge: Streaming Audio Response
    VAD->>Bridge: Voice Activity Detected at t = t_utterance_start
    
    Note over Bridge: Calculate Δt = t_utterance_start - t_prompt_end
    
    alt Δt > 800ms (RVC Delay Detected)
        Bridge->>Gate: Anomaly Flag: Latency = 1040ms (> 800ms)
        Gate->>Gate: Escalate Policy -> BLOCK_ALERT / STEP_UP
        Gate-->>Bridge: Send TwiML <Hangup> or IVR PIN Gather
    else Δt <= 800ms (Natural Human Reaction)
        Bridge->>Detectif: Re-Score Challenge Audio
        Detectif-->>Gate: Aletheia: 0.08 (Natural) | Eidos: 0.94 (Match)
        Gate->>Gate: Deterministic Matrix -> APPROVE
        Gate-->>Bridge: Issue JWT Credential & Unlock Voice Pipeline
    end
```

### 4. Implementation Design in `backend/telephony_bridge.py`

#### A. Dynamic Challenge Generator ([`backend/agent.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/agent.py))
The LLM generates single-use dynamic phonetic phrases embedded with randomized nonces:
```python
def generate_active_challenge_prompt(speaker_name: str, language: str = "en-IN") -> Dict[str, str]:
    """Generates an unpredictable phonetic challenge phrase with low perplexity for humans."""
    nonce = f"{random.randint(10, 99)}"
    phrases = {
        "en-IN": f"Security verification: Please confirm code {nonce} and say: 'The green river flows through Bangalore'.",
        "hi-IN": f"सुरक्षा पुष्टि: कृपया कोड {nonce} बताएं और कहें: 'वाराणसी के घाट पर आज शाम गंगा आरती है'。",
        "kn-IN": f"ಸುರಕ್ಷತಾ ದೃಢೀಕರಣ: ದಯವಿಟ್ಟು ಕೋಡ್ {nonce} ಹೇಳಿ: 'ಮೈಸೂರು ಅರಮನೆಯಲ್ಲಿ ಇಂದು ದೀಪಾಲಂಕಾರವಿದೆ'。"
    }
    return {
        "nonce": nonce,
        "language": language,
        "challenge_phrase": phrases.get(language, phrases["en-IN"])
    }
```

#### B. Millisecond Latency Buffer Tracking via Twilio Mark Events
1. Telephony bridge sends audio frames to the caller and appends a `mark` message:
   ```json
   {"event": "mark", "streamSid": "MZ123", "mark": {"name": "CHALLENGE_PLAYBACK_COMPLETE"}}
   ```
2. When Twilio finishes playing the audio, it sends a WebSocket callback with `mark.name = "CHALLENGE_PLAYBACK_COMPLETE"`. The bridge records:
   $$t_{\text{prompt\_end}} = \text{time.perf\_counter()}$$
3. As the caller speaks, the streaming buffer checks root-mean-square (RMS) energy threshold:
   $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} x[i]^2} > \text{VAD\_THRESHOLD\_DBFS}$$
4. The first frame exceeding threshold marks utterance onset:
   $$t_{\text{utterance\_start}} = \text{time.perf\_counter()}$$
   $$\Delta t = (t_{\text{utterance\_start}} - t_{\text{prompt\_end}}) \times 1000 \text{ ms}$$
5. If $\Delta t > 800\text{ ms}$, the session records an **RVC Latency Anomaly**.

#### C. Composite Trust Metric & DetectifAI Re-Scoring
The accumulated challenge audio is re-submitted to DetectifAI. The composite trust score is calculated:
$$\text{Trust} = 0.50 \cdot (1 - \text{SynthScore}) + 0.50 \cdot \text{MatchScore} - 0.30 \cdot \mathbb{I}(\Delta t > 800\text{ms})$$

If $\text{Trust} \ge 0.80$ and $\Delta t \le 800\text{ms}$, the call transitions to `APPROVED`. Otherwise, it triggers `BLOCK_ALERT` (or falls back to `STEP_UP` 4-digit IVR PIN).

---

## Phase 3: 14:00 – 17:00 | Verified-Agent Cryptographic Handshake, Indic Multi-Dialect Pipeline (Bhashini) & Live Demo Polish

### 1. Verified-Agent Handshake (Agent-to-Agent Security)
When multi-agent BFSI architectures interact (e.g., an automated external loan aggregator bot calling HDFC Bank's voice API), UnClone Gate enforces the **Agent-to-Agent (A2A) Cryptographic Handshake** implemented in [`backend/credentials.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/credentials.py):

```
                        AGENT-TO-AGENT VERIFICATION PROTOCOL
                        
 [ Calling Voice Agent ]                     [ UnClone Telephony Gate ]
            │                                             │
            ├──── 1. POST /api/credential/issue ─────────►│
            │     { agent_id, org, allowed_actions }      │
            │                                             │ 2. Mint single-use JWT
            │                                             │    claims: jti, exp (60s),
            │                                             │    allowed_actions, limit_inr
            │◄─── 3. Return signed JWT ───────────────────┤
            │                                             │
            ├──── 4. Connect with Header: ───────────────►│
            │     "X-UnClone-Credential: <jwt>"           │
            │                                             │ 5. verify_handshake()
            │                                             │    - Cryptographic signature
            │                                             │    - Expiry check (freshness)
            │                                             │    - Single-use JTI check
            │                                             │      in SQLite audit registry
            │                                             │    - Scope & financial limit
            │                                             │
            │◄─── 6. Handshake Approved / 403 ────────────┤
```

#### Downstream Integration with LiveKit, Pipecat, and Bolna:
- **LiveKit ([`LiveKitUnCloneGateAdapter`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L514-L581))**: Upon `APPROVE`, the gate injects `verified_credential` into `room.local_participant.metadata["unclone_credential"]`. Downstream agents verify this before invoking financial execution tools.
- **Pipecat ([`PipecatUnCloneGateProcessor`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L583-L646))**: Frames pass through `UnCloneGateProcessor`. If a clone is detected, an `EndTaskFrame` terminates the pipeline before speech synthesis or LLM runs.
- **Bolna ([`BolnaTelephonyGateBridge`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L648-L697))**: Acts as an inline reverse proxy, routing authenticated calls to `ws://bolna-agent/chat/v1/{agent_id}` with bearer credentials while terminating unverified callers.

### 2. Pan-India Multilingual Voice Pipeline via Bhashini
India's BFSI infrastructure requires support for linguistic diversity across regional dialects. UnClone Gate incorporates the Government of India's **Bhashini (National Language Translation Mission / ULCA)** architecture:

```
 Caller Audio (8kHz mu-law) 
         │
         ▼
 Bhashini ASR (ASR Engine: Hindi / Kannada / Tamil)
         │  - Acoustic dialect normalization
         │  - Telephony noise suppression
         ▼
 Intent Extraction & Semantic Analysis (NVIDIA Nemotron-70B)
         │  - Validates requested banking intent in English / Vernacular
         ▼
 Bhashini TTS (TTS Engine: hi-IN, kn-IN)
         │  - High-fidelity Indic voice synthesis for IVR prompts
         ▼
 Output Stream to Telephony Bridge (8kHz G.711 mu-law)
```

#### Indic Challenge Prompts:
- **Hindi (`hi-IN`)**:
  > *"सीता रामचन्द्रन जी, बैंक सुरक्षा सत्यापन के लिए कृपया कोड 47 दोहराएं: 'वाराणसी के मंदिर में आरती का समय हो गया है'।"*
- **Kannada (`kn-IN`)**:
  > *"ಸೀತಾ ರಾಮಚಂದ್ರನ್ ಅವರೇ, ಬ್ಯಾಂಕ್ ಭದ್ರತಾ ಪರಿಶೀಲನೆಗಾಗಿ ದಯವಿಟ್ಟು ಕೋಡ್ 82 ಹೇಳಿ: 'ಕಾವೇರಿ ನದಿಯು ಕರ್ನಾಟಕದ ಜೀವ ನದಿಯಾಗಿದೆ'।"*

#### Dialectic Biometric Normalization:
Regional phonetic traits (retroflex consonants, vowel elongation, tone accents) can skew standard European-trained acoustic models. The UnClone Gate calibrates DetectifAI Aletheia and Eidos thresholds specifically for Indic speech samples:
- `SYNTH_HIGH`: Adjusted to **0.50** to prevent false positives on expressive Dravidian pitch contours.
- `MATCH_HIGH`: Set to **0.85** on 16kHz resampled phone audio to accommodate regional accent variations.

### 3. Live Demo Polish & Presentation Choreography (16:00 – 17:00)

The live presentation demonstrates three contrasting customer scenarios on the live Grok UI dashboard:

```
========================================================================================================================
 DEMO SCENARIO             AUDIO INPUT               GATE BEHAVIOR & METRICS                     BUSINESS OUTCOME
========================================================================================================================
 Scenario 1:               Senior Citizen Sita       • 8kHz G.711 stream buffered (1.5s)         • Fund transfer approved
 Legitimate Senior         Ramachandran speaking     • Aletheia: Synth = 0.04 (Natural)          • ₹50,000 sent securely
 Customer (English/Kannada) naturally on phone       • Eidos: Match = 0.92 (Enrolled Sita)       • Latency: 320ms (Human)
                                                     • Decision: APPROVE                         • JWT credential minted
------------------------------------------------------------------------------------------------------------------------
 Scenario 2:               AI Voice Clone Attack     • 8kHz G.711 stream buffered (1.5s)         • Call cut in < 1.5s
 Fraud Syndicate Cloned    (ElevenLabs / XTTS clone  • Aletheia: Synth = 0.91 (Synthetic)        • Tool HARD-LOCKED
 Voiceprint of Sita        trained on 3s sample)     • Eidos: Match = 0.89 (Matches Sita)        • ₹20 token cost saved
                                                     • Decision: BLOCK_ALERT                     • Fraud Ops alerted
------------------------------------------------------------------------------------------------------------------------
 Scenario 3:               Impostor with Live RVC    • Dynamic Kannada challenge issued          • Prompt failed
 Real-Time Neural Voice    (Real-time voice changer  • Response Latency Δt = 1,120ms (> 800ms)   • Diverted to 4-digit
 Changer (Active Challenge) running on microphone)   • Anomaly: RVC Latency Buffer detected      • IVR PIN or Senior
                                                     • Decision: STEP_UP / BLOCK_ALERT           • Branch Representative
========================================================================================================================
```

---

## Hour-by-Hour Execution Timetable (Saturday 08:00 – 17:00)

| Time Window | Sub-Phase | Engineering Focus | Primary Files & Artifacts | Exit Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **08:00 – 08:45** | 1.1 | Telephony Audio Codec validation | [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L82-L146) | Bit-exact G.711 mu-law decoding; pure Python LUT benchmark |
| **08:45 – 09:30** | 1.2 | Sliding window ring-buffer tuning | [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L162-L215) | Buffer precisely triggers at 75 chunks ($1.50\text{s}$); drains cleanly |
| **09:30 – 10:15** | 1.3 | 8kHz to 16kHz linear resampling | [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L128-L146) | Resampled WAV headers match RIFF/16kHz/16-bit specs |
| **10:15 – 11:00** | 1.4 | WebSocket media stream integration | [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L843-L914) | Twilio WS simulator receives chunks; unit test suite passes |
| **11:00 – 11:45** | 2.1 | Dynamic challenge phrase generation | [`backend/agent.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/agent.py), [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py) | Dynamic nonce and phonetic phrases generated via Nemotron-70B |
| **11:45 – 12:30** | 2.2 | Latency timing buffer & mark events | [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L474-L480) | High-precision timing delta ($\Delta t$) calculated accurately |
| **12:30 – 13:15** | 2.3 | >800ms RVC anomaly detection | [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py) | Test cases trigger anomaly flag on artificial $>800\text{ms}$ delay |
| **13:15 – 14:00** | 2.4 | Secondary DetectifAI re-scoring | [`backend/gate.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/gate.py), [`backend/detectif_client.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/detectif_client.py) | Rescored audio updates session state to `APPROVE` or `BLOCK` |
| **14:00 – 14:45** | 3.1 | Single-use JWT agent credential | [`backend/credentials.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/credentials.py) | Cryptographic signature, expiration, and replay protection validated |
| **14:45 – 15:30** | 3.2 | Downstream voice agent handoff | [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py#L514-L697) | LiveKit, Pipecat, and Bolna adapters receive `X-UnClone-Credential` |
| **15:30 – 16:15** | 3.3 | Bhashini Indic voice pipeline | [`backend/telephony_bridge.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/telephony_bridge.py), [`backend/agent.py`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Backend/backend/agent.py) | Hindi and Kannada prompts generated, synthesized, and verified |
| **16:15 – 17:00** | 3.4 | Live demo polish & telemetry sync | [`Frontend/`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Frontend/), [`new_frontend_grok/`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/new_frontend_grok/) | UI dashboard reflects live gate status, waveform, and ₹ saved counter |

---

## Technical Invariants & Security Posture

1. **Fail-Closed Principle**:
   - If DetectifAI endpoints time out, return an HTTP error, or receive malformed audio packets, the deterministic engine strictly outputs `BLOCK` or `STEP_UP`.
   - Under no circumstances does the system default to open/authorized.
2. **Zero LLM Policy Authority**:
   - NVIDIA Nemotron-70B handles conversational dialogue, explanation, and intent parsing **only after** identity is verified.
   - The LLM has zero authority to allow, override, or relax biometric gate security decisions.
3. **Replay-Proof Cryptographic Tokens**:
   - Every issued agent credential contains a unique `jti` (UUIDv4) and an expiry timestamp ($TTL \le 60\text{s}$).
   - Attempting to reuse an existing `jti` triggers an immediate security alert and handshake rejection.
4. **Economic Denial of Service Mitigation**:
   - Telephony calls flagged as synthetic clones are severed via Twilio `<Hangup>` or SIP `BYE` within the first **1.5 seconds**.
   - This bypasses all downstream LLM token generation and TTS audio synthesis, preserving cloud GPU compute and saving **₹10–₹20 per call**.

---

## Summary & Verification Protocol

To verify the complete telephony bridge and test suite on Saturday morning:

```powershell
# 1. Run Telephony Bridge Automated Unit Tests (Python 3.12)
& "C:\Users\chandan.s\AppData\Local\Programs\Python\Python312\python.exe" -m unittest tests/test_telephony_bridge.py

# 2. Run Core Contract & Gate Policy Tests
& "C:\Users\chandan.s\AppData\Local\Programs\Python\Python312\python.exe" -m unittest tests/test_contract.py

# 3. Start UnClone Telephony Gateway Server
& "C:\Users\chandan.s\AppData\Local\Programs\Python\Python312\python.exe" run_server.py
```

*This roadmap provides the definitive engineering specification for Track 3: UNCLONE Agents, directly operationalizing the Saturday execution plan from Slide 5.*
