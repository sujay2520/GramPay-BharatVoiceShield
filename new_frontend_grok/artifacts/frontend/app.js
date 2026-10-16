/**
 * UnClone Agent Gate – Frontend
 * Renders ONLY what the backend returns. No hard-coded scores or statuses.
 * Backend URL is the single config constant below.
 */

// ========== CONFIG (change only this for different hosts) ==========
const BACKEND_URL = "https://your-backend.onrender.com";   // ← set to real deployed URL
// const BACKEND_URL = "http://localhost:8000";            // local dev

// ========== STATE ==========
let mediaRecorder = null;
let recordedChunks = [];
let currentBlob = null;          // last recorded or uploaded audio
let currentSpeakerId = null;     // from last successful enroll
let lastCredential = null;       // for replay test
let isRecording = false;
let enrollMode = false;          // true when recording for enroll

// ========== DOM HELPERS ==========
const $ = (id) => document.getElementById(id);

function showOverlay(text = "Working…") {
  $("overlayText").textContent = text;
  $("overlay").classList.remove("hidden");
  $("overlay").classList.add("flex");
}
function hideOverlay() {
  $("overlay").classList.add("hidden");
  $("overlay").classList.remove("flex");
}

function setStatusCard(decision, reason) {
  const card = $("statusCard");
  const emoji = $("statusEmoji");
  const title = $("statusTitle");
  const reasonEl = $("statusReason");

  card.classList.remove("status-approve", "status-block", "status-stepup", "status-ready");

  if (!decision) {
    card.classList.add("status-ready");
    emoji.textContent = "🛡️";
    title.textContent = "System Ready";
    title.className = "text-xl md:text-2xl font-bold text-slate-200";
    reasonEl.textContent = reason || "Tap and speak, or upload a short clip.";
    return;
  }

  const d = decision.toUpperCase();
  if (d === "APPROVE") {
    card.classList.add("status-approve");
    emoji.textContent = "✅";
    title.textContent = "APPROVED";
    title.className = "text-xl md:text-2xl font-bold text-emerald-300";
  } else if (d === "BLOCK_ALERT" || d === "BLOCK") {
    card.classList.add("status-block");
    emoji.textContent = "🛑";
    title.textContent = d === "BLOCK_ALERT" ? "BLOCKED + ALERT" : "BLOCKED";
    title.className = "text-xl md:text-2xl font-bold text-red-300";
  } else if (d === "STEP_UP") {
    card.classList.add("status-stepup");
    emoji.textContent = "⚠️";
    title.textContent = "STEP-UP REQUIRED";
    title.className = "text-xl md:text-2xl font-bold text-amber-300";
  } else {
    card.classList.add("status-ready");
    emoji.textContent = "❓";
    title.textContent = decision;
    title.className = "text-xl md:text-2xl font-bold text-slate-200";
  }
  reasonEl.textContent = reason || "";
}

function setHealthBadge(ok, detectifReachable) {
  const badge = $("healthBadge");
  const dot = $("healthDot");
  const text = $("healthText");
  badge.classList.remove("health-ok", "health-fail", "health-unknown");

  if (ok === true && detectifReachable === true) {
    badge.classList.add("health-ok");
    dot.className = "w-2.5 h-2.5 rounded-full bg-emerald-400";
    text.textContent = "Platform API: Reachable";
  } else if (ok === true && detectifReachable === false) {
    badge.classList.add("health-fail");
    dot.className = "w-2.5 h-2.5 rounded-full bg-red-400";
    text.textContent = "DetectifAI: Unreachable";
  } else {
    badge.classList.add("health-unknown");
    dot.className = "w-2.5 h-2.5 rounded-full bg-slate-500";
    text.textContent = "Status: Unknown";
  }
}

function updateGauges(detection, verification) {
  const synth = detection?.synthetic_score;
  const match = verification?.match_score;

  if (typeof synth === "number") {
    const pct = Math.min(100, Math.max(0, synth * 100));
    $("gaugeSynthVal").textContent = pct.toFixed(1) + "%";
    $("gaugeSynthBar").style.width = pct + "%";
    $("gaugeSynthBar").className = "h-full transition-all duration-500 " +
      (synth >= 0.5 ? "bg-red-500" : synth >= 0.2 ? "bg-amber-500" : "bg-emerald-500");
  } else {
    $("gaugeSynthVal").textContent = "—";
    $("gaugeSynthBar").style.width = "0%";
  }

  if (typeof match === "number") {
    const pct = Math.min(100, Math.max(0, match * 100));
    $("gaugeMatchVal").textContent = pct.toFixed(1) + "%";
    $("gaugeMatchBar").style.width = pct + "%";
    $("gaugeMatchBar").className = "h-full transition-all duration-500 " +
      (match >= 0.85 ? "bg-emerald-500" : match >= 0.5 ? "bg-amber-500" : "bg-red-500");
  } else {
    $("gaugeMatchVal").textContent = "—";
    $("gaugeMatchBar").style.width = "0%";
  }
}

function updateCost(cost) {
  if (!cost) return;
  $("costSteps").textContent = cost.agent_steps_skipped ?? 0;
  $("costSeconds").textContent = cost.agent_seconds_avoided ?? 0;
  $("costInr").textContent = "₹" + (Number(cost.est_inr) || 0).toFixed(2);
  if (cost.assumption) {
    $("costAssumptionText").textContent = cost.assumption;
  }
}

function showError(msg, failClosed = true) {
  setStatusCard("BLOCK", failClosed
    ? (msg || "Something went wrong. For safety the gate is closed.")
    : msg);
  $("jsonLog").textContent = JSON.stringify({ error: msg, fail_closed: failClosed }, null, 2);
}

// ========== API CALLS ==========
async function apiHealth() {
  try {
    const r = await fetch(`${BACKEND_URL}/api/health`, { method: "GET" });
    const data = await r.json();
    setHealthBadge(!!data.ok, data.detectif_reachable);
    return data;
  } catch (e) {
    setHealthBadge(false, false);
    return null;
  }
}

async function apiEnroll(audioBlob, name) {
  const fd = new FormData();
  fd.append("audio", audioBlob, "enroll.webm");
  fd.append("name", name);
  const r = await fetch(`${BACKEND_URL}/api/enroll`, { method: "POST", body: fd });
  const data = await r.json();
  if (!r.ok || data.error) throw data;
  return data;
}

async function apiCheck(audioBlob, speakerId, action, amount) {
  const fd = new FormData();
  fd.append("audio", audioBlob, "check.webm");
  fd.append("speaker_id", speakerId);
  fd.append("action", action);
  if (amount !== undefined && amount !== null && amount !== "") {
    fd.append("amount", amount);
  }
  const r = await fetch(`${BACKEND_URL}/api/check`, { method: "POST", body: fd });
  const data = await r.json();
  if (!r.ok || data.error) throw data;
  return data;
}

async function apiAgentTurn(audioBlob, speakerId) {
  const fd = new FormData();
  fd.append("audio", audioBlob, "turn.webm");
  fd.append("speaker_id", speakerId);
  const r = await fetch(`${BACKEND_URL}/api/agent/turn`, { method: "POST", body: fd });
  const data = await r.json();
  if (!r.ok || data.error) throw data;
  return data;
}

async function apiIssueCredential() {
  const body = {
    agent_id: "demo-agent-001",
    org: "UnClone Bank Demo",
    allowed_actions: ["CHECK_BALANCE", "TRANSFER_FUNDS"],
    limit_inr: 50000
  };
  const r = await fetch(`${BACKEND_URL}/api/credential/issue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await r.json();
  if (!r.ok || data.error) throw data;
  return data;
}

async function apiVerifyCredential(credential) {
  const r = await fetch(`${BACKEND_URL}/api/handshake/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential })
  });
  const data = await r.json();
  if (!r.ok || data.error) throw data;
  return data;
}

async function apiAudit(limit = 50) {
  const r = await fetch(`${BACKEND_URL}/api/audit?limit=${limit}`);
  return r.json();
}

async function apiStats() {
  const r = await fetch(`${BACKEND_URL}/api/stats`);
  return r.json();
}

// ========== RENDER RESPONSE ==========
function renderCheckResponse(data) {
  // Status card – only what API returns
  setStatusCard(data.decision, data.reason);

  // Gauges
  updateGauges(data.detection, data.verification);

  // Decision & tool
  $("metricDecision").textContent = data.decision || "—";
  $("metricDecision").className = "font-bold " +
    (data.decision === "APPROVE" ? "text-emerald-400" :
     data.decision === "STEP_UP" ? "text-amber-400" : "text-red-400");

  const toolStatus = data.tool?.status || "LOCKED";
  $("metricTool").textContent = toolStatus;
  $("metricTool").className = toolStatus === "EXECUTED" ? "text-emerald-400" : "text-yellow-400";

  // Latency
  const detMs = data.detection?.latency_ms ?? "—";
  const verMs = data.verification?.latency_ms ?? "—";
  $("metricLatency").textContent = `${detMs} / ${verMs} ms`;

  // Cost
  updateCost(data.cost);

  // Raw JSON
  $("jsonLog").textContent = JSON.stringify(data, null, 2);

  // Optional agent fields
  if (data.transcript || data.agent_reply_text) {
    const extra = [];
    if (data.transcript) extra.push("Transcript: " + data.transcript);
    if (data.intent) extra.push("Intent: " + data.intent);
    if (data.agent_reply_text) extra.push("Agent: " + data.agent_reply_text);
    $("statusReason").textContent =
      (data.reason || "") + (extra.length ? "\n\n" + extra.join("\n") : "");
  }
}

// ========== RECORDING ==========
async function startRecording(forEnroll = false) {
  enrollMode = forEnroll;
  recordedChunks = [];
  currentBlob = null;

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // Prefer webm/opus; browser will choose best available
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
      currentBlob = new Blob(recordedChunks, { type: mime });
      stream.getTracks().forEach((t) => t.stop());
      isRecording = false;
      updateRecordButtons(false);
      $("recordHint").textContent = `Recorded ${(currentBlob.size / 1024).toFixed(1)} KB · ready to send`;
    };

    mediaRecorder.start();
    isRecording = true;
    updateRecordButtons(true);
    $("recordHint").textContent = "Recording… speak clearly (3–8 s)";
  } catch (err) {
    alert("Microphone access denied or unavailable: " + err.message);
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

function updateRecordButtons(recording) {
  const btn = enrollMode ? $("btnEnrollRecord") : $("btnRecord");
  const stopBtn = enrollMode ? $("btnEnrollStop") : $("btnStop");
  const label = enrollMode ? null : $("recordLabel");
  const icon = enrollMode ? null : $("recordIcon");

  if (recording) {
    btn.classList.add("recording");
    if (label) label.textContent = "Recording…";
    if (icon) icon.textContent = "🔴";
    stopBtn.disabled = false;
  } else {
    btn.classList.remove("recording");
    if (label) label.textContent = "Tap and Speak";
    if (icon) icon.textContent = "🎙️";
    stopBtn.disabled = true;
  }
}

// ========== EVENT HANDLERS ==========
function getAudioForRequest(fileInputId) {
  // Prefer live recording if present, else file input
  if (currentBlob && currentBlob.size > 0) return currentBlob;
  const input = $(fileInputId);
  if (input && input.files && input.files[0]) return input.files[0];
  return null;
}

$("btnRecord").addEventListener("click", () => {
  if (isRecording) return;
  startRecording(false);
});
$("btnStop").addEventListener("click", stopRecording);

$("btnEnrollRecord").addEventListener("click", () => {
  if (isRecording) return;
  startRecording(true);
});
$("btnEnrollStop").addEventListener("click", stopRecording);

$("btnEnroll").addEventListener("click", async () => {
  const name = $("enrollName").value.trim();
  if (!name) {
    alert("Please enter a name for the speaker.");
    return;
  }
  const audio = getAudioForRequest("audioFileEnroll");
  if (!audio) {
    alert("Record or upload a short audio clip first.");
    return;
  }

  showOverlay("Enrolling speaker…");
  try {
    const data = await apiEnroll(audio, name);
    currentSpeakerId = data.speaker_id;
    $("enrollResult").textContent =
      `Enrolled: ${data.name} · speaker_id=${data.speaker_id} · ${data.latency_ms ?? "?"} ms`;
    $("jsonLog").textContent = JSON.stringify(data, null, 2);
    setStatusCard(null, `Speaker "${data.name}" enrolled successfully. You can now run a gate check.`);
  } catch (err) {
    const msg = err.error || err.message || "Enrollment failed";
    $("enrollResult").textContent = "Error: " + msg;
    showError(msg, err.fail_closed !== false);
  } finally {
    hideOverlay();
  }
});

$("btnCheck").addEventListener("click", async () => {
  if (!currentSpeakerId) {
    alert("Enroll a speaker first (right panel).");
    return;
  }
  const audio = getAudioForRequest("audioFileSenior");
  if (!audio) {
    alert("Record or upload audio first.");
    return;
  }
  const action = $("actionSelect").value;
  const amount = $("amountInput").value;

  showOverlay("Running DetectifAI gate…");
  try {
    const data = await apiCheck(audio, currentSpeakerId, action, amount);
    renderCheckResponse(data);
  } catch (err) {
    showError(err.error || err.message || "Gate check failed", err.fail_closed !== false);
  } finally {
    hideOverlay();
    refreshAudit();
    refreshStats();
  }
});

$("btnAgentTurn").addEventListener("click", async () => {
  if (!currentSpeakerId) {
    alert("Enroll a speaker first (right panel).");
    return;
  }
  const audio = getAudioForRequest("audioFileSenior");
  if (!audio) {
    alert("Record or upload audio first.");
    return;
  }

  showOverlay("Gate → STT → LLM (only if approved)…");
  try {
    const data = await apiAgentTurn(audio, currentSpeakerId);
    renderCheckResponse(data);
  } catch (err) {
    showError(err.error || err.message || "Agent turn failed", err.fail_closed !== false);
  } finally {
    hideOverlay();
    refreshAudit();
    refreshStats();
  }
});

// Credentials
$("btnIssueCred").addEventListener("click", async () => {
  showOverlay("Issuing credential…");
  try {
    const data = await apiIssueCredential();
    // Assume backend returns { credential: "..." } or similar
    const cred = data.credential || data.token || JSON.stringify(data);
    lastCredential = cred;
    $("credInput").value = typeof cred === "string" ? cred : JSON.stringify(cred);
    $("credResult").textContent = "Issued. Paste into verify or use Replay.";
    $("jsonLog").textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    $("credResult").textContent = "Error: " + (err.error || err.message);
  } finally {
    hideOverlay();
  }
});

$("btnVerifyCred").addEventListener("click", async () => {
  const cred = $("credInput").value.trim();
  if (!cred) {
    alert("Paste a credential first.");
    return;
  }
  showOverlay("Verifying credential…");
  try {
    const data = await apiVerifyCredential(cred);
    $("badgeLabel").textContent = data.badge || "—";
    $("badgeLabel").className = "text-xs px-2 py-1 rounded " +
      (data.badge === "VERIFIED_AGENT"
        ? "bg-emerald-900 text-emerald-300"
        : "bg-red-900 text-red-300");
    $("badgeReason").textContent = data.reason || "";
    $("credResult").textContent = JSON.stringify(data.checks || data, null, 2);
    $("jsonLog").textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    $("badgeLabel").textContent = "REJECTED";
    $("badgeLabel").className = "text-xs px-2 py-1 rounded bg-red-900 text-red-300";
    $("badgeReason").textContent = err.error || err.message || "Verification failed";
  } finally {
    hideOverlay();
  }
});

$("btnReplayCred").addEventListener("click", async () => {
  if (!lastCredential) {
    alert("Issue a credential first, then replay it.");
    return;
  }
  $("credInput").value = typeof lastCredential === "string"
    ? lastCredential
    : JSON.stringify(lastCredential);
  // Trigger verify (second use should be rejected)
  $("btnVerifyCred").click();
});

// Audit & Stats
async function refreshAudit() {
  try {
    const data = await apiAudit(30);
    const rows = Array.isArray(data) ? data : (data.rows || data.audit || []);
    const tbody = $("auditBody");
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="p-3 text-center text-slate-500">No entries yet</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map((r) => {
      const t = r.ts || r.time || r.created_at || "—";
      const d = r.decision || "—";
      const s = r.synthetic_score != null ? (r.synthetic_score * 100).toFixed(0) + "%" : (r.detection?.synthetic_score != null ? (r.detection.synthetic_score * 100).toFixed(0) + "%" : "—");
      const m = r.match_score != null ? (r.match_score * 100).toFixed(0) + "%" : (r.verification?.match_score != null ? (r.verification.match_score * 100).toFixed(0) + "%" : "—");
      const tool = r.tool_status || r.tool?.status || "—";
      return `<tr class="border-t border-slate-800">
        <td class="p-2 whitespace-nowrap">${t}</td>
        <td class="p-2">${d}</td>
        <td class="p-2">${s}</td>
        <td class="p-2">${m}</td>
        <td class="p-2">${tool}</td>
      </tr>`;
    }).join("");
  } catch (e) {
    // silent – backend may not be up yet
  }
}

async function refreshStats() {
  try {
    const data = await apiStats();
    if (data.checks != null || data.total_checks != null) {
      // Map common shapes
      const steps = data.steps_skipped ?? data.agent_steps_skipped ?? 0;
      const secs = data.seconds_avoided ?? data.agent_seconds_avoided ?? 0;
      const inr = data.est_inr ?? data.total_est_inr ?? 0;
      $("costSteps").textContent = steps;
      $("costSeconds").textContent = secs;
      $("costInr").textContent = "₹" + Number(inr).toFixed(2);
    }
    if (data.assumption) $("costAssumptionText").textContent = data.assumption;
  } catch (e) { /* ignore */ }
}

$("btnRefreshAudit").addEventListener("click", refreshAudit);
$("btnRefreshStats").addEventListener("click", refreshStats);

$("costAssumption").addEventListener("change", () => {
  const v = $("costAssumption").value;
  $("costAssumptionText").textContent = `Assumption: Rs ${v} per min (editable)`;
});

// File inputs clear the live blob so the chosen file is used
$("audioFileSenior").addEventListener("change", () => { currentBlob = null; });
$("audioFileEnroll").addEventListener("change", () => { currentBlob = null; });

// ========== INIT ==========
(async function init() {
  setStatusCard(null);
  await apiHealth();
  // Re-check health every 60 s
  setInterval(apiHealth, 60000);
  refreshAudit();
  refreshStats();
})();
