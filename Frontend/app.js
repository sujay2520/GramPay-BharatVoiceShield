/**
 * GramPay local voice identity and synthetic-audio check UI.
 * Uses the same localhost origin as the local API server.
 * - Health Check & Live Credits: /api/health, /api/credits
 * - Voice Gate Check: /api/check
 * - Voice Enrollment: /api/enroll (with >= 15s timer support)
 * - Tier-2 Active Challenge: /api/challenge/generate & /api/challenge/verify with response latency timer
 * - Full Voice Agent Turn: /api/agent/turn (STT -> LLM with NVIDIA Nemotron)
 * - Hello! UPI Payment Tool Execution: /api/pay/upi
 * - Verified Bank Agent Handshake: /api/credential/issue & /api/handshake/verify with replay prevention
 * - Slide 4 Official Live Counters: /api/stats (checks_run, clones_blocked, agent_steps_skipped, agent_time_saved_inr)
 * - Live Audit Log Table: /api/audit?limit=30 with auto & manual refresh
 */

// ========== 1. LOCAL GATEWAY ORIGIN ==========
function resolveInitialBackendUrl() {
  if (typeof window === "undefined") return "http://127.0.0.1:8000";
  const hostname = window.location.hostname.toLowerCase();
  if (hostname === "localhost" || hostname === "127.0.0.1") return window.location.origin;
  return "";
}

let BACKEND_URL = resolveInitialBackendUrl();

// ========== 2. APPLICATION STATE ==========
let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;
let recordTarget = null;           // 'senior' | 'enroll' | 'challenge'

// Day 2 Multilingual & Multi-Device Contract State
let currentLang = "kn";            // 'kn' (Kannada) | 'hi' (Hindi) | 'en' (English)
const currentDevice = "phone1";    // The caller/farmer phone view
let currentSource = "live_mic";    // 'live_mic' | 'clone_clip'
let lastEventId = null;            // Event sourcing cursor for /api/latest-state

// Audio Blobs
let currentBlob = null;            // Primary voice order audio (recording or file upload)
let enrollBlob = null;             // Enrollment voice sample (recording or file upload)
let challengeAudioBlob = null;     // Tier-2 challenge voice sample

// Speaker Profile
let currentSpeakerId = (() => { try { return localStorage.getItem("unclone_speaker_id") || "Account_holder"; } catch (e) { return "Account_holder"; } })();
let currentSpeakerName = (() => { try { return localStorage.getItem("unclone_speaker_name") || "Account holder"; } catch (e) { return "Account holder"; } })();

// Tier-2 Active Challenge State
let challengeTimerInterval = null;
let challengeStartTime = 0;
let challengeElapsedSeconds = 0;
let currentChallengeId = null;
let challengeCurrentPhrase = [];
let callerChallengeActive = false;

// Senior & Enrollment Recording Timers
let seniorTimerInterval = null;
let seniorRecordStart = 0;
let seniorElapsedSec = 0;

let enrollTimerInterval = null;
let enrollRecordStart = 0;
let enrollElapsedSec = 0;

// Security Credentials State
let lastCredential = null;         // Stored single-use JWT for replay test

// Live telemetry cache. Empty values remain empty until the gateway returns data.
let lastTelemetryStats = {
  checks_run: null,
  clones_blocked: null,
  agent_steps_skipped: null,
  agent_seconds_avoided: null,
  agent_time_saved_inr: null,
  rate_per_min: null
};

// ========== 3. DOM SELECTOR HELPER ==========
const $ = (id) => {
  const el = document.getElementById(id);
  if (el) return el;
  return null;
};

// ========== 3B. SENIOR VOICE ASSISTANT (WEB SPEECH SYNTHESIS TTS) ==========
const TTS_PHRASES = {
  approved: {
    kn: "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಯಶಸ್ವಿಯಾಗಿದೆ.",
    hi: "आवाज़ की जाँच सफल हुई।",
    en: "Voice check passed."
  },
  blocked: {
    kn: "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಪೂರ್ಣಗೊಳ್ಳಲಿಲ್ಲ. ಮುಂದಿನ ಕ್ರಮ ಅನುಮೋದಿಸಲ್ಪಟ್ಟಿಲ್ಲ.",
    hi: "आवाज़ की जाँच पूरी नहीं हुई। आगे की कार्रवाई स्वीकृत नहीं हुई।",
    en: "Voice check could not be completed. No downstream action was approved."
  }
};

const TTS_LANG_TAGS = {
  kn: "kn-IN",
  hi: "hi-IN",
  en: "en-IN"
};

let lastSpokenVerdict = null;
let lastSpokenTime = 0;

/**
 * Web Speech Synthesis (TTS) Voice Assistant for Rural & Senior Citizens:
 * Automatically speaks native language confirmations aloud when payments are approved
 * or synthetic clone attacks are blocked.
 */
function speakVoiceAssistant(verdict, force = false) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    console.warn("Web Speech Synthesis (TTS) is not supported in this browser environment.");
    return;
  }

  const normVerdict = String(verdict || "").toUpperCase();
  let type = null;
  if (normVerdict === "APPROVE" || normVerdict === "APPROVED") {
    type = "approved";
  } else if (
    normVerdict === "BLOCK" ||
    normVerdict === "BLOCK_ALERT" ||
    normVerdict === "BLOCKED" ||
    normVerdict === "FAIL" ||
    normVerdict === "FAILED"
  ) {
    type = "blocked";
  }

  if (!type) return;

  const now = Date.now();
  if (!force && lastSpokenVerdict === type && (now - lastSpokenTime < 1500)) {
    return;
  }
  lastSpokenVerdict = type;
  lastSpokenTime = now;

  const langKey = (currentLang || "kn").toLowerCase();
  const phraseConfig = TTS_PHRASES[type];
  const phrase = (phraseConfig && phraseConfig[langKey]) || (phraseConfig && phraseConfig.en);
  const langTag = TTS_LANG_TAGS[langKey] || "en-IN";

  if (!phrase) return;

  try {
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(phrase);
    utterance.lang = langTag;
    utterance.rate = 0.95; // Clear, comfortable tempo for rural seniors
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    if (voices && voices.length > 0) {
      const match = voices.find(v => v.lang === langTag)
        || voices.find(v => v.lang && v.lang.toLowerCase().replace(/_/g, "-") === langTag.toLowerCase())
        || voices.find(v => v.lang && v.lang.toLowerCase().startsWith(langKey));
      if (match) utterance.voice = match;
    }

    // Keep window reference to avoid garbage collection drop in Chrome
    window._activeUtterance = utterance;
    utterance.onend = () => { window._activeUtterance = null; };
    utterance.onerror = (e) => {
      console.warn("TTS utterance error:", e);
      window._activeUtterance = null;
    };

    window.speechSynthesis.speak(utterance);
  } catch (err) {
    console.warn("Web Speech Synthesis playback error:", err);
  }
}

// Pre-load voices on browser voice list change
if (typeof window !== "undefined" && "speechSynthesis" in window) {
  window.speechSynthesis.onvoiceschanged = () => {
    try { window.speechSynthesis.getVoices(); } catch (e) {}
  };
}

window.speakVoiceAssistant = speakVoiceAssistant;

// ========== 4. UI OVERLAY & FEEDBACK HELPERS ==========
function showOverlay(text = "Working…") {
  const overlay = $("overlay");
  const overlayText = $("overlayText");
  if (overlayText) overlayText.textContent = text;
  if (overlay) {
    overlay.classList.remove("hidden");
    overlay.classList.add("flex");
  }
}

function hideOverlay() {
  const overlay = $("overlay");
  if (overlay) {
    overlay.classList.add("hidden");
    overlay.classList.remove("flex");
  }
}

/**
 * Updates Big Status Card on the Senior Farmer View
 * Displays large, high-contrast, visually unmistakable indicators (Approved / Blocked / Step-Up).
 * Automatically triggers Web Speech Synthesis (TTS) in the citizen's native language.
 */
function setStatusCard(decision, reason) {
  const card = $("statusCard");
  const emoji = $("statusEmoji");
  const title = $("statusTitle");
  const reasonEl = $("statusReason");
  const tier2Prompt = $("tier2PromptAction");

  if (!card) return;

  card.classList.remove("status-approve", "status-block", "status-stepup", "status-ready");

  const lang = (currentLang || "kn").toLowerCase();

  if (!decision) {
    card.classList.add("status-ready");
    if (emoji) {
      emoji.textContent = "🛡️";
      emoji.className = "mx-auto mb-3 flex size-24 items-center justify-center rounded-full bg-paper/95 border-2 border-line text-ink shadow-md text-6xl";
    }
    if (title) {
      if (lang === "kn") {
        title.textContent = "ಧ್ವನಿ ಪರಿಶೀಲನೆ / VOICE CHECK";
      } else if (lang === "hi") {
        title.textContent = "आवाज़ की जाँच / VOICE CHECK";
      } else {
        title.textContent = "Tap to check your voice";
      }
      title.className = "font-display text-2xl sm:text-3xl md:text-4xl font-extrabold leading-tight uppercase";
    }
    if (reasonEl) {
      const cfg = (typeof window !== "undefined" && window.LANGUAGES && window.LANGUAGES[lang]) || null;
      reasonEl.textContent = reason || (lang === "kn" ? "ದೊಡ್ಡ ಗುಂಡಿಯನ್ನು ಒತ್ತಿ ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ." : (lang === "hi" ? "बटन दबाकर स्पष्ट रूप से बोलें।" : "Tap the microphone and speak clearly."));
      reasonEl.className = "mx-auto mt-2 max-w-xl text-lg sm:text-xl leading-relaxed text-muted font-medium";
    }
    if (tier2Prompt) tier2Prompt.classList.add("hidden");
    return;
  }

  const d = String(decision).toUpperCase();
  if (d === "APPROVE" || d === "APPROVED") {
    card.classList.add("status-approve");
    if (emoji) {
      emoji.textContent = "✅";
      emoji.className = "mx-auto mb-3 flex size-24 sm:size-28 items-center justify-center rounded-full bg-emerald-700 border-4 border-emerald-400 text-white shadow-2xl text-6xl md:text-7xl transition-transform duration-300 scale-105";
    }
    if (title) {
      if (lang === "kn") {
        title.textContent = "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಯಶಸ್ವಿಯಾಗಿದೆ";
      } else if (lang === "hi") {
        title.textContent = "आवाज़ की जाँच सफल हुई";
      } else {
        title.textContent = "Voice Check Passed";
      }
      title.className = "font-display text-2xl sm:text-3xl md:text-4xl font-extrabold leading-tight text-white tracking-tight";
    }
    if (reasonEl) {
      const defaultDesc = lang === "kn"
        ? "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಯಶಸ್ವಿಯಾಗಿದೆ."
        : (lang === "hi"
          ? "आवाज़ की जाँच सफल हुई।"
          : "The voice check passed.");
      reasonEl.textContent = reason || defaultDesc;
      reasonEl.className = "mx-auto mt-2 max-w-xl text-lg sm:text-xl font-bold text-emerald-100";
    }
    if (tier2Prompt) tier2Prompt.classList.add("hidden");

    // Automatically speak native language confirmation aloud
    speakVoiceAssistant("approved");

  } else if (d === "UNAVAILABLE") {
    card.classList.add("status-block");
    if (emoji) emoji.textContent = "⚠️";
    if (title) {
      title.textContent = "Voice check could not be completed";
      title.className = "font-display text-2xl sm:text-3xl md:text-4xl font-extrabold leading-tight text-white tracking-tight";
    }
    if (reasonEl) {
      const prefix = "No downstream action was approved by this voice check.";
      reasonEl.textContent = reason ? (String(reason).includes(prefix) ? reason : `${prefix} ${reason}`) : prefix;
      reasonEl.className = "mx-auto mt-2 max-w-xl text-lg sm:text-xl font-bold text-rose-100";
    }
    if (tier2Prompt) tier2Prompt.classList.add("hidden");
  } else if (d === "BLOCK_ALERT" || d === "BLOCK" || d === "BLOCKED") {
    card.classList.add("status-block");
    if (emoji) {
      emoji.textContent = "🛑";
      emoji.className = "mx-auto mb-3 flex size-24 sm:size-28 items-center justify-center rounded-full bg-rose-800 border-4 border-rose-400 text-white shadow-2xl text-6xl md:text-7xl transition-transform duration-300 animate-pulse";
    }
    if (title) {
      if (lang === "kn") {
        title.textContent = "ಧ್ವನಿ ಪರಿಶೀಲನೆ ತಡೆಯಲಾಗಿದೆ";
      } else if (lang === "hi") {
        title.textContent = "आवाज़ की जाँच रोक दी गई";
      } else {
        title.textContent = "Voice check blocked";
      }
      title.className = "font-display text-2xl sm:text-3xl md:text-4xl font-extrabold leading-tight text-white tracking-tight";
    }
    if (reasonEl) {
      const defaultDesc = lang === "kn"
        ? "ಸಂಶ್ಲೇಷಿತ ಧ್ವನಿ ಪತ್ತೆಯಾಗಿದೆ; ಪರಿಶೀಲನೆ ತಡೆಯಲಾಗಿದೆ."
        : (lang === "hi"
          ? "सिंथेटिक आवाज़ मिली; जाँच रोक दी गई।"
          : "Synthetic voice detected; the check was blocked.");
      reasonEl.textContent = reason || defaultDesc;
      reasonEl.className = "mx-auto mt-2 max-w-xl text-lg sm:text-xl font-bold text-rose-100";
    }
    if (tier2Prompt) tier2Prompt.classList.add("hidden");

    // Automatically speak native language warning aloud
    speakVoiceAssistant("blocked");

  } else if (d === "STEP_UP" || d === "EXTRA_CHECK") {
    card.classList.add("status-stepup");
    if (emoji) {
      emoji.textContent = "⚡";
      emoji.className = "mx-auto mb-3 flex size-20 sm:size-24 items-center justify-center rounded-full bg-wait-bg border-3 border-wait text-wait shadow-xl text-5xl md:text-6xl transition-transform duration-300";
    }
    if (title) {
      if (lang === "kn") {
        title.textContent = "ಹೆಚ್ಚುವರಿ ಧ್ವನಿ ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿದೆ (Tier-2 Challenge)";
      } else if (lang === "hi") {
        title.textContent = "अतिरिक्त सुरक्षा जाँच आवश्यक (Tier-2 Challenge)";
      } else {
        title.textContent = "Step-Up Required · Tier-2 Active Challenge";
      }
      title.className = "font-display text-2xl sm:text-3xl font-bold leading-tight";
    }
    if (reasonEl) {
      const defaultDesc = lang === "kn"
        ? "ಮತ್ತೊಂದು ಧ್ವನಿ ಮಾದರಿ ಅಗತ್ಯವಿದೆ. ಮೈಕ್ ಒತ್ತಿ ಸಹಜವಾಗಿ ಮಾತನಾಡಿ."
        : (lang === "hi"
          ? "एक और आवाज़ का नमूना चाहिए। माइक दबाकर स्वाभाविक रूप से बोलें।"
          : "Another voice sample is needed. Tap the mic and speak naturally.");
      reasonEl.textContent = reason || defaultDesc;
      reasonEl.className = "mx-auto mt-2 max-w-xl text-base sm:text-lg font-medium text-wait";
    }
    if (tier2Prompt) tier2Prompt.classList.remove("hidden");

    // Highlight Tier-2 Challenge Box
    const box = $("tier2Box");
    if (box) {
      box.classList.add("ring-4", "ring-wait", "ring-offset-2");
      setTimeout(() => {
        box.classList.remove("ring-4", "ring-wait", "ring-offset-2");
      }, 3500);
    }
  } else {
    card.classList.add("status-ready");
    if (emoji) {
      emoji.textContent = "ℹ️";
      emoji.className = "mx-auto mb-3 flex size-16 items-center justify-center rounded-full bg-paper/90 border border-line text-ink shadow-sm text-3xl";
    }
    if (title) {
      title.textContent = decision;
      title.className = "font-display text-2xl md:text-3xl font-bold leading-tight uppercase";
    }
    if (tier2Prompt) tier2Prompt.classList.add("hidden");
    if (reasonEl) reasonEl.textContent = reason || "";
  }

  // Also sync with #callerStatusCard in caller phone view & virtual phone
  const cCard = $("callerStatusCard");
  const cEmoji = $("callerStatusEmoji");
  const cTitle = $("callerStatusTitle");
  const cReason = $("callerStatusReason");
  const cBox = $("callerChallengeBox");
  if (cCard) {
    cCard.classList.remove("status-approve", "status-block", "status-stepup", "status-ready");
    if (!decision) {
      cCard.classList.add("status-ready");
      if (cEmoji) cEmoji.textContent = "🛡️";
      if (cTitle) cTitle.textContent = lang === "kn" ? "ಧ್ವನಿ ಪರಿಶೀಲನೆ" : (lang === "hi" ? "आवाज़ की जाँच" : "Voice check");
      if (cReason) cReason.textContent = reason || (lang === "kn" ? "ಮಾತನಾಡಲು ಮೈಕ್ ಒತ್ತಿ; ನಿಲ್ಲಿಸಲು ಮತ್ತೆ ಒತ್ತಿ." : (lang === "hi" ? "बोलने के लिए माइक दबाएँ; रोकने के लिए फिर दबाएँ।" : "Tap the mic to speak; tap again to stop and check."));
      if (cBox) cBox.classList.add("hidden");
    } else if (d === "APPROVE" || d === "APPROVED" || d === "PAY") {
      cCard.classList.add("status-approve");
      if (cEmoji) cEmoji.textContent = "✅";
      if (cTitle) cTitle.textContent = lang === "kn" ? "✅ ಧ್ವನಿ ಪರಿಶೀಲನೆ ಯಶಸ್ವಿಯಾಗಿದೆ" : (lang === "hi" ? "✅ आवाज़ की जाँच सफल हुई" : "✅ Voice check passed");
      if (cReason) cReason.textContent = reason || (lang === "kn" ? "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಯಶಸ್ವಿ. ಯಾವುದೇ ಪಾವತಿ ಮಾಡಲಾಗಿಲ್ಲ." : (lang === "hi" ? "आवाज़ की जाँच सफल हुई। कोई भुगतान नहीं किया गया।" : "Voice check passed. No payment was made."));
      if (cBox) cBox.classList.add("hidden");
    } else if (d === "UNAVAILABLE") {
      cCard.classList.add("status-block");
      if (cEmoji) cEmoji.textContent = "⚠️";
      if (cTitle) cTitle.textContent = "Voice check could not be completed";
      if (cReason) {
        const prefix = "No downstream action was approved by this voice check.";
        cReason.textContent = reason ? (String(reason).includes(prefix) ? reason : `${prefix} ${reason}`) : prefix;
      }
      if (cBox) cBox.classList.add("hidden");
    } else if (d === "BLOCK_ALERT" || d === "BLOCK" || d === "BLOCKED") {
      cCard.classList.add("status-block");
      if (cEmoji) cEmoji.textContent = "🛑";
      if (cTitle) cTitle.textContent = lang === "kn" ? "🛑 ಎಚ್ಚರಿಕೆ! ನಕಲಿ (AI) ಧ್ವನಿ ಪತ್ತೆಯಾಗಿದೆ" : (lang === "hi" ? "🛑 सावधान! नकली (AI) आवाज़ पकड़ी गई" : "🛑 Alert! AI Voice Clone Attempt Blocked");
      if (cReason) cReason.textContent = reason || (lang === "kn" ? "ಧ್ವನಿ ಪರಿಶೀಲನೆ ವಿಫಲವಾಗಿದೆ; ಮುಂದಿನ ಕ್ರಮ ಕೈಗೊಳ್ಳಲಿಲ್ಲ." : (lang === "hi" ? "आवाज़ की जाँच विफल हुई; आगे की कार्रवाई नहीं हुई।" : "Voice check failed; no downstream action was taken."));
      if (cBox) cBox.classList.add("hidden");
    } else if (d === "STEP_UP" || d === "EXTRA_CHECK") {
      cCard.classList.add("status-stepup");
      if (cEmoji) cEmoji.textContent = "⚡";
      if (cTitle) cTitle.textContent = lang === "kn" ? "ಹೆಚ್ಚುವರಿ ಧ್ವನಿ ಪರಿಶೀಲನೆ (Tier-2 Challenge)" : (lang === "hi" ? "अतिरिक्त सुरक्षा जाँच (Tier-2 Challenge)" : "Extra Voice Check Required");
      if (cReason) cReason.textContent = lang === "kn" ? "ಮತ್ತೊಂದು ಧ್ವನಿ ಮಾದರಿ ಅಗತ್ಯವಿದೆ. ಮೈಕ್ ಒತ್ತಿ ಸಹಜವಾಗಿ ಮಾತನಾಡಿ." : (lang === "hi" ? "एक और आवाज़ का नमूना चाहिए। माइक दबाकर स्वाभाविक रूप से बोलें।" : "Another voice sample is needed. Tap the mic and speak naturally.");
      if (cBox) cBox.classList.add("hidden");
    }
  }
}

/**
 * Updates Header Connection & DetectifAI Status Badge
 */
function setHealthBadge(ok, detectifReachable, details) {
  const badge = $("healthBadge");
  const dot = $("healthDot");
  const text = $("healthText");
  if (!badge) return;

  badge.classList.remove("health-ok", "health-fail", "health-unknown");
  if (ok === true && detectifReachable === true) {
    badge.classList.add("health-ok");
    if (dot) dot.innerHTML = '<span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-safe"></span>';
    if (text) text.textContent = "DetectifAI reachable";
    badge.title = `Local gateway and DetectifAI are reachable${BACKEND_URL ? ` (${BACKEND_URL})` : ""}.`;
    return;
  }

  badge.classList.add("health-fail");
  if (dot) dot.innerHTML = '<span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-alert"></span>';
  const message = ok === false ? "DetectifAI unavailable" : "Gateway unavailable";
  if (text) text.textContent = message;
  const detailText = details?.reason || details?.error || "Check the local API and provider connection.";
  badge.title = `${message}: ${detailText}`;
}

/**
 * Updates Biometric Gauges and Latency Breakdown
 */
function updateGauges(detection, verification) {
  const synth = detection?.synthetic_score;
  const match = verification?.match_score;
  const detMs = detection?.latency_ms;
  const verMs = verification?.latency_ms;

  // Synthetic Vocoder Gauge
  if (typeof synth === "number") {
    const pct = Math.min(100, Math.max(0, synth * 100));
    if ($("gaugeSynthVal")) $("gaugeSynthVal").textContent = pct.toFixed(1) + "%";
    if ($("gaugeSynthBar")) {
      $("gaugeSynthBar").style.width = pct + "%";
      $("gaugeSynthBar").className = "h-full transition-all duration-500 " +
        (synth >= 0.62 ? "bg-red-500" : synth >= 0.20 ? "bg-amber-500" : "bg-emerald-500");
    }
  } else {
    if ($("gaugeSynthVal")) $("gaugeSynthVal").textContent = "—";
    if ($("gaugeSynthBar")) $("gaugeSynthBar").style.width = "0%";
  }

  // Speaker Biometric Match Gauge
  if (typeof match === "number") {
    const pct = Math.min(100, Math.max(0, match * 100));
    if ($("gaugeMatchVal")) $("gaugeMatchVal").textContent = pct.toFixed(1) + "%";
    if ($("gaugeMatchBar")) {
      $("gaugeMatchBar").style.width = pct + "%";
      $("gaugeMatchBar").className = "h-full transition-all duration-500 " +
        (match >= 0.53 ? "bg-cyan-500" : match >= 0.40 ? "bg-amber-500" : "bg-red-500");
    }
  } else {
    if ($("gaugeMatchVal")) $("gaugeMatchVal").textContent = "—";
    if ($("gaugeMatchBar")) $("gaugeMatchBar").style.width = "0%";
  }

  // Latency Breakdown
  const detVal = (typeof detMs === "number" && detMs > 0) ? detMs : 0;
  const verVal = (typeof verMs === "number" && verMs > 0) ? verMs : 0;
  const totalMs = detVal + verVal;

  if ($("metricLatency")) {
    $("metricLatency").textContent = (detMs != null && verMs != null)
      ? `Aletheia: ${detMs}ms | Eidos: ${verMs}ms`
      : "— / — ms";
  }

  if ($("latencyTotalText")) {
    $("latencyTotalText").textContent = totalMs > 0 ? `Total: ${totalMs.toFixed(0)} ms` : "Total: — ms";
  }

  if ($("latencyDetBar") && $("latencyVerBar")) {
    if (totalMs > 0) {
      const detPct = Math.min(100, (detVal / totalMs) * 100);
      const verPct = 100 - detPct;
      $("latencyDetBar").style.width = detPct + "%";
      $("latencyVerBar").style.width = verPct + "%";
    } else {
      $("latencyDetBar").style.width = "0%";
      $("latencyVerBar").style.width = "0%";
    }
  }
}

/**
 * Backend-reported telemetry counters:
 *  - checks_run
 *  - clones_blocked
 *  - agent_steps_skipped
 *  - agent_time_saved_inr (when provided by the backend)
 */
function updateSlide4Counters(statsData) {
  if (!statsData) return;

  const checks = statsData.checks_run ?? statsData.checks ?? statsData.total_checks ?? lastTelemetryStats.checks_run;
  const blocked = statsData.clones_blocked ?? statsData.blocks ?? statsData.total_blocked ?? lastTelemetryStats.clones_blocked;
  const skipped = statsData.agent_steps_skipped ?? statsData.steps_skipped ?? lastTelemetryStats.agent_steps_skipped;
  const seconds = statsData.agent_seconds_avoided ?? statsData.seconds_avoided ?? lastTelemetryStats.agent_seconds_avoided;

  const inrSaved = statsData.agent_time_saved_inr != null && Number.isFinite(Number(statsData.agent_time_saved_inr))
    ? Number(statsData.agent_time_saved_inr)
    : null;

  lastTelemetryStats = {
    checks_run: checks,
    clones_blocked: blocked,
    agent_steps_skipped: skipped,
    agent_seconds_avoided: seconds,
    agent_time_saved_inr: inrSaved,
    rate_per_min: null
  };

  // Update the 4 Primary Slide 4 Presentation Counters
  if ($("checks_run")) $("checks_run").textContent = checks == null ? "—" : Number(checks).toLocaleString();
  if ($("clones_blocked")) $("clones_blocked").textContent = blocked == null ? "—" : Number(blocked).toLocaleString();
  if ($("agent_steps_skipped")) $("agent_steps_skipped").textContent = skipped == null ? "—" : Number(skipped).toLocaleString();
  if ($("agent_time_saved_inr")) $("agent_time_saved_inr").textContent = inrSaved == null ? "—" : "₹" + inrSaved.toFixed(2);

  // Update secondary metrics
  if ($("costSteps")) $("costSteps").textContent = skipped == null ? "—" : Number(skipped).toLocaleString();
  if ($("costSeconds")) $("costSeconds").textContent = seconds == null ? "—" : Number(seconds).toFixed(0);
  if ($("costInr")) $("costInr").textContent = inrSaved == null ? "—" : "₹" + inrSaved.toFixed(2);
  if ($("costAssumptionText")) $("costAssumptionText").textContent = "Reported by backend";
}

/**
 * Error display with Section 4 deterministic fail-closed state
 */
function showError(msg, failClosed = true) {
  let displayMsg = typeof msg === "object" ? (msg.error || msg.message || JSON.stringify(msg)) : String(msg || "");
  if (displayMsg.includes("Unexpected token") || displayMsg.includes("not valid JSON") || displayMsg.includes("The page c")) {
    displayMsg = "Local gateway is not connected. Start the local server and retry.";
  }
  setStatusCard("UNAVAILABLE", failClosed ? displayMsg : (displayMsg || "The voice check did not finish."));
  if ($("jsonLog")) {
    $("jsonLog").textContent = JSON.stringify({ error: displayMsg, fail_closed: failClosed }, null, 2);
  }
}

// ========== 5. TIER-2 ACTIVE CHALLENGE (NEMOTRON PHRASE & LATENCY TIMER) ==========
function renderPhraseChips() {
  const chipsHtml = challengeCurrentPhrase.map(w => 
    `<span class="px-3.5 py-1.5 bg-amber-950/80 border border-amber-500 text-amber-300 font-bold font-mono rounded-lg text-sm md:text-base shadow-sm">${w}</span>`
  ).join(" ");

  if ($("phraseChips")) $("phraseChips").innerHTML = chipsHtml;
  if ($("modalPhraseChips")) $("modalPhraseChips").innerHTML = chipsHtml;
}

/**
 * Tier-2 Phrase Generator: Queries /api/challenge/new?lang={currentLang} for dynamic 4-word challenge phrase
 */
async function generateChallenge() {
  challengeCurrentPhrase = [];
  currentChallengeId = null;
  try {
    const data = await safeApiFetch(`${BACKEND_URL}/api/challenge/new?lang=${encodeURIComponent(currentLang)}`);
    if (data && Array.isArray(data.words) && data.words.length) {
      currentChallengeId = data.challenge_id || null;
      challengeCurrentPhrase = data.words;
    }
  } catch (e) {
    // Continue to the supported legacy challenge endpoint.
  }

  if (!challengeCurrentPhrase.length) {
    const payload = {
      speaker_id: currentSpeakerId || "Account_holder",
      action: $("actionSelect")?.value || "VOICE_VERIFY",
      amount: parseFloat($("amountInput")?.value || "") || undefined,
      lang: currentLang
    };
    const legacy = await safeApiFetch(`${BACKEND_URL}/api/challenge/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (legacy?.challenge_id && legacy.phrase) {
      currentChallengeId = legacy.challenge_id;
      challengeCurrentPhrase = Array.isArray(legacy.phrase) ? legacy.phrase : String(legacy.phrase).trim().split(/\s+/);
    }
  }

  if (!challengeCurrentPhrase.length) throw new Error("Challenge service returned no phrase.");
  renderPhraseChips();
  resetChallengeTimerUI();
}

function startChallengeTimer() {
  stopChallengeTimer();
  challengeStartTime = performance.now();
  challengeElapsedSeconds = 0;

  challengeTimerInterval = setInterval(() => {
    const elapsed = (performance.now() - challengeStartTime) / 1000;
    challengeElapsedSeconds = elapsed;
    updateChallengeTimerUI(elapsed);
    if ($("callerBtnRecordTimer")) $("callerBtnRecordTimer").textContent = `00:${elapsed < 10 ? "0" : ""}${elapsed.toFixed(1)}s`;

  }, 25);
}

function stopChallengeTimer() {
  if (challengeTimerInterval) {
    clearInterval(challengeTimerInterval);
    challengeTimerInterval = null;
  }
}

function resetChallengeTimerUI() {
  challengeElapsedSeconds = 0;
  updateChallengeTimerUI(0);
  if ($("challengeTimerStatus")) $("challengeTimerStatus").textContent = "Status: Ready to capture phrase";
  if ($("modalTimerStatus")) $("modalTimerStatus").textContent = "Status: Ready to speak phrase";
  const resultEl = $("challengeResult");
  const modalEl = $("modalResult");
  if (resultEl) resultEl.classList.add("hidden");
  if (modalEl) modalEl.classList.add("hidden");
}

function updateChallengeTimerUI(elapsed) {
  const formatted = elapsed.toFixed(2) + " s";
  const pct = Math.min(100, (elapsed / 5.0) * 100);

  // Inline Box UI
  if ($("challengeTimerVal")) $("challengeTimerVal").textContent = formatted;
  if ($("challengeTimerBar")) {
    $("challengeTimerBar").style.width = pct + "%";
    $("challengeTimerBar").className = "h-full transition-all duration-75 bg-gold";
  }

  const latencyFlagText = $("challengeLatencyFlagText");
  if (latencyFlagText) latencyFlagText.textContent = `Elapsed: ${formatted}`;

  // Modal UI
  if ($("modalTimerVal")) $("modalTimerVal").textContent = formatted;
  if ($("modalTimerBar")) {
    $("modalTimerBar").style.width = pct + "%";
    $("modalTimerBar").className = "h-full transition-all duration-75 bg-gold";
  }
  const modalFlag = $("modalLatencyFlag");
  if (modalFlag) {
    modalFlag.className = "font-mono font-bold text-muted";
    modalFlag.textContent = `Elapsed: ${formatted}`;
  }

  const statusText = elapsed > 0
    ? `Capturing vocal phrase… ${formatted}`
    : "Status: Ready to capture phrase";

  if ($("challengeTimerStatus")) $("challengeTimerStatus").textContent = statusText;
  if ($("modalTimerStatus")) $("modalTimerStatus").textContent = statusText;
}

function setChallengeStatus(msg, isError = false) {
  const resultEl = $("challengeResult");
  const modalEl = $("modalResult");

  if (resultEl) {
    resultEl.textContent = msg;
    resultEl.classList.remove("hidden", "text-red-400", "text-emerald-400", "text-amber-400");
    resultEl.classList.add(isError ? "text-red-400" : "text-emerald-400");
  }
  if (modalEl) {
    modalEl.textContent = msg;
    modalEl.classList.remove("hidden", "text-red-400", "text-emerald-400", "text-amber-400");
    modalEl.classList.add(isError ? "text-red-400" : "text-emerald-400");
  }
}

// ========== 6. API CLIENT FUNCTIONS & BULLETPROOF SAFE FETCH ==========

/**
 * Safe fetch & JSON parser (Safeguard against HTML 404/500 pages e.g. Vercel)
 * Never throws raw 'Unexpected token T in JSON' syntax errors.
 */
async function safeApiFetch(url, options = {}) {
  let r;
  const fetchOpts = { ...options };
  fetchOpts.mode = fetchOpts.mode || "cors";
  fetchOpts.headers = { ...(fetchOpts.headers || {}) };

  try {
    r = await fetch(url, fetchOpts);
  } catch (netErr) {
    throw {
      error: `Network error reaching the local gateway: ${netErr.message || "Failed to fetch"}. Check that the local server is running.`,
      status: 0,
      isNetwork: true,
    };
  }

  const contentType = r.headers ? (r.headers.get("content-type") || "") : "";
  let data = null;

  if (contentType.includes("application/json")) {
    try {
      data = await r.json();
    } catch (e) {
      data = { error: "Server returned non-standard JSON response", status: r.status };
    }
  } else {
    // Non-JSON response (e.g. Vercel 404 HTML: "The page could not be found")
    let text = "";
    try {
      text = await r.text();
    } catch (e) {}

    let userMsg = `Gateway returned HTTP ${r.status}`;
    if (r.status === 404) {
      userMsg = "Gateway endpoint not found (HTTP 404). Check backend connection in settings.";
    } else if (r.status === 502 || r.status === 504) {
      userMsg = "Gateway offline or timed out (HTTP 502/504).";
    } else if (text && text.length < 120 && !text.includes("<html") && !text.includes("<!DOCTYPE")) {
      userMsg = text.trim();
    }
    data = { error: userMsg, status: r.status, rawText: text };
  }

  if (!r.ok || data.error) {
    throw data;
  }
  return data;
}

/**
 * 1. Health check (/api/health)
 */
async function apiHealth() {
  try {
    const data = await safeApiFetch(`${BACKEND_URL}/api/health`, { method: "GET" });
    setHealthBadge(!!data.ok, data.detectif_reachable, data.detectif_details);
    if (data.credits_remaining != null) updateCreditCounters(data.credits_remaining);
    else void apiCredits();
    return data;
  } catch (e) {
    setHealthBadge(false, false, { reason: e.error || e.message || "Gateway unavailable" });
    return { ok: false, detectif_reachable: false, error: e.error || e.message };
  }
}

function updateCreditCounters(credits) {
  const text = credits == null || !Number.isFinite(Number(credits)) ? "—" : Number(credits).toLocaleString();
  ["creditsCounter", "judgeCreditsVal", "consoleLiveCredits"].forEach((id) => {
    const el = $(id);
    if (el) el.textContent = text;
  });
}

/**
 * 2. Credits query (/api/credits)
 */
async function apiCredits() {
  try {
    const data = await safeApiFetch(`${BACKEND_URL}/api/credits`, { method: "GET" });
    if (data && data.available != null) {
      updateCreditCounters(data.available);
    }
    return data;
  } catch (e) {
    updateCreditCounters(null);
    return null;
  }
}

/**
 * 3. Speaker Enrollment (/api/enroll)
 */
async function apiEnroll(audioBlob, name, lang = currentLang) {
  const fd = new FormData();
  fd.append("audio", audioBlob, "enroll.wav");
  fd.append("name", name);
  fd.append("lang", lang || "kn");
  return await safeApiFetch(`${BACKEND_URL}/api/enroll`, { method: "POST", body: fd });
}

/**
 * 4. Dual-Gate Voice Check (/api/check)
 */
async function apiCheck(audioBlob, speakerId, action, amount, lang = currentLang, device = currentDevice, source = currentSource) {
  const fd = new FormData();
  fd.append("audio", audioBlob, "check.wav");
  fd.append("speaker_id", speakerId || currentSpeakerId);
  fd.append("action", action || "VOICE_VERIFY");
  fd.append("lang", lang || "kn");
  fd.append("device", device || "phone1");
  fd.append("source", source || "live_mic");
  if (amount !== undefined && amount !== null && amount !== "") {
    fd.append("amount", amount);
  }
  return await safeApiFetch(`${BACKEND_URL}/api/check`, { method: "POST", body: fd });
}

/**
 * 4b. Tier-2 Challenge Submit with Fix 1 Original Audio Execution (/api/challenge/submit)
 */
async function apiChallengeSubmit(audioBlob, challengeId, speakerId, responseDelayMs) {
  const fd = new FormData();
  fd.append("audio", audioBlob, "challenge.wav");
  if (challengeId) fd.append("challenge_id", challengeId);
  if (speakerId) fd.append("speaker_id", speakerId);
  if (responseDelayMs != null) fd.append("response_delay_ms", String(responseDelayMs));

  return await safeApiFetch(`${BACKEND_URL}/api/challenge/submit`, { method: "POST", body: fd });
}

/**
 * 5. Full Voice Agent Turn (/api/agent/turn)
 */
async function apiAgentTurn(audioBlob, speakerId, action, amount) {
  const fd = new FormData();
  fd.append("audio", audioBlob, "turn.webm");
  fd.append("speaker_id", speakerId);
  fd.append("action", action || "TRANSFER_FUNDS");
  if (amount) fd.append("amount", amount);
  return await safeApiFetch(`${BACKEND_URL}/api/agent/turn`, { method: "POST", body: fd });
}

/**
 * 7. NPCI Hello! UPI Payment Execution (/api/pay/upi)
 */
async function apiPayUpi(amount, speakerId, credential) {
  if (!speakerId || !Number.isFinite(Number(amount)) || Number(amount) <= 0) {
    throw new Error("Choose a voice profile and enter a valid payment amount first.");
  }
  const payload = {
    amount: Number(amount),
    speaker_id: speakerId,
    credential: credential || undefined,
    is_unlocked: true
  };

  return await safeApiFetch(`${BACKEND_URL}/api/pay/upi`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

/**
 * 8. Verified Bank Agent Credential Issue (/api/credential/issue)
 */
async function apiIssueCredential() {
  const body = {
    agent_id: "npci-grampay-001",
    org: "NPCI Hello! UPI & 123Pay Authority",
    allowed_actions: ["CHECK_BALANCE", "TRANSFER_FUNDS", "PAY_UPI"],
    limit_inr: 50000.0
  };
  return await safeApiFetch(`${BACKEND_URL}/api/credential/issue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}

/**
 * 9. Credential Handshake Verification (/api/handshake/verify)
 */
async function apiVerifyCredential(credential) {
  return await safeApiFetch(`${BACKEND_URL}/api/handshake/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential })
  });
}

/**
 * 10. Audit Log Query (/api/audit?limit=30)
 */
async function apiAudit(limit = 30) {
  try {
    return await safeApiFetch(`${BACKEND_URL}/api/audit?limit=${limit}`);
  } catch (e) {
    return [];
  }
}

/**
 * 11. Slide 4 Stats Query (/api/stats)
 */
async function apiStats() {
  try {
    return await safeApiFetch(`${BACKEND_URL}/api/stats`);
  } catch (e) {
    return lastTelemetryStats;
  }
}

// ========== 7. RENDER CHECK / GATE RESPONSE ==========
function renderCheckResponse(data) {
  callerChallengeActive = data?.decision === "EXTRA_CHECK" && !!data.challenge?.challenge_id;
  if (callerChallengeActive) {
    currentChallengeId = data.challenge.challenge_id;
    challengeCurrentPhrase = Array.isArray(data.challenge.words) ? data.challenge.words : [];
    renderPhraseChips();
  }
  // 1. Status Card: PAY / APPROVED, CLONE BLOCKED, or EXTRA VOICE CHECK
  const unavailable = data.status === "error" || !!data.api_error || ["api_error", "challenge_failed"].includes(data.reason_key);
  setStatusCard(unavailable ? "UNAVAILABLE" : data.decision, unavailable ? data.api_error || data.reason : data.reason);
  updateRecordButtons(isRecording);

  // 2. Gauges & Latency Breakdown
  updateGauges(data.detection, data.verification);

  // 3. Decision & Tool Status
  if ($("metricDecision")) {
    const d = data.decision || "—";
    $("metricDecision").textContent = d;
    $("metricDecision").className = "text-right font-bold " +
      (d === "APPROVE" ? "text-safe" :
       d === "STEP_UP" ? "text-wait" : "text-alert");
  }

  const toolStatus = data.tool?.status || (data.tool_status ?? "LOCKED");
  if ($("metricTool")) {
    $("metricTool").textContent = toolStatus;
    $("metricTool").className = "font-bold " +
      (toolStatus === "EXECUTED" ? "text-safe" : "text-alert");
  }
  if ($("metricToolLockIcon")) {
    $("metricToolLockIcon").textContent = toolStatus === "EXECUTED" ? "🔓" : "🔒";
  }

  // 4. Slide 4 Cost & Telemetry Cache
  if (data.cost) {
    if (data.cost.agent_steps_skipped != null) {
      lastTelemetryStats.agent_steps_skipped = data.cost.agent_steps_skipped;
    }
    if (data.cost.agent_seconds_avoided != null) {
      lastTelemetryStats.agent_seconds_avoided = data.cost.agent_seconds_avoided;
    }
  }

  // 5. Update 2x2 Gate Decision Matrix & Live Spectrogram
  const synthScore = data.detection?.synthetic_score ?? data.synthetic_score;
  const matchScore = data.verification?.match_score ?? data.match_score;
  if (synthScore != null || matchScore != null) {
    renderGateMatrix(matchScore, synthScore, data.decision);
  }
  const isSynth = data.detection?.is_synthetic === true || data.detection?.verdict === "fake" || data.reason_key === "synthetic_blocked";
  renderSpectrogramSnapshot(isSynth, data.decision);

  // Update credits if returned in payload
  if (data.credits_remaining != null) {
    const counter = $("creditsCounter");
    if (counter) counter.textContent = Number(data.credits_remaining).toLocaleString();
    const judgeCredits = $("judgeCreditsVal");
    if (judgeCredits) judgeCredits.textContent = Number(data.credits_remaining).toLocaleString();
  }

  // 6. Raw Telemetry JSON
  if ($("jsonLog")) {
    $("jsonLog").textContent = JSON.stringify(data, null, 2);
  }

  // 7. Optional downstream speech-to-text transcript & Nemotron assistant vocal response
  if (data.transcript || data.agent_reply_text) {
    const extra = [];
    if (data.transcript) extra.push("🎙️ Spoken Order: " + data.transcript);
    if (data.intent) extra.push("🎯 Detected Intent: " + data.intent);
    if (data.agent_reply_text) extra.push("🤖 NPCI Voice Assistant: " + data.agent_reply_text);
    if ($("statusReason")) {
      $("statusReason").textContent =
        (data.reason ? data.reason + "\n\n" : "") + extra.join("\n");
    }
  }
}

// ========== 7B. 2x2 DECISION MATRIX & LIVE SPECTROGRAM VISUALIZERS ==========
let matrixPointsHistory = [];

function renderGateMatrix(matchScore, synthScore, decision) {
  const canvas = $("matrixCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const width = canvas.width;
  const height = canvas.height;
  const paddingLeft = 44;
  const paddingRight = 18;
  const paddingTop = 18;
  const paddingBottom = 30;

  const plotW = width - paddingLeft - paddingRight;
  const plotH = height - paddingTop - paddingBottom;

  // Clear canvas
  ctx.clearRect(0, 0, width, height);

  // Background fill
  ctx.fillStyle = "#0B0F17";
  ctx.fillRect(0, 0, width, height);

  // Axis mapping (0.0 to 1.0)
  const toX = (m) => paddingLeft + Math.max(0, Math.min(1, m)) * plotW;
  const toY = (s) => paddingTop + (1 - Math.max(0, Math.min(1, s))) * plotH;

  const matchThresh = 0.53;
  const synthLow = 0.20;
  const synthHigh = 0.50;

  const xSplit = toX(matchThresh);
  const yLow = toY(synthLow);
  const yHigh = toY(synthHigh);

  // 1. Quadrant Fills
  // Q1: Safe (Low Synth < 0.20, High Match >= 0.53) -> Emerald Green
  ctx.fillStyle = "rgba(16, 185, 129, 0.14)";
  ctx.fillRect(xSplit, yLow, width - paddingRight - xSplit, height - paddingBottom - yLow);

  // Q2: Clone Attack (High Synth >= 0.50, High Match >= 0.53) -> Alert Red
  ctx.fillStyle = "rgba(239, 68, 68, 0.16)";
  ctx.fillRect(xSplit, paddingTop, width - paddingRight - xSplit, yHigh - paddingTop);

  // Q3: Impostor Bot (High Synth >= 0.50, Low Match < 0.53) -> Crimson
  ctx.fillStyle = "rgba(185, 28, 28, 0.15)";
  ctx.fillRect(paddingLeft, paddingTop, xSplit - paddingLeft, yHigh - paddingTop);

  // Q4: Mismatch (Low Synth < 0.20, Low Match < 0.53) -> Amber
  ctx.fillStyle = "rgba(245, 158, 11, 0.12)";
  ctx.fillRect(paddingLeft, yLow, xSplit - paddingLeft, height - paddingBottom - yLow);

  // Borderline Middle Band (0.20 <= Synth < 0.50)
  ctx.fillStyle = "rgba(245, 158, 11, 0.07)";
  ctx.fillRect(paddingLeft, yHigh, plotW, yLow - yHigh);

  // 2. Threshold Reference Lines (Dashed)
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);

  // Vertical Match Threshold
  ctx.strokeStyle = "rgba(217, 119, 6, 0.65)";
  ctx.beginPath();
  ctx.moveTo(xSplit, paddingTop);
  ctx.lineTo(xSplit, height - paddingBottom);
  ctx.stroke();

  // Horizontal Synth High Threshold
  ctx.strokeStyle = "rgba(239, 68, 68, 0.65)";
  ctx.beginPath();
  ctx.moveTo(paddingLeft, yHigh);
  ctx.lineTo(width - paddingRight, yHigh);
  ctx.stroke();

  // Horizontal Synth Low Threshold
  ctx.strokeStyle = "rgba(16, 185, 129, 0.65)";
  ctx.beginPath();
  ctx.moveTo(paddingLeft, yLow);
  ctx.lineTo(width - paddingRight, yLow);
  ctx.stroke();

  ctx.setLineDash([]); // Reset dash

  // 3. Coordinate Axes
  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(paddingLeft, paddingTop);
  ctx.lineTo(paddingLeft, height - paddingBottom);
  ctx.lineTo(width - paddingRight, height - paddingBottom);
  ctx.stroke();

  // 4. Axis Ticks & Labels
  ctx.fillStyle = "#94A3B8";
  ctx.font = "9px monospace";
  ctx.textAlign = "center";
  ctx.fillText("0%", paddingLeft, height - paddingBottom + 12);
  ctx.fillText("53%", xSplit, height - paddingBottom + 12);
  ctx.fillText("100%", width - paddingRight, height - paddingBottom + 12);
  ctx.fillText("Eidos Match →", paddingLeft + plotW / 2, height - paddingBottom + 22);

  ctx.textAlign = "right";
  ctx.fillText("100%", paddingLeft - 5, paddingTop + 7);
  ctx.fillText("50%", paddingLeft - 5, yHigh + 3);
  ctx.fillText("20%", paddingLeft - 5, yLow + 3);
  ctx.fillText("0%", paddingLeft - 5, height - paddingBottom);

  // Quadrant Watermarks
  ctx.font = "bold 8px sans-serif";
  ctx.textAlign = "center";
  ctx.fillStyle = "rgba(239, 68, 68, 0.65)";
  ctx.fillText("Q2: CLONE", (xSplit + width - paddingRight) / 2, paddingTop + 13);
  ctx.fillStyle = "rgba(16, 185, 129, 0.65)";
  ctx.fillText("Q1: SAFE", (xSplit + width - paddingRight) / 2, height - paddingBottom - 7);
  ctx.fillStyle = "rgba(244, 63, 94, 0.65)";
  ctx.fillText("Q3: BOT", (paddingLeft + xSplit) / 2, paddingTop + 13);
  ctx.fillStyle = "rgba(245, 158, 11, 0.65)";
  ctx.fillText("Q4: MISMATCH", (paddingLeft + xSplit) / 2, height - paddingBottom - 7);

  // 5. Historical Points
  matrixPointsHistory.forEach((pt) => {
    const px = toX(pt.match);
    const py = toY(pt.synth);
    ctx.beginPath();
    ctx.arc(px, py, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = pt.decision === "APPROVE" ? "rgba(16, 185, 129, 0.45)"
      : pt.decision === "BLOCK_ALERT" ? "rgba(239, 68, 68, 0.45)"
      : pt.decision === "BLOCK" ? "rgba(225, 29, 72, 0.45)"
      : "rgba(245, 158, 11, 0.45)";
    ctx.fill();
  });

  // 6. Latest Transaction Point
  if (typeof matchScore === "number" && typeof synthScore === "number") {
    const curX = toX(matchScore);
    const curY = toY(synthScore);

    const color = decision === "APPROVE" ? "#10B981"
      : decision === "BLOCK_ALERT" ? "#EF4444"
      : decision === "BLOCK" ? "#E11D48"
      : "#F59E0B";

    // Pulsing outer ripple
    ctx.beginPath();
    ctx.arc(curX, curY, 10, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Solid inner dot
    ctx.beginPath();
    ctx.arc(curX, curY, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    // Coordinate tag bubble
    const tag = `[S:${(synthScore * 100).toFixed(0)}%, M:${(matchScore * 100).toFixed(0)}%]`;
    ctx.font = "bold 9px monospace";
    const textW = ctx.measureText(tag).width;
    const tagX = Math.min(width - paddingRight - textW - 4, Math.max(paddingLeft + 4, curX - textW / 2));
    const tagY = curY > paddingTop + 20 ? curY - 12 : curY + 18;

    ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
    ctx.fillRect(tagX - 3, tagY - 9, textW + 6, 13);
    ctx.strokeStyle = color;
    ctx.strokeRect(tagX - 3, tagY - 9, textW + 6, 13);
    ctx.fillStyle = "#FFFFFF";
    ctx.textAlign = "left";
    ctx.fillText(tag, tagX, tagY + 1);

    // Save into history if not duplicate
    const exists = matrixPointsHistory.some(p => Math.abs(p.match - matchScore) < 0.001 && Math.abs(p.synth - synthScore) < 0.001);
    if (!exists) {
      matrixPointsHistory.push({ match: matchScore, synth: synthScore, decision: decision || "UNKNOWN" });
      if (matrixPointsHistory.length > 25) matrixPointsHistory.shift();
    }

    // Update quadrant badge
    const badge = $("matrixQuadrantBadge");
    if (badge) {
      const qText = decision === "APPROVE" ? "Q1: APPROVE (SAFE)"
        : decision === "BLOCK_ALERT" ? "Q2: BLOCK_ALERT (CLONE)"
        : decision === "BLOCK" ? "Q3: BLOCK (BOT)"
        : "Q4: STEP_UP";
      badge.textContent = qText;
      badge.className = "rounded-md px-2 py-0.5 text-[10px] font-mono font-bold " +
        (decision === "APPROVE" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
         : decision === "BLOCK_ALERT" ? "bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse"
         : decision === "BLOCK" ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
         : "bg-amber-500/20 text-amber-400 border border-amber-500/40");
    }
  }
}

let spectrogramState = {
  decision: "STANDBY"
};

function renderSpectrogramSnapshot(_isSynthetic, decision) {
  spectrogramState.decision = decision || "STANDBY";
  const canvas = $("spectrogramCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.fillStyle = "#0B0F17";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#94A3B8";
  ctx.font = "14px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("No spectrogram data is provided by the analysis API.", canvas.width / 2, canvas.height / 2);
  const badge = $("spectrogramStatusBadge");
  if (badge) badge.textContent = "Provider spectrogram unavailable";
}

// ========== 8. AUDIO RECORDING ENGINE (16-bit Mono 16kHz PCM WAV) ==========
function handleRecordingFinished(recordedBlob, elapsedSec) {
  isRecording = false;
  const sec = (typeof elapsedSec === "number" ? elapsedSec : 0).toFixed(1);
  const sizeKb = (recordedBlob.size / 1024).toFixed(1);

  if (recordTarget === "challenge") {
    challengeAudioBlob = recordedBlob;
    stopChallengeTimer();
    updateRecordButtons(false);
    const finalSec = challengeElapsedSeconds.toFixed(2);
    const msg = `Captured in ${finalSec}s · Ready to verify Tier-2`;
    if ($("challengeTimerStatus")) $("challengeTimerStatus").textContent = msg;
    if ($("modalTimerStatus")) $("modalTimerStatus").textContent = msg;
  } else if (recordTarget === "enroll") {
    enrollBlob = recordedBlob;
    stopEnrollTimer();
    updateRecordButtons(false);
    if ($("enrollResult")) {
      $("enrollResult").textContent = `Voice sample recorded: ${sizeKb} KB (${sec}s). Click Enroll to store profile.`;
    }
  } else {
    // Senior / Live Voice Order
    currentBlob = recordedBlob;
    stopSeniorTimer();
    updateRecordButtons(false);

    // Update preview player
    const previewContainer = $("previewContainer");
    const audioPlayback = $("audioPlayback");
    if (audioPlayback && previewContainer) {
      audioPlayback.src = URL.createObjectURL(recordedBlob);
      previewContainer.classList.remove("hidden");
    }

    if ($("recordHint")) {
      $("recordHint").textContent = `Recorded ${sizeKb} KB (${sec}s 16kHz PCM WAV) · Ready for gate check`;
    }
    if ($("audioDurationBadge")) {
      $("audioDurationBadge").textContent = `${sec}s · ${sizeKb} KB (PCM 16kHz)`;
    }
  }
}

async function startRecording(target = "senior") {
  recordTarget = target;
  recordedChunks = [];

  // Check if getUserMedia is supported in the current browser/network context
  const hasMediaDevices = !!(
    typeof navigator !== "undefined" &&
    navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function"
  );

  if (!hasMediaDevices) {
    showError("Microphone recording is unavailable in this browser context. Open this local app on localhost or grant microphone access.");
    return;
  }

  // 1. Prefer In-Browser 16kHz Mono PCM WAV Recorder (Day 2 Fix 3)
  if (window.PcmAudioRecorder && typeof window.PcmAudioRecorder.start === "function") {
    try {
      await window.PcmAudioRecorder.start();
      isRecording = true;
      updateRecordButtons(true);
      if (target === "challenge") startChallengeTimer();
      else if (target === "enroll") startEnrollTimer();
      else startSeniorTimer();
      return;
    } catch (e) {
      console.warn("PcmAudioRecorder failed, falling back to MediaRecorder", e);
    }
  }

  // 2. Fallback to standard MediaRecorder
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";

    mediaRecorder = new MediaRecorder(stream, { mimeType: mime });
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordedChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const recordedBlob = new Blob(recordedChunks, { type: mime });
      stream.getTracks().forEach((t) => t.stop());
      const sec = target === "challenge" ? challengeElapsedSeconds : target === "enroll" ? enrollElapsedSec : seniorElapsedSec;
      handleRecordingFinished(recordedBlob, sec);
    };

    mediaRecorder.start();
    isRecording = true;
    updateRecordButtons(true);

    if (target === "challenge") {
      startChallengeTimer();
    } else if (target === "enroll") {
      startEnrollTimer();
    } else {
      startSeniorTimer();
    }
  } catch (err) {
    console.warn("Microphone access unavailable or denied:", err);
    isRecording = false;
    updateRecordButtons(false);
    showError(err?.message || "Microphone access was denied or unavailable.");
  }
}

async function stopRecording() {
  // Check PcmAudioRecorder first
  if (window.PcmAudioRecorder && window.PcmAudioRecorder.isRecording && window.PcmAudioRecorder.isRecording()) {
    try {
      const res = await window.PcmAudioRecorder.stop();
      if (res && res.blob) {
        handleRecordingFinished(res.blob, res.durationSeconds);
        return;
      }
    } catch (e) {
      console.warn("PcmAudioRecorder.stop error, falling back", e);
    }
  }

  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    const recorder = mediaRecorder;
    await new Promise((resolve) => {
      recorder.addEventListener("stop", resolve, { once: true });
      recorder.stop();
    });
  }
  if (recordTarget === "challenge") {
    stopChallengeTimer();
  } else if (recordTarget === "enroll") {
    stopEnrollTimer();
  } else {
    stopSeniorTimer();
  }
}

// Senior Recording Timer
function startSeniorTimer() {
  stopSeniorTimer();
  seniorRecordStart = performance.now();
  seniorElapsedSec = 0;
  seniorTimerInterval = setInterval(() => {
    const elapsed = (performance.now() - seniorRecordStart) / 1000;
    seniorElapsedSec = elapsed;
    const s = elapsed.toFixed(1);
    if ($("recordTimerText")) $("recordTimerText").textContent = `00:${elapsed < 10 ? '0' : ''}${s} s`;
    if ($("callerBtnRecordTimer")) $("callerBtnRecordTimer").textContent = `00:${elapsed < 10 ? '0' : ''}${s} s`;
    if ($("recordHint")) {
      $("recordHint").textContent = elapsed >= 4.0
        ? "≥ 4.0s recorded (Sufficient for DetectifAI Aletheia)"
        : `Recording order… speak clearly (${s}s / min 4.0s)`;
    }
    if ($("audioDurationBadge")) {
      $("audioDurationBadge").textContent = elapsed >= 4.0 ? "≥ 4.0s OK" : "Recording…";
    }
  }, 100);
}

function stopSeniorTimer() {
  if (seniorTimerInterval) {
    clearInterval(seniorTimerInterval);
    seniorTimerInterval = null;
  }
}

// Enrollment Recording Timer (>= 15s visual feedback)
function startEnrollTimer() {
  stopEnrollTimer();
  enrollRecordStart = performance.now();
  enrollElapsedSec = 0;
  const timerBar = $("enrollTimerBar");
  const progress = $("enrollTimerProgress");
  if (timerBar) timerBar.classList.remove("hidden");

  enrollTimerInterval = setInterval(() => {
    const elapsed = (performance.now() - enrollRecordStart) / 1000;
    enrollElapsedSec = elapsed;
    const pct = Math.min(100, (elapsed / 15.0) * 100);
    if (progress) {
      progress.style.width = pct + "%";
      progress.className = "h-full transition-all duration-100 " +
        (elapsed >= 15.0 ? "bg-emerald-500" : "bg-indigo-500");
    }
    if ($("enrollRecLabel")) {
      $("enrollRecLabel").textContent = elapsed >= 15.0
        ? `Recording (${elapsed.toFixed(1)}s - ≥15s OK)`
        : `Recording (${elapsed.toFixed(1)}s / 15s)`;
    }
  }, 100);
}

function stopEnrollTimer() {
  if (enrollTimerInterval) {
    clearInterval(enrollTimerInterval);
    enrollTimerInterval = null;
  }
  if ($("enrollRecLabel")) {
    $("enrollRecLabel").textContent = "Record Enrollment (≥15s)";
  }
}

function updateRecordButtons(recording) {
  if (recordTarget === "enroll") {
    const btn = $("btnEnrollRecord");
    const stopBtn = $("btnEnrollStop");
    const icon = $("enrollRecIcon");
    if (btn) {
      if (recording) {
        btn.classList.add("recording");
        if (icon) icon.textContent = "🔴";
      } else {
        btn.classList.remove("recording");
        if (icon) icon.textContent = "🎙️";
      }
    }
    if (stopBtn) stopBtn.disabled = !recording;
  } else if (recordTarget === "challenge") {
    const btn = $("btnRecordChallenge");
    const stopBtn = $("btnStopChallenge");
    const modalBtn = $("btnModalRecord");
    const modalStop = $("btnModalStop");

    if (btn) {
      if (recording) {
        btn.classList.add("recording");
        if ($("recChallengeLabel")) $("recChallengeLabel").textContent = "Recording Phrase…";
        if ($("recChallengeIcon")) $("recChallengeIcon").textContent = "🔴";
      } else {
        btn.classList.remove("recording");
        if ($("recChallengeLabel")) $("recChallengeLabel").textContent = "Recite Phrase Aloud";
        if ($("recChallengeIcon")) $("recChallengeIcon").textContent = "🎙️";
      }
    }
    if (stopBtn) stopBtn.disabled = !recording;

    if (modalBtn) {
      if (recording) modalBtn.classList.add("recording");
      else modalBtn.classList.remove("recording");
    }
    if (modalStop) modalStop.disabled = !recording;
  } else {
    // Senior/Farmer voice
    const btn = $("btnRecord");
    const stopBtn = $("btnStop");
    const label = $("recordLabel");
    const icon = $("recordIcon");

    if (btn) {
      if (recording) {
        btn.classList.add("recording");
        if (label) label.textContent = "ಧ್ವನಿ ರೆಕಾರ್ಡ್ ಆಗುತ್ತಿದೆ...";
        if (icon) icon.textContent = "🔴";
      } else {
        btn.classList.remove("recording");
        if (label) label.textContent = "ಮಾತನಾಡಿ / बोलिए / TAP TO SPEAK";
        if (icon) icon.textContent = "🎙️";
      }
    }
    if (stopBtn) stopBtn.disabled = !recording;

  }

  // Keep the one-tap caller control accurate for both normal and challenge audio.
  const callerMic = $("callerBtnRecord");
  const callerLabel = $("callerBtnRecordLabel");
  const callerIcon = $("callerBtnRecordIcon");
  if (callerMic) {
    if (recording) {
      callerMic.classList.add("recording", "bg-red-600", "border-red-600", "animate-pulse");
      callerMic.classList.remove("bg-ink", "border-ink");
      if (callerLabel) callerLabel.textContent = currentLang === "kn" ? "ನಿಲ್ಲಿಸಿ" : currentLang === "hi" ? "रोकें" : "Tap to Stop";
      if (callerIcon) callerIcon.textContent = "⏹️";
    } else {
      callerMic.classList.remove("recording", "bg-red-600", "border-red-600", "animate-pulse");
      callerMic.classList.add("bg-ink", "border-ink");
      if (callerLabel) callerLabel.textContent = callerChallengeActive
        ? (currentLang === "kn" ? "ಮತ್ತೊಂದು ಮಾದರಿ" : currentLang === "hi" ? "दूसरा नमूना" : "Record another sample")
        : (currentLang === "kn" ? "ಮಾತನಾಡಿ" : currentLang === "hi" ? "बोलिए" : "Tap to Speak");
      if (callerIcon) callerIcon.textContent = "🎙️";
    }
  }
}

function getAudioForRequest(fileInputId) {
  if (currentBlob && currentBlob.size > 0) return currentBlob;
  const input = $(fileInputId);
  if (input && input.files && input.files[0]) return input.files[0];
  return null;
}

// ========== 9. TAB VIEW TOGGLE & 1-CLICK HERO SCENARIOS ==========

// 1. Tab View Switching Logic (Farmer Simple View vs Judge Technical Console)
let currentView = "farmer"; // "farmer" | "judge" | "split"

function setView(view) {
  currentView = view;
  const tabFarmer = $("tabFarmer") || $("tabFarmerView") || $("tabBtnSimple");
  const tabJudge = $("tabJudge") || $("tabJudgeView") || $("tabBtnForensic");
  const tabSplit = $("tabSplit") || $("btnTabSplit");
  const panelFarmer = $("panelFarmer") || document.querySelector("section#panelFarmer") || document.querySelector("main section:first-of-type");
  const panelJudge = $("panelJudge") || document.querySelector("section#panelJudge") || document.querySelector("main section:last-of-type");
  const workspaceGrid = $("workspaceGrid");
  const judgeOverview = $("judgeOverviewSection");

  if (view === "farmer") {
    tabFarmer?.classList.add("active");
    tabJudge?.classList.remove("active");
    tabSplit?.classList.remove("bg-ink", "text-paper");
    tabSplit?.classList.add("bg-paper", "text-ink");

    panelFarmer?.classList.remove("hidden");
    panelJudge?.classList.add("hidden");
    panelJudge?.classList.remove("flex");

    // Hide judge overview (Slide 4 stats ribbon & 1-click test cards) for clean, senior-friendly screen
    judgeOverview?.classList.add("hidden");

    if (workspaceGrid) {
      // Clean, centered responsive container for mobile phone & laptop mode
      workspaceGrid.className = "mx-auto w-full max-w-xl md:max-w-2xl transition-all duration-300";
    }
  } else if (view === "judge") {
    tabJudge?.classList.add("active");
    tabFarmer?.classList.remove("active");
    tabSplit?.classList.remove("bg-ink", "text-paper");
    tabSplit?.classList.add("bg-paper", "text-ink");

    panelFarmer?.classList.add("hidden");
    panelJudge?.classList.remove("hidden");
    panelJudge?.classList.add("flex");

    // Reveal telemetry stats ribbon & 1-click test cards for judges
    judgeOverview?.classList.remove("hidden");

    if (workspaceGrid) {
      workspaceGrid.className = "mx-auto max-w-4xl transition-all duration-300";
    }

    // Refresh telemetry counters & audit log when entering judge console
    refreshStats();
    refreshAudit();
  } else if (view === "split") {
    tabFarmer?.classList.remove("active");
    tabJudge?.classList.remove("active");
    tabSplit?.classList.add("bg-ink", "text-paper");
    tabSplit?.classList.remove("bg-paper", "text-ink");

    panelFarmer?.classList.remove("hidden");
    panelJudge?.classList.remove("hidden");
    panelJudge?.classList.add("flex");

    // Reveal telemetry stats ribbon & 1-click test cards for judges
    judgeOverview?.classList.remove("hidden");

    if (workspaceGrid) {
      workspaceGrid.className = "mx-auto grid max-w-6xl gap-6 lg:grid-cols-[430px_1fr] items-start transition-all duration-300";
    }

    refreshStats();
    refreshAudit();
  }

  try {
    localStorage.setItem("unclone_active_view", view);
  } catch (e) {}
}

window.setView = setView;
window.setTab = setView;

// Attach tab listeners
$("tabFarmer")?.addEventListener("click", () => setView("farmer"));
$("tabFarmerView")?.addEventListener("click", () => setView("farmer"));
$("tabJudge")?.addEventListener("click", () => setView("judge"));
$("tabJudgeView")?.addEventListener("click", () => setView("judge"));
$("tabSplit")?.addEventListener("click", () => {
  setView(currentView === "split" ? "farmer" : "split");
});

// 3. Prepend Audit Table Helper
function prependAuditRow(r) {
  const tbody = $("auditBody");
  if (!tbody) return;

  const rawTs = r.ts || "";
  const t = rawTs ? (rawTs.includes("T") ? rawTs.substring(11, 19) : rawTs.substring(0, 19)) : "—";
  const d = r.decision || "—";
  const s = typeof r.synthetic_score === "number" ? (r.synthetic_score * 100).toFixed(0) + "%" : "—";
  const m = typeof r.match_score === "number" ? (r.match_score * 100).toFixed(0) + "%" : "—";
  const tool = r.tool_status || "LOCKED";

  const decColor = d.includes("APPROVE")
    ? "text-emerald-400 font-bold"
    : (d.startsWith("BLOCK") ? "text-red-400 font-bold" : "text-amber-400 font-bold");
  const toolColor = (tool === "EXECUTED" || tool === "UNLOCKED") ? "text-emerald-400 font-semibold" : "text-yellow-400/90";

  const rowHtml = `<tr class="border-t border-slate-800 hover:bg-slate-800/40 transition">
    <td class="p-2.5 whitespace-nowrap text-slate-400">${t}</td>
    <td class="p-2.5 ${decColor}">${d}</td>
    <td class="p-2.5 ${r.synthetic_score >= 0.62 ? 'text-red-400 font-semibold' : 'text-slate-300'}">${s}</td>
    <td class="p-2.5 ${r.match_score >= 0.53 ? 'text-cyan-400 font-semibold' : 'text-slate-300'}">${m}</td>
    <td class="p-2.5 font-mono text-[10px] ${toolColor}">${tool}</td>
  </tr>`;

  if (tbody.innerHTML.includes("No audit") || tbody.innerHTML.includes("colspan")) {
    tbody.innerHTML = rowHtml;
  } else {
    tbody.insertAdjacentHTML("afterbegin", rowHtml);
  }
}

// Bind Voice Assistant (TTS) Replay Action
$("btnReplayTTS")?.addEventListener("click", () => {
  if (lastSpokenVerdict) {
    speakVoiceAssistant(lastSpokenVerdict, true);
  } else {
    speakVoiceAssistant("approved", true);
  }
});

// ========== 10. PRESET EVENT LISTENERS & WORKFLOWS ==========

// Health check button
$("btnCheckHealth")?.addEventListener("click", () => {
  showOverlay("Checking local provider connection…");
  apiHealth().finally(hideOverlay);
});

// 2. Senior / Farmer Audio Recording & File Handling
$("btnRecord")?.addEventListener("click", () => {
  if (isRecording) return;
  startRecording("senior");
});
$("btnStop")?.addEventListener("click", stopRecording);

$("audioFileSenior")?.addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (file) {
    currentBlob = file;
    const previewContainer = $("previewContainer");
    const audioPlayback = $("audioPlayback");
    if (audioPlayback && previewContainer) {
      audioPlayback.src = URL.createObjectURL(file);
      previewContainer.classList.remove("hidden");
    }
    const sizeKb = (file.size / 1024).toFixed(1);
    if ($("recordHint")) $("recordHint").textContent = `Selected: ${file.name} (${sizeKb} KB)`;
    if ($("audioDurationBadge")) $("audioDurationBadge").textContent = `${sizeKb} KB`;
  }
});

// 3. Speaker Enrollment Recording & Execution
$("btnEnrollRecord")?.addEventListener("click", () => {
  if (isRecording) return;
  startRecording("enroll");
});
$("btnEnrollStop")?.addEventListener("click", stopRecording);

$("audioFileEnroll")?.addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (file) {
    enrollBlob = file;
    const sizeKb = (file.size / 1024).toFixed(1);
    if ($("enrollResult")) $("enrollResult").textContent = `Selected enrollment audio: ${file.name} (${sizeKb} KB)`;
  }
});

$("btnEnroll")?.addEventListener("click", async () => {
  const nameInput = $("enrollName")?.value.trim();
    const name = nameInput || "Account holder";
  const audio = enrollBlob || $("audioFileEnroll")?.files?.[0] || currentBlob;

  if (!audio) {
    alert("Record or upload an enrollment voice sample first (≥15 seconds recommended for DetectifAI Eidos).");
    return;
  }

  showOverlay("Sending voice enrollment to DetectifAI Eidos…");
  try {
    const data = await apiEnroll(audio, name);
    currentSpeakerId = data.speaker_id;
    currentSpeakerName = data.name || name;
    try {
      localStorage.setItem("unclone_speaker_id", currentSpeakerId);
      localStorage.setItem("unclone_speaker_name", currentSpeakerName);
    } catch (e) {}

    if ($("currentSpeakerLabel")) {
      $("currentSpeakerLabel").textContent = `${currentSpeakerName} (${data.speaker_id.substring(0, 8)}…)`;
    }
    if ($("currentSpeakerBadge")) {
      $("currentSpeakerBadge").textContent = `${currentSpeakerName} (${data.speaker_id.substring(0, 8)}…)`;
    }
    if ($("enrollResult")) {
      $("enrollResult").textContent = `Enrolled: ${currentSpeakerName} · speaker_id=${data.speaker_id} · ${data.latency_ms ?? 0} ms`;
    }
    if ($("jsonLog")) $("jsonLog").textContent = JSON.stringify(data, null, 2);

    setStatusCard(null, `Account holder "${currentSpeakerName}" enrolled successfully in DetectifAI Eidos. GramPay Voice Shield is active.`);
  } catch (err) {
    const msg = err.error || err.message || "Enrollment failed";
    if ($("enrollResult")) $("enrollResult").textContent = "Error: " + msg;
    showError(msg, err.fail_closed !== false);
  } finally {
    hideOverlay();
    refreshAudit();
    refreshStats();
  }
});

// 4. Primary Voice Gate Check (/api/check)
$("btnCheck")?.addEventListener("click", async () => {
  const audio = getAudioForRequest("audioFileSenior");
  if (!audio) {
    alert("Record your voice or select an audio file first.");
    return;
  }

  const action = "VOICE_VERIFY";
  const amount = null;
  const speakerId = currentSpeakerId;
  if (!speakerId) {
    showError("Enroll a voice profile before running verification.", true);
    return;
  }

  showOverlay("Running GramPay Voice Gate Check (DetectifAI Aletheia + Eidos)…");
  try {
    const data = await apiCheck(audio, speakerId, action, amount);
    renderCheckResponse(data);
  } catch (err) {
    showError(err.error || err.message || "Gate check failed", err.fail_closed !== false);
  } finally {
    hideOverlay();
    refreshAudit();
    refreshStats();
  }
});

// 5. Full Agent Turn (/api/agent/turn)
$("btnAgentTurn")?.addEventListener("click", async () => {
  const audio = getAudioForRequest("audioFileSenior");
  if (!audio) {
    alert("Record your voice or select an audio file first.");
    return;
  }

  const action = $("actionSelect")?.value || "TRANSFER_FUNDS";
  const amount = $("amountInput")?.value || "5000";
  const speakerId = currentSpeakerId;

  showOverlay("Gate Check → Speech-to-Text → NVIDIA Nemotron Assistant Turn…");
  try {
    const data = await apiAgentTurn(audio, speakerId, action, amount);
    renderCheckResponse(data);
  } catch (err) {
    showError(err.error || err.message || "Agent turn execution failed", err.fail_closed !== false);
  } finally {
    hideOverlay();
    refreshAudit();
    refreshStats();
  }
});

// 6. Direct Hello! UPI Tool Execution (/api/pay/upi)
$("btnExecutePay")?.addEventListener("click", async () => {
  const amount = parseFloat($("amountInput")?.value || "");
  const speakerId = currentSpeakerId;
  if (!speakerId || !Number.isFinite(amount) || amount <= 0) {
    showError("Choose a voice profile and enter a valid payment amount first.");
    return;
  }

  showOverlay("Executing NPCI Hello! UPI / 123Pay Voice Payment Tool…");
  try {
    const data = await apiPayUpi(amount, speakerId, lastCredential);
    setStatusCard(data.status === "EXECUTED" ? "APPROVE" : null, data.message || "Payment API returned a response; check its status before treating the payment as complete.");
    if ($("metricTool")) {
      $("metricTool").textContent = "EXECUTED";
      $("metricTool").className = "font-black text-base text-emerald-400";
    }
    if ($("jsonLog")) $("jsonLog").textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    showError(err.error || err.message || "UPI payment execution failed", err.fail_closed !== false);
  } finally {
    hideOverlay();
    refreshAudit();
    refreshStats();
  }
});

// 7. Tier-2 Active Challenge Controls
$("btnNewPhrase")?.addEventListener("click", () => generateChallenge().catch(err => setChallengeStatus(err.message || "Challenge service unavailable.", true)));
$("btnNewPhraseModal")?.addEventListener("click", () => generateChallenge().catch(err => setChallengeStatus(err.message || "Challenge service unavailable.", true)));

$("btnRecordChallenge")?.addEventListener("click", () => {
  if (isRecording) return;
  startRecording("challenge");
});
$("btnStopChallenge")?.addEventListener("click", stopRecording);

$("btnModalRecord")?.addEventListener("click", () => {
  if (isRecording) return;
  startRecording("challenge");
});
$("btnModalStop")?.addEventListener("click", stopRecording);

async function verifySecondVoiceSample() {
  const elapsed = challengeElapsedSeconds;
  const audio = challengeAudioBlob || currentBlob;

  if (!audio) {
    alert("Record yourself speaking the randomized phrase first to verify response latency.");
    return;
  }

  showOverlay("Checking the second voice sample…");
  try {
    const speakerId = currentSpeakerId;
    const data = await apiChallengeSubmit(audio, currentChallengeId, speakerId, Math.round(elapsed * 1000));

    renderCheckResponse(data);

    if (data.decision === "PAY" || data.decision === "APPROVE" || data.verified) {
      const msg = `✅ PASS: Voice verification passed. Response time: ${elapsed.toFixed(2)}s.`;
      setChallengeStatus(msg, false);
      const okMsg = (window.getReasonText && window.getReasonText(currentLang, "approved"))
        || `Voice challenge passed. Measured response time: ${elapsed.toFixed(2)}s.`;
      setStatusCard("APPROVE", okMsg);
    } else {
      const failReason = (window.getReasonText && window.getReasonText(currentLang, "challenge_failed"))
        || (data.reason || "Voice verification could not be completed.");
      const msg = `🛑 FAIL: Tier-2 verification blocked: ${failReason}`;
      setChallengeStatus(msg, true);
      setStatusCard("BLOCK_ALERT", failReason);
    }
  } catch (err) {
    const msg = err.error || err.message || "Challenge verification failed";
    setChallengeStatus("🛑 Error: " + msg, true);
    showError(msg, err.fail_closed !== false);
  } finally {
    hideOverlay();
    refreshAudit();
    refreshStats();
  }
}

$("btnVerifyChallenge")?.addEventListener("click", verifySecondVoiceSample);
$("btnModalVerify")?.addEventListener("click", async () => {
  await verifySecondVoiceSample();
  closeChallengeModal();
});

// Challenge Modal Open / Close
function openChallengeModal() {
  const m = $("challengeModal");
  if (m) {
    m.classList.remove("hidden");
    m.classList.add("flex");
  }
  if (!currentChallengeId) generateChallenge().catch(err => setChallengeStatus(err.message || "Challenge service unavailable.", true));
}

function closeChallengeModal() {
  const m = $("challengeModal");
  if (m) {
    m.classList.add("hidden");
    m.classList.remove("flex");
  }
}

$("btnOpenChallenge")?.addEventListener("click", openChallengeModal);
$("btnCloseModal")?.addEventListener("click", closeChallengeModal);
$("challengeModal")?.addEventListener("click", (e) => {
  if (e.target === $("challengeModal")) closeChallengeModal();
});

// 8. Bank Agent Credentials Handshake & Replay Prevention
$("btnIssueCred")?.addEventListener("click", async () => {
  showOverlay("Issuing Single-Use NPCI Bank Agent Credential…");
  try {
    const data = await apiIssueCredential();
    const token = data.credential || data.token || JSON.stringify(data);
    lastCredential = token;

    if ($("credInput")) $("credInput").value = token;
    if ($("badgeLabel")) {
      $("badgeLabel").textContent = "ISSUED";
      $("badgeLabel").className = "rounded-full px-3 py-1 text-xs font-bold tracking-wide bg-wait-bg text-wait border border-wait";
    }
    if ($("badgeReason")) {
      $("badgeReason").textContent = "Cryptographic single-use JWT issued. Ready for mutual verification.";
    }
    if ($("credResult")) {
      $("credResult").textContent = `Issued Token: ${token.substring(0, 48)}…`;
    }
    if ($("jsonLog")) $("jsonLog").textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    if ($("credResult")) $("credResult").textContent = "Error issuing credential: " + (err.error || err.message);
  } finally {
    hideOverlay();
  }
});

$("btnVerifyCred")?.addEventListener("click", async () => {
  const cred = $("credInput")?.value.trim();
  if (!cred) {
    alert("Please issue or paste a credential token first.");
    return;
  }

  showOverlay("Verifying Mutual Cryptographic Handshake…");
  try {
    const data = await apiVerifyCredential(cred);
    if (data.badge === "VERIFIED_AGENT") {
      if ($("badgeLabel")) {
        $("badgeLabel").textContent = "VERIFIED_AGENT";
        $("badgeLabel").className = "rounded-full px-3 py-1 text-xs font-bold tracking-wide bg-safe-bg text-safe border border-safe glow-verified";
      }
      if ($("badgeReason")) {
        $("badgeReason").textContent = data.reason || "Mutual cryptographic trust established with NPCI Hello! UPI Authority.";
      }
      if ($("credResult")) {
        $("credResult").textContent = `Handshake Verified: Nonce consumed, signature valid, org: ${data.org || "NPCI"}.`;
      }
    } else {
      if ($("badgeLabel")) {
        $("badgeLabel").textContent = "REJECTED";
        $("badgeLabel").className = "rounded-full px-3 py-1 text-xs font-bold tracking-wide bg-alert-bg text-alert border border-alert";
      }
      if ($("badgeReason")) {
        $("badgeReason").textContent = data.reason || "Credential rejected: unauthorized or expired.";
      }
      if ($("credResult")) {
        $("credResult").textContent = "Verification Failed: " + (data.reason || "Rejected");
      }
    }
    if ($("jsonLog")) $("jsonLog").textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    if ($("badgeLabel")) {
      $("badgeLabel").textContent = "REJECTED";
      $("badgeLabel").className = "rounded-full px-3 py-1 text-xs font-bold tracking-wide bg-alert-bg text-alert border border-alert";
    }
    if ($("badgeReason")) {
      $("badgeReason").textContent = err.error || err.message || "Credential rejected (single-use replay or invalid signature).";
    }
    if ($("credResult")) {
      $("credResult").textContent = "Handshake Rejected: " + (err.error || err.message);
    }
  } finally {
    hideOverlay();
  }
});

$("btnReplayCred")?.addEventListener("click", async () => {
  if (!lastCredential) {
    alert("Issue and verify a credential first. Then test replay attack rejection.");
    return;
  }

  if ($("credInput")) $("credInput").value = lastCredential;

  // Replay the exact same consumed credential: must be rejected
  showOverlay("Executing Replay Attack on Consumed Token (Deterministic Rejection Expected)…");
  try {
    const data = await apiVerifyCredential(lastCredential);
    if (data.badge === "REJECTED" || data.status === "rejected") {
      if ($("badgeLabel")) {
        $("badgeLabel").textContent = "REPLAY REJECTED";
        $("badgeLabel").className = "rounded-full px-3 py-1 text-xs font-bold tracking-wide bg-alert-bg text-alert border border-alert";
      }
      if ($("badgeReason")) {
        $("badgeReason").textContent = "Deterministic Replay Prevention: Token nonce was already consumed on first use.";
      }
      if ($("credResult")) {
        $("credResult").textContent = "REPLAY ATTACK BLOCKED: " + (data.reason || "Token nonce already consumed");
      }
    }
    if ($("jsonLog")) $("jsonLog").textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    if ($("badgeLabel")) {
      $("badgeLabel").textContent = "REPLAY REJECTED";
      $("badgeLabel").className = "rounded-full px-3 py-1 text-xs font-bold tracking-wide bg-alert-bg text-alert border border-alert";
    }
    if ($("badgeReason")) {
      $("badgeReason").textContent = "Deterministic Replay Prevention: Token nonce already consumed. Replay attack blocked.";
    }
    if ($("credResult")) {
      $("credResult").textContent = "REPLAY BLOCKED: " + (err.error || err.message);
    }
  } finally {
    hideOverlay();
  }
});

// 9. Raw Telemetry JSON Copy
$("btnCopyJson")?.addEventListener("click", async () => {
  const jsonText = $("jsonLog")?.textContent || "";
  try {
    await navigator.clipboard.writeText(jsonText);
    const btn = $("btnCopyJson");
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = "Copied!";
      setTimeout(() => { btn.textContent = orig; }, 1500);
    }
  } catch (e) {
    // Clipboard permission denied fallback
  }
});

// 10. Slide 4 Telemetry Stats & Live Audit Log Table
async function refreshStats() {
  try {
    const data = await apiStats();
    if (data && (data.checks != null || data.total_checks != null || data.checks_run != null)) {
      updateSlide4Counters(data);
    }
  } catch (e) {
    updateSlide4Counters(lastTelemetryStats);
  }
}

function renderAuditRows(rows) {
  const tbody = $("auditBody");
  if (!tbody) return;
  const list = Array.isArray(rows) ? rows : [];

  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-slate-400">No voice checks recorded.</td></tr>';
    return;
  }

  tbody.innerHTML = list.map((r) => {
    const rawTs = r.ts || r.time || r.created_at || "";
    const t = rawTs.includes("T") ? rawTs.substring(11, 19) : (rawTs.substring(0, 19) || "—");
    const d = r.decision || "—";

    // Scores
    let s = "—";
    let m = "—";
    const synthVal = r.synthetic_score ?? r.detection?.synthetic_score ?? r.scores?.synthetic;
    const matchVal = r.match_score ?? r.verification?.match_score ?? r.scores?.match;

    if (typeof synthVal === "number") s = (synthVal * 100).toFixed(0) + "%";
    if (typeof matchVal === "number") m = (matchVal * 100).toFixed(0) + "%";

    const tool = r.tool_status || r.tool?.status || "—";

    const decColor = d === "APPROVE" || d.includes("APPROVE")
      ? "text-emerald-400 font-bold"
      : (d.startsWith("BLOCK") ? "text-red-400 font-bold" : "text-amber-400 font-bold");

    const toolColor = tool === "EXECUTED" ? "text-emerald-400 font-semibold" : "text-yellow-400/90";

    return `<tr class="border-t border-slate-800 hover:bg-slate-800/40 transition">
      <td class="p-2.5 whitespace-nowrap text-slate-400 font-mono text-[11px]">${t}</td>
      <td class="p-2.5 ${decColor}">${d}</td>
      <td class="p-2.5 ${synthVal >= 0.62 ? 'text-red-400 font-semibold' : 'text-slate-300'}">${s}</td>
      <td class="p-2.5 ${matchVal >= 0.53 ? 'text-cyan-400 font-semibold' : 'text-slate-300'}">${m}</td>
      <td class="p-2.5 font-mono text-[10px] ${toolColor}">${tool}</td>
    </tr>`;
  }).join("");
}

async function refreshAudit() {
  try {
    const data = await apiAudit(30);
    const rows = Array.isArray(data) ? data : (data.logs || data.rows || data.audit || []);
    renderAuditRows(rows);
  } catch (e) {
    renderAuditRows([]);
  }
}

$("btnRefreshStats")?.addEventListener("click", refreshStats);
$("btnRefreshAudit")?.addEventListener("click", refreshAudit);

// ========== 11. MULTILINGUAL & DEVICE SELECTOR CONTROLLERS ==========
function setLanguage(lang) {
  currentLang = lang || "kn";
  
  // Highlight active lang button with senior-accessible classes (20px+ font with checkmark)
  document.querySelectorAll(".lang-btn").forEach((btn) => {
    const isAct = btn.dataset.lang === currentLang;
    btn.classList.toggle("active", isAct);
    if (isAct) {
      btn.className = "lang-btn active min-h-[64px] sm:min-h-[72px] rounded-2xl px-4 py-3 text-[20px] sm:text-[22px] md:text-[24px] font-bold transition border-3 border-ink bg-ink text-paper shadow-md flex items-center justify-center text-center gap-2";
    } else {
      btn.className = "lang-btn min-h-[64px] sm:min-h-[72px] rounded-2xl px-4 py-3 text-[20px] sm:text-[22px] md:text-[24px] font-bold transition border-2 border-line bg-paper text-ink hover:bg-cream-2 shadow-2xs flex items-center justify-center text-center gap-2";
    }
    const checkEl = btn.querySelector(".lang-check");
    if (checkEl) {
      checkEl.classList.toggle("hidden", !isAct);
    }
  });

  // Localized hint and primary button CTA (Zero Jargon)
  const cfg = (typeof window !== "undefined" && window.LANGUAGES && window.LANGUAGES[currentLang]) || null;
  if (cfg) {
    const instruction = currentLang === "kn" ? "ದೊಡ್ಡ ಗುಂಡಿಯನ್ನು ಒತ್ತಿ ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ." : currentLang === "hi" ? "बटन दबाकर स्पष्ट रूप से बोलें।" : "Tap the microphone and speak clearly.";
    if ($("statusReason")) $("statusReason").textContent = instruction;
    if ($("recordHint")) $("recordHint").textContent = instruction;
  }

  // Update primary Speak button label (Clean, single language, no clipping)
  if ($("recordLabel")) {
    $("recordLabel").textContent = currentLang === "kn" ? "ಮಾತನಾಡಿ (Tap to Speak)" : currentLang === "hi" ? "बोलिए (Tap to Speak)" : "Tap to Speak";
  }
  if ($("stopLabel")) {
    $("stopLabel").textContent = currentLang === "kn" ? "ನಿಲ್ಲಿಸಿ (Stop)" : currentLang === "hi" ? "रोकें (Stop)" : "Stop";
  }

  // Update TTS Replay button label
  if ($("btnReplayTTSLabel")) {
    $("btnReplayTTSLabel").textContent = currentLang === "kn"
      ? "ಧ್ವನಿ ದೃಢೀಕರಣ ಆಲಿಸಿ / Replay Voice Assistant"
      : (currentLang === "hi"
        ? "पुष्टि आवाज़ सुनें / Replay Voice Assistant"
        : "Replay Voice Assistant Confirmation");
  }

  // Regenerate challenge words in selected script
  generateChallenge().catch(err => setChallengeStatus(err.message || "Challenge service unavailable.", true));
}

function renderConsoleEventsTable(events) {
  const tbody = $("consoleEventsTableBody");
  if (!tbody || !events || events.length === 0) return;
  const last5 = events.slice(-5).reverse();
  tbody.innerHTML = last5.map(ev => {
    const timeStr = ev.ts ? new Date(ev.ts).toLocaleTimeString() : new Date().toLocaleTimeString();
    const spk = ev.speaker_id || "—";
    const dec = ev.decision || "—";
    const synth = ev.synthetic_score ?? ev.detection?.synthetic_score;
    const match = ev.match_score ?? ev.verification?.match_score;
    const tool = ev.tool_status || "—";

    const decColor = (dec === "APPROVE" || dec === "PAY")
      ? "text-emerald-400 font-bold"
      : (dec === "STEP_UP" || dec === "EXTRA_CHECK" ? "text-amber-400 font-bold" : "text-red-400 font-bold");
    const toolBadge = tool === "EXECUTED"
      ? '<span class="px-2 py-0.5 rounded-md bg-emerald-950 text-emerald-400 border border-emerald-500/40 text-xs font-bold">🔓 EXECUTED</span>'
      : `<span class="px-2 py-0.5 rounded-md bg-slate-900 text-slate-400 border border-slate-700 text-xs font-bold">${tool}</span>`;

    return `
      <tr class="hover:bg-cream-2/40 transition">
        <td class="p-3 text-xs text-muted font-mono">${timeStr}</td>
        <td class="p-3 font-medium text-xs">${spk}</td>
        <td class="p-3 ${decColor}">${dec}</td>
        <td class="p-3 font-mono font-bold ${synth >= 0.50 ? 'text-red-400' : 'text-emerald-400'}">${synth != null ? (synth * 100).toFixed(1) + '%' : '—'}</td>
        <td class="p-3 font-mono font-bold ${match >= 0.80 ? 'text-cyan-400' : 'text-amber-400'}">${match != null ? (match * 100).toFixed(1) + '%' : '—'}</td>
        <td class="p-3">${toolBadge}</td>
      </tr>
    `;
  }).join("");
}

async function pollLatestState() {
  try {
    const url = lastEventId ? `${BACKEND_URL}/api/latest-state?since=${lastEventId}` : `${BACKEND_URL}/api/latest-state`;
    const data = await safeApiFetch(url);
    if (!data) return;

    // 1. Live Platform Credits Balance
    if (data.credits_remaining != null) {
      const counter = $("creditsCounter");
      if (counter) counter.textContent = Number(data.credits_remaining).toLocaleString();
      const judgeCredits = $("judgeCreditsVal");
      if (judgeCredits) judgeCredits.textContent = Number(data.credits_remaining).toLocaleString();
      const consoleCredits = $("consoleLiveCredits");
      if (consoleCredits) consoleCredits.textContent = Number(data.credits_remaining).toLocaleString();
    }

    // 2. Slide 4 presentation counters
    if (data.stats) {
      updateSlide4Counters(data.stats);
      if ($("consoleStepsSkipped")) $("consoleStepsSkipped").textContent = data.stats.agent_steps_skipped ?? "—";
      if ($("consoleInrSaved")) $("consoleInrSaved").textContent = data.stats.agent_time_saved_inr == null ? "—" : `₹${Number(data.stats.agent_time_saved_inr).toFixed(2)}`;
    }

    // 3. Process new events stream
    if (data.events && data.events.length > 0) {
      if (lastEventId === null) {
        // Existing audit rows may belong to earlier app activity. Establish a
        // cursor without presenting those rows as checks from this session.
        const priorEvents = data.events;
        lastEventId = priorEvents[priorEvents.length - 1].event_id || priorEvents[priorEvents.length - 1].request_id;
        const tbody = $("consoleEventsTableBody");
        if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-muted font-sans font-medium">No voice checks recorded in this session.</td></tr>';
        return;
      }
      lastEventId = data.events[data.events.length - 1].event_id || data.events[data.events.length - 1].request_id;
      data.events.forEach(ev => prependAuditRow(ev));

      // Latest event updates 2x2 matrix, live spectrogram, and gauges
      const latest = data.events[data.events.length - 1];
      const synth = latest.synthetic_score ?? latest.detection?.synthetic_score;
      const match = latest.match_score ?? latest.verification?.match_score;
      const dec = latest.decision;
      const tool = latest.tool_status || "—";
      const detMs = latest.detection_latency_ms ?? latest.detection?.latency_ms ?? latest.latency_ms;
      const verMs = latest.verification_latency_ms ?? latest.verification?.latency_ms;

      if (synth != null || match != null) {
        updateGauges(
          { synthetic_score: synth, latency_ms: detMs },
          { match_score: match, latency_ms: verMs }
        );
        renderGateMatrix(match, synth, dec);
      }

      if ($("metricDecision")) {
        $("metricDecision").textContent = dec || "—";
        $("metricDecision").className = "text-right font-bold " +
          (dec === "APPROVE" ? "text-safe" : (dec === "STEP_UP" ? "text-wait" : "text-alert"));
      }
      if ($("metricTool")) {
        $("metricTool").textContent = tool;
        $("metricTool").className = "font-bold " + (tool === "EXECUTED" ? "text-safe" : "text-alert");
      }
      if ($("metricToolLockIcon")) {
        $("metricToolLockIcon").textContent = tool === "EXECUTED" ? "🔓" : "🔒";
      }

      const isSynth = latest.is_synthetic === true || latest.detection?.is_synthetic === true || latest.reason_key === "synthetic_blocked";
      renderSpectrogramSnapshot(isSynth, dec);

      // ===== 4 LARGE CARDS FOR LAPTOP JUDGE CONSOLE (?mode=console) =====
      // Card 1: Full-Width Decision Banner (Readable from 10 feet away)
      const banner = $("consoleDecisionBanner");
      const bannerText = $("consoleBannerText");
      const bannerDot = $("consoleBannerDot");
      if (banner && bannerText) {
        if (dec === "APPROVE" || dec === "PAY") {
          banner.className = "w-full rounded-3xl border-4 border-emerald-500 bg-emerald-950/90 p-6 sm:p-8 text-center shadow-2xl transition-all duration-300";
          bannerText.textContent = "🟢 VOICE CHECK APPROVED";
          bannerText.className = "font-display text-3xl sm:text-5xl font-black tracking-wide text-emerald-400 uppercase";
          if (bannerDot) bannerDot.className = "size-5 rounded-full bg-emerald-400 animate-pulse";
        } else if (dec === "BLOCK" || dec === "BLOCK_ALERT") {
          banner.className = "w-full rounded-3xl border-4 border-red-500 bg-red-950/90 p-6 sm:p-8 text-center shadow-2xl transition-all duration-300";
          bannerText.textContent = "🔴 VOICE CHECK BLOCKED";
          bannerText.className = "font-display text-3xl sm:text-5xl font-black tracking-wide text-red-400 uppercase";
          if (bannerDot) bannerDot.className = "size-5 rounded-full bg-red-400 animate-ping";
        } else if (dec === "STEP_UP" || dec === "EXTRA_CHECK") {
          banner.className = "w-full rounded-3xl border-4 border-amber-500 bg-amber-950/90 p-6 sm:p-8 text-center shadow-2xl transition-all duration-300";
          bannerText.textContent = "🟡 EXTRA CHECK (4-WORD COGNITIVE CHALLENGE)";
          bannerText.className = "font-display text-3xl sm:text-5xl font-black tracking-wide text-amber-400 uppercase";
          if (bannerDot) bannerDot.className = "size-5 rounded-full bg-amber-400 animate-pulse";
        }
      }

      // Card 2: Two Giant Score Cards
      if ($("consoleSynthScore") && synth != null) {
        $("consoleSynthScore").textContent = `${(synth * 100).toFixed(1)}%`;
        $("consoleSynthScore").className = "font-mono text-6xl sm:text-7xl font-black " + (synth >= 0.50 ? "text-red-400" : "text-emerald-400");
      }
      if ($("consoleDetLatency")) $("consoleDetLatency").textContent = detMs != null ? `⚡ ${detMs} ms` : "—";

      if ($("consoleMatchScore") && match != null) {
        $("consoleMatchScore").textContent = `${(match * 100).toFixed(1)}%`;
        $("consoleMatchScore").className = "font-mono text-6xl sm:text-7xl font-black " + (match >= 0.80 ? "text-cyan-400" : (match >= 0.53 ? "text-amber-400" : "text-red-400"));
      }
      if ($("consoleVerLatency")) $("consoleVerLatency").textContent = verMs != null ? `⚡ ${verMs} ms` : "—";

      // Card 3: Action Gate Status & Spoken Transcript
      const toolBadge = $("consoleToolStatusBadge");
      const toolText = $("consoleToolStatusText");
      const toolIcon = $("consoleToolLockIcon");
      if (toolBadge && toolText && toolIcon) {
        if (tool === "EXECUTED") {
          toolBadge.className = "rounded-2xl px-5 py-2 text-base sm:text-lg font-black tracking-wide border-2 bg-emerald-950 border-emerald-500 text-emerald-300 flex items-center gap-2";
          toolIcon.textContent = "🔓";
          toolText.textContent = "Downstream action executed (reported by API)";
        } else if (tool === "—") {
          toolBadge.className = "rounded-2xl px-5 py-2 text-base sm:text-lg font-black tracking-wide border-2 bg-slate-900 border-slate-700 text-slate-300 flex items-center gap-2";
          toolIcon.textContent = "•";
          toolText.textContent = "No downstream action status reported";
        } else {
          toolBadge.className = "rounded-2xl px-5 py-2 text-base sm:text-lg font-black tracking-wide border-2 bg-red-950 border-red-500 text-red-300 flex items-center gap-2";
          toolIcon.textContent = "🔒";
          toolText.textContent = `Downstream action status: ${tool}`;
        }
      }

      const transcriptBox = $("consoleTranscriptBox");
      const bypassNote = $("consoleLlmBypassNote");
      if (transcriptBox && bypassNote) {
        const userTxt = latest.transcript || latest.user_text;
        const trans = latest.translation;
        transcriptBox.textContent = userTxt ? `🗣️ ${userTxt}${trans ? ` → [English: "${trans}"]` : ""}` : "No transcript reported";
        bypassNote.textContent = latest.llm_status || "No language model status reported";
        bypassNote.className = "font-mono font-bold text-slate-400";
      }

      // Card 4: 5-Row Recent Events Table
      renderConsoleEventsTable(data.events);
    }
  } catch (e) {
    // Polling retry
  }
}

function switchStageMode(mode) {
  const normMode = String(mode || "split").toLowerCase();

  // Highlight active role switcher pill
  document.querySelectorAll(".mode-switcher-pill").forEach(p => {
    const target = p.dataset.targetMode;
    const isAct = (normMode === "split" && target === "split") ||
                  (normMode === "caller" && target === "phone1") ||
                  (normMode === "console" && target === "console");
    p.classList.toggle("active", isAct);
    if (isAct) {
      p.className = "mode-switcher-pill active inline-flex items-center gap-1.5 rounded-xl border-2 border-ink bg-ink text-paper px-3 py-1.5 text-xs sm:text-sm font-bold shadow-xs transition cursor-pointer";
    } else {
      p.className = "mode-switcher-pill inline-flex items-center gap-1.5 rounded-xl border-2 border-line bg-cream hover:bg-cream-2 text-ink px-3 py-1.5 text-xs sm:text-sm font-bold shadow-2xs transition cursor-pointer";
    }
  });

  if (normMode === "console") {
    document.body.classList.add("mode-console");
    document.body.classList.remove("mode-caller", "mode-split");
    if ($("judgeConsoleView")) {
      $("judgeConsoleView").classList.remove("hidden");
      $("judgeConsoleView").classList.add("flex");
    }
    if ($("callerPhoneView")) {
      $("callerPhoneView").classList.add("hidden");
      $("callerPhoneView").classList.remove("flex");
    }
    if ($("standardView")) {
      $("standardView").classList.add("hidden");
    }
    setView("judge");
    pollLatestState();
    if (!window._consolePollInterval) {
      window._consolePollInterval = setInterval(pollLatestState, 1000);
    }
  } else if (normMode === "caller") {
    document.body.classList.add("mode-caller");
    document.body.classList.remove("mode-console", "mode-split");
    if ($("callerPhoneView")) {
      $("callerPhoneView").classList.remove("hidden");
      $("callerPhoneView").classList.add("flex");
    }
    if ($("judgeConsoleView")) {
      $("judgeConsoleView").classList.add("hidden");
      $("judgeConsoleView").classList.remove("flex");
    }
    if ($("standardView")) {
      $("standardView").classList.add("hidden");
    }
    setView("farmer");
    initCallerPhoneControls();

    // Start 1500ms live fraud sync on Farmer Phone
    pollCallerState();
    if (!window._callerPollInterval) {
      window._callerPollInterval = setInterval(pollCallerState, 1500);
    }
  } else {
    // Judge-ready split: the actual farmer phone experience beside bank telemetry.
    document.body.classList.remove("mode-caller", "mode-console");
    document.body.classList.add("mode-split");
    if ($("standardView")) {
      $("standardView").classList.add("hidden");
    }
    if ($("callerPhoneView")) {
      $("callerPhoneView").classList.remove("hidden");
      $("callerPhoneView").classList.add("flex");
    }
    if ($("judgeConsoleView")) {
      $("judgeConsoleView").classList.remove("hidden");
      $("judgeConsoleView").classList.add("flex");
    }
    setView("split");
    initCallerPhoneControls();
    pollLatestState();
    pollCallerState();
    if (!window._consolePollInterval) {
      window._consolePollInterval = setInterval(pollLatestState, 1500);
    }
    if (!window._callerPollInterval) {
      window._callerPollInterval = setInterval(pollCallerState, 1500);
    }
  }
}

let lastCallerNotifiedEventId = null;
let callerStatePrimed = false;

async function pollCallerState() {
  try {
    const url = lastCallerNotifiedEventId
      ? `${BACKEND_URL}/api/latest-state?since=${lastCallerNotifiedEventId}`
      : `${BACKEND_URL}/api/latest-state`;
    const data = await safeApiFetch(url);
    if (!data || !Array.isArray(data.events)) return;

    // Ignore audit history already present when this page opens. Only alert on a
    // new event observed after the farmer view is active.
    if (!callerStatePrimed) {
      const priorEvent = data.events[data.events.length - 1];
      lastCallerNotifiedEventId = priorEvent?.event_id || priorEvent?.request_id || null;
      callerStatePrimed = true;
      return;
    }
    if (data.events.length === 0) return;

    const latest = data.events[data.events.length - 1];
    const evId = latest.event_id || latest.request_id;
    if (evId === lastCallerNotifiedEventId) return;
    lastCallerNotifiedEventId = evId;

    const agentBadge = $("callerAgentBadge");
    if (agentBadge && latest.badge === "VERIFIED_AGENT") {
      agentBadge.textContent = "Voice profile verified";
    }

    const dec = latest.decision;
    const lang = (currentLang || "kn").toLowerCase();

    // Flash security result directly on Farmer Phone
    if (dec === "BLOCK_ALERT" || dec === "BLOCK") {
      callerChallengeActive = false;
      const card = $("callerStatusCard");
      const emoji = $("callerStatusEmoji");
      const title = $("callerStatusTitle");
      const reason = $("callerStatusReason");
      const box = $("callerChallengeBox");

      if (card) {
        card.classList.remove("status-ready", "status-approve", "status-stepup");
        card.classList.add("status-block");
      }
      if (emoji) emoji.textContent = "🛑";
      const unavailable = ["api_error", "challenge_failed"].includes(latest.reason_key) || latest.fail_closed === true;
      const syntheticDetected = !unavailable && (latest.reason_key === "synthetic_blocked" || latest.detection?.is_synthetic === true);
      if (title) {
        title.textContent = syntheticDetected
          ? (lang === "kn" ? "🛑 ಸಂಶ್ಲೇಷಿತ ಧ್ವನಿ ಪತ್ತೆಯಾಗಿದೆ" : (lang === "hi" ? "🛑 सिंथेटिक आवाज़ मिली" : "Synthetic voice detected"))
          : (lang === "kn" ? "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಪೂರ್ಣಗೊಳ್ಳಲಿಲ್ಲ" : (lang === "hi" ? "आवाज़ की जाँच पूरी नहीं हो सकी" : "Voice check could not be completed"));
      }
      if (reason) {
        reason.textContent = syntheticDetected
          ? (lang === "kn" ? "ಸಂಶ್ಲೇಷಿತ ಧ್ವನಿ ಎಂದು ಪತ್ತೆಯಾಗಿದೆ. ಯಾವುದೇ ಮುಂದಿನ ಕ್ರಮ ಅನುಮೋದಿಸಲ್ಪಟ್ಟಿಲ್ಲ." : (lang === "hi" ? "सिंथेटिक आवाज़ मिली। कोई आगे की कार्रवाई स्वीकृत नहीं हुई।" : "Synthetic voice detected. No downstream action was approved."))
          : (lang === "kn" ? "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಪೂರ್ಣಗೊಳ್ಳಲಿಲ್ಲ. ಈ ಪರಿಶೀಲನೆಯಲ್ಲಿ ಮುಂದಿನ ಕ್ರಮಕ್ಕೆ ಅನುಮೋದನೆ ನೀಡಲಾಗಿಲ್ಲ." : (lang === "hi" ? "आवाज़ की जाँच पूरी नहीं हो सकी। इस जाँच से आगे की कार्रवाई स्वीकृत नहीं हुई।" : "Voice check could not be completed. No downstream action was approved by this voice check."));
      }
      if (box) box.classList.add("hidden");
      if (syntheticDetected) speakVoiceAssistant("blocked");
    } else if (dec === "APPROVE" || dec === "PAY") {
      callerChallengeActive = false;
      const card = $("callerStatusCard");
      const emoji = $("callerStatusEmoji");
      const title = $("callerStatusTitle");
      const reason = $("callerStatusReason");
      const box = $("callerChallengeBox");

      if (card) {
        card.classList.remove("status-ready", "status-block", "status-stepup");
        card.classList.add("status-approve");
      }
      if (emoji) emoji.textContent = "✅";
      if (title) {
        title.textContent = lang === "kn"
          ? "✅ ಧ್ವನಿ ಪರಿಶೀಲನೆ ಯಶಸ್ವಿಯಾಗಿದೆ"
          : (lang === "hi" ? "✅ आवाज़ की जाँच सफल हुई" : "✅ Voice check passed");
      }
      if (reason) {
        reason.textContent = lang === "kn"
          ? "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಯಶಸ್ವಿ. ಯಾವುದೇ ಪಾವತಿ ಮಾಡಲಾಗಿಲ್ಲ."
          : (lang === "hi" ? "आवाज़ की जाँच सफल हुई। कोई भुगतान नहीं किया गया।" : "Voice check passed. No payment was made.");
      }
      if (box) box.classList.add("hidden");
      speakVoiceAssistant("approved");
    } else if (dec === "EXTRA_CHECK" && latest.challenge?.challenge_id) {
      callerChallengeActive = true;
      currentChallengeId = latest.challenge.challenge_id;
      challengeCurrentPhrase = Array.isArray(latest.challenge.words) ? latest.challenge.words : [];
      renderPhraseChips();
      setStatusCard("EXTRA_CHECK", latest.reason || "Record another voice sample to continue the check.");
      updateRecordButtons(false);
    }
  } catch (e) {
    // Polling retry
  }
}

function initRoleSwitcherPills() {
  const pills = [
    { id: "pillModeSplit", mode: "split", url: "?view=split" },
    { id: "pillModePhone1", mode: "caller", url: "?mode=caller" },
    { id: "pillModeConsole", mode: "console", url: "?mode=console" }
  ];

  pills.forEach(p => {
    const el = $(p.id);
    if (el) {
      el.onclick = (e) => {
        e.preventDefault();
        try {
          window.history.pushState({}, "", p.url);
        } catch (err) {}
        switchStageMode(p.mode);
      };
    }
  });

  // Initialize the local caller clock
  initVirtualPhoneClock();
}

function initVirtualPhoneClock() {
  const clockEl = $("phoneSimClock");
  if (!clockEl) return;
  const updateClock = () => {
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };
  updateClock();
  setInterval(updateClock, 1000);
}



function initCallerPhoneControls() {
  // Wire up caller mic button
  const callerMic = $("callerBtnRecord");
  if (callerMic) {
    callerMic.onclick = async () => {
      if (isRecording) {
        const target = recordTarget;
        await stopRecording();
        const submitWhenReady = async () => {
          if (isRecording) return setTimeout(submitWhenReady, 50);
          const audio = target === "challenge" ? challengeAudioBlob : currentBlob;
          const duration = target === "challenge" ? challengeElapsedSeconds : seniorElapsedSec;
          if (!audio || audio.size < 44) {
            showError("No voice audio was captured. Allow microphone access and try again.", true);
            return;
          }
          if (duration < 3) {
            showError("Please speak for at least 3 seconds, then tap again to check your voice.", true);
            return;
          }
          if (target !== "challenge") {
            $("btnCheck")?.click();
            return;
          }
          if (!currentChallengeId) {
            showError("The voice challenge expired. Start a new voice check.", true);
            callerChallengeActive = false;
            updateRecordButtons(false);
            return;
          }
          callerMic.disabled = true;
          showOverlay("Checking your challenge voice…");
          try {
            const data = await apiChallengeSubmit(audio, currentChallengeId, currentSpeakerId, Math.round(duration * 1000));
            renderCheckResponse(data);
          } catch (err) {
            showError(err.error || err.message || "Challenge voice check failed", err.fail_closed !== false);
            callerChallengeActive = false;
            updateRecordButtons(false);
          } finally {
            callerMic.disabled = false;
            hideOverlay();
            refreshAudit();
            refreshStats();
          }
        };
        await submitWhenReady();
      } else {
        await startRecording(callerChallengeActive ? "challenge" : "senior");
      }
    };
  }

  // Wire up caller language toggle
  document.querySelectorAll(".caller-lang-btn").forEach(btn => {
    btn.onclick = () => {
      const l = btn.dataset.lang;
      if (l) {
        setLanguage(l);
        document.querySelectorAll(".caller-lang-btn").forEach(b => {
          const isAct = b.dataset.lang === l;
          b.classList.toggle("active", isAct);
          if (isAct) {
            b.className = "caller-lang-btn active rounded-xl px-3 py-1.5 text-sm font-black transition border-2 border-ink bg-ink text-paper";
          } else {
            b.className = "caller-lang-btn rounded-xl px-3 py-1.5 text-sm font-bold transition border-2 border-transparent text-ink hover:bg-cream-2";
          }
        });
      }
    };
  });

  // Wire up compact enroll button
  const callerEnroll = $("callerBtnEnroll");
  if (callerEnroll) {
    callerEnroll.onclick = async () => {
      if (!isRecording) {
        await startRecording("enroll");
        return;
      }
      if (recordTarget !== "enroll") {
        showError("Stop the current recording before enrolling a voice profile.", false);
        return;
      }
      await stopRecording();
      $("btnEnroll")?.click();
    };
  }

}

// ========== 10. SYSTEM INITIALIZATION & MULTI-DEVICE PROTOCOL ==========
(async function init() {
  setStatusCard(null);
  renderPhraseChips();

  // Keep scores empty until a live provider response arrives.
  renderGateMatrix(null, null, null);
  renderSpectrogramSnapshot(false, "STANDBY");

  // Wire Language Selector Bar
  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.addEventListener("click", () => setLanguage(btn.dataset.lang));
  });

  // The farmer and bank are the only product views. Test attacks use labeled controls.

  // Set default speaker profile
  if ($("currentSpeakerLabel")) {
    $("currentSpeakerLabel").textContent = currentSpeakerName || "No voice profile enrolled";
  }

  // Initialize 1-Tap Role Switcher Pills
  initRoleSwitcherPills();

  // Initialize the farmer, bank console, or split view. Legacy device query values are ignored.
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const modeParam = urlParams.get("mode");
    const viewParam = urlParams.get("view") || urlParams.get("tab") || window.location.hash.replace("#", "");
    const path = window.location.pathname.toLowerCase();

    // 2. Multi-Device Stage Setup (Default to Split View on Desktop with no ?mode=)
    if (modeParam === "console" || path.includes("judge") || path.includes("console")) {
      switchStageMode("console");
    } else if (modeParam === "caller") {
      switchStageMode("caller");
    } else if (viewParam && ["farmer", "judge", "split"].includes(viewParam.toLowerCase())) {
      switchStageMode(viewParam.toLowerCase());
    } else {
      // Default to Split View: Caller on Left, Judge Console on Right (immediate working product with 0 login)
      switchStageMode("split");
    }

    if (urlParams.get("lang")) setLanguage(urlParams.get("lang"));
  } catch (e) {
    switchStageMode("split");
  }

  // Initial queries
  await apiHealth();
  try {
    await generateChallenge();
  } catch (err) {
    setChallengeStatus(err.message || "Challenge service unavailable.", true);
  }
  await refreshStats();
  await refreshAudit();

  // Periodic health check every 25 seconds
  setInterval(apiHealth, 25000);
  // Periodic Slide 4 stats refresh every 10 seconds
  setInterval(refreshStats, 10000);
  // Periodic audit refresh every 15 seconds
  setInterval(refreshAudit, 15000);
})();
