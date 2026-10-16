# 🌾 GramPay (BharatVoice Shield)
### Track 3: UNCLONE Agents — BMSCE AI Hackathon 2026
**Zero-Trust Voice Security & Cost-Optimization Gateway for NPCI Hello! UPI, 123Pay & BFSI Conversational Voice Agents**

[![DetectifAI](https://img.shields.io/badge/DetectifAI-Aletheia%20%2B%20Eidos-00C853?style=flat&logo=shield)](https://platform.detectif.ai)
[![NVIDIA](https://img.shields.io/badge/NVIDIA-Nemotron--3.5-76B900?style=flat&logo=nvidia)](https://integrate.api.nvidia.com)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%28Python%203.12%29-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Vercel](https://img.shields.io/badge/Deploy-Vercel-black?style=flat&logo=vercel)](https://vercel.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 💡 The Core Problem
Over 500 million Indian citizens—predominantly rural farmers and senior citizens—use **NPCI Hello! UPI** and **UPI 123Pay** on cellular voice lines to pay for agricultural supplies or receive DBT subsidies. 
Fraudsters harvest 3-second WhatsApp voice notes to synthesize real-time voice clones (XTTS, ElevenLabs, RVC), tricking automated banking voice agents and draining accounts. Furthermore, conversational voice agents burn expensive LLM tokens (₹10–₹20 per call) before authenticating the caller.

## 🛡️ The GramPay Solution
**GramPay (BharatVoice Shield)** is an inline zero-trust gateway sitting between PSTN/VoIP phone networks and downstream banking AI voice agents:
1. **Zero-Trust Audio Pre-Gating**: Biometric acoustic liveness screening executes **BEFORE** any LLM reasoning or bank tool execution. All banking tools remain **HARD-LOCKED** until voice liveness is mathematically proven.
2. **Dual-Engine DetectifAI OpenAPI v1 Integration**:
   - **Aletheia (`/v1/deepfake/detect`)**: Evaluates synthetic vocoder artifacts (`threshold = 0.62`).
   - **Eidos (`/v1/speakers/verify`)**: Confirms 1-to-1 acoustic voiceprint match (`threshold = 0.53`).
3. **Stage B Dynamic Cognitive Active Challenge (Tier 2)**:
   - For noisy 8kHz cellular audio, **NVIDIA Nemotron-3.5** generates dynamic, unpredictable 4-word recitation phrases (*"Green monsoon lotus peacock"*).
   - Real-time neural voice changers incur buffering delays (`>800ms`), catching attackers with zero user friction.
4. **Agent Cost Optimization**: Terminating clone attacks in under 300ms deflects malicious calls before LLM invocation, saving ~120s of compute and ₹20.00 per deflected attack.
5. **Cryptographic Single-Use Agent Handshake**: Mutual authentication using expiring single-use JWT credentials with replay attack rejection.

---

## ⚡ Quick Start

### 1. Clone & Set Up Backend
```bash
git clone https://github.com/sujay2520/GramPay-BharatVoiceShield.git
cd GramPay-BharatVoiceShield/Backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python run_server.py
```
Open [http://localhost:8000](http://localhost:8000) to access the gateway and user interface.

### 2. Run Test Suite
```bash
python -m unittest discover tests
# Ran 170 tests in 34.134s, OK
```

### 3. Run Automated Telephony Attack Demo
```bash
python scripts/demo_telephony_voice_attack.py
```

---

## 📊 Live System Architecture
```
                     [ Rural Citizen / Voice Telephony ]
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │    FastAPI Gateway (:8000)   │
                      └──────────────┬───────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
  ┌───────────────────────────────┐       ┌───────────────────────────────┐
  │ DetectifAI Aletheia Engine    │       │ DetectifAI Eidos Engine       │
  │ /v1/deepfake/detect           │       │ /v1/speakers/verify           │
  │ (Synthetic Score vs 0.62)     │       │ (Similarity Score vs 0.53)    │
  └──────────────┬────────────────┘       └───────────────┬───────────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     ▼
                      ┌──────────────────────────────┐
                      │ gate.py (Deterministic Gate) │
                      └──────────────┬───────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
[ Tier 1: Low Risk ]      [ Tier 2: Medium Risk ]      [ Tier 3: High Risk ]
   APPROVE / PAY            STEP_UP / Challenge           BLOCK_ALERT
Tool Unlocked & Executed   NVIDIA Nemotron Phrase      Tool LOCKED · ₹20 Saved
```

---

## 🧪 Google Colab Benchmark
The complete evaluation benchmark notebook is available at:
**[Google Colab Benchmark Notebook](https://colab.research.google.com/drive/1iso7n6nMzd4tJG3nnCDE8KYjksNSCi5e)**
Includes 16 automated cells testing synthetic vocoder detection, speaker verification, and BFSI call-center cost deflection models (10,000, 50,000, and 100,000 calls).

---

## 🚀 Vercel Deployment

GramPay's frontend is optimized for zero-configuration, zero-downtime deployment on **Vercel**:

### Option A: Import Entire Repository (Root Directory = `.`)
1. Import repository into Vercel.
2. Leave **Root Directory** as `./` (or default).
3. The root [`vercel.json`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/vercel.json) automatically configures clean URLs, routes `/(farmer|judge|split)` to `index.html`, and serves all static assets from `Frontend/`.

### Option B: Deploy Frontend Directory (Root Directory = `Frontend`)
1. In Vercel Project Settings, set **Root Directory** to `Frontend`.
2. [`Frontend/vercel.json`](file:///c:/Users/chandan.s/OneDrive/Desktop/Unclone/Frontend/vercel.json) handles clean URLs, view routes, and audio caching.

### Connecting to Live Backend Gateway:
- **URL Parameter**: Open `https://<your-app>.vercel.app/?backend=https://your-backend.railway.app`
- **UI Configuration**: Click the **DetectifAI Status Badge** in the header or switch to the **Judge Console** to enter your backend URL and click **Save**.
- **Vercel Reverse Proxy**: For same-origin `/api` routing, add a rewrite in `vercel.json`:
  ```json
  { "source": "/api/(.*)", "destination": "https://your-backend.railway.app/api/$1" }
  ```
- **Offline / Demonstration Mode**: The demo quick-test scenarios include offline simulation fallbacks so the biometric telemetry and live audio scenarios display seamlessly even if the backend is momentarily disconnected.

---

## 📄 License & Attribution
Developed for the **BMSCE AI Hackathon 2026 (Track 3: UNCLONE Agents)**. Powered by DetectifAI and NVIDIA Nemotron.

