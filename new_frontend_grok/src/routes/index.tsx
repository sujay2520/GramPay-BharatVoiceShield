import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import {
  Mic,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  Square,
  Upload,
  Lock,
  Unlock,
  Loader2,
  Radio,
} from "lucide-react";
import {
  agentTurn,
  audit,
  checkCall,
  enroll,
  getBackend,
  health,
  issueCredential,
  setBackend,
  stats,
  verifyCredential,
  type CheckResponse,
} from "@/lib/gate-api";

export const Route = createFileRoute("/")({ component: Home });

type Tone = "idle" | "approve" | "block" | "step" | "error";

function toneOf(decision?: string): Tone {
  const d = (decision || "").toUpperCase();
  if (d === "APPROVE") return "approve";
  if (d === "STEP_UP") return "step";
  if (d === "BLOCK" || d === "BLOCK_ALERT") return "block";
  return "idle";
}

function titleOf(decision?: string) {
  const d = (decision || "").toUpperCase();
  if (d === "APPROVE") return "Approved";
  if (d === "BLOCK_ALERT") return "Blocked. Clone alert.";
  if (d === "BLOCK") return "Blocked";
  if (d === "STEP_UP") return "Step-up required";
  return "Ready";
}

function Home() {
  const [backend, setBackendState] = useState("");
  const [busy, setBusy] = useState("");
  const [healthText, setHealthText] = useState("Not checked");
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [name, setName] = useState("");
  const [speakerId, setSpeakerId] = useState("");
  const [action, setAction] = useState("TRANSFER_FUNDS");
  const [amount, setAmount] = useState("50000");
  const [result, setResult] = useState<CheckResponse | null>(null);
  const [err, setErr] = useState("");
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [totals, setTotals] = useState<CheckResponse | null>(null);
  const [cred, setCred] = useState("");
  const [badge, setBadge] = useState<CheckResponse | null>(null);
  const [recording, setRecording] = useState<"senior" | "enroll" | null>(null);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [enrollBlob, setEnrollBlob] = useState<Blob | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    setBackendState(getBackend());
  }, []);

  function saveBackend() {
    setBackend(backend.trim());
    setHealthText("Saved. Check reachability.");
    setHealthOk(null);
  }

  async function onHealth() {
    setBusy("Checking platform…");
    setErr("");
    try {
      const data = await health();
      if (data.error) {
        setHealthOk(false);
        setHealthText(data.error);
      } else if (data.detectif_reachable === true) {
        setHealthOk(true);
        setHealthText("DetectifAI reachable");
      } else if (data.detectif_reachable === false) {
        setHealthOk(false);
        setHealthText("Backend up. DetectifAI not reachable");
      } else {
        setHealthOk(null);
        setHealthText(data.ok ? "Backend ok. DetectifAI unknown" : "Unknown");
      }
    } catch (e) {
      setHealthOk(false);
      setHealthText(e instanceof Error ? e.message : "Unreachable. Gate stays closed.");
    } finally {
      setBusy("");
    }
  }

  async function startRec(which: "senior" | "enroll") {
    setErr("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const rec = new MediaRecorder(stream, { mimeType: mime });
      chunks.current = [];
      rec.ondataavailable = (ev) => {
        if (ev.data.size) chunks.current.push(ev.data);
      };
      rec.onstop = () => {
        const b = new Blob(chunks.current, { type: mime });
        if (which === "enroll") setEnrollBlob(b);
        else setBlob(b);
        stream.getTracks().forEach((t) => t.stop());
        setRecording(null);
      };
      recRef.current = rec;
      rec.start();
      setRecording(which);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Microphone blocked.");
    }
  }

  function stopRec() {
    recRef.current?.stop();
  }

  function apply(data: CheckResponse) {
    if (data.error) {
      setErr(data.error);
      setResult({
        decision: data.fail_closed === false ? "STEP_UP" : "BLOCK",
        reason: data.error,
        fail_closed: true,
      });
      return;
    }
    setErr("");
    setResult(data);
    if (data.speaker_id) setSpeakerId(String(data.speaker_id));
  }

  async function run(label: string, fn: () => Promise<CheckResponse>) {
    setBusy(label);
    setErr("");
    try {
      apply(await fn());
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Request failed";
      setErr(msg);
      setResult({ decision: "BLOCK", reason: msg, fail_closed: true });
    } finally {
      setBusy("");
    }
  }

  async function loadLogs() {
    setBusy("Loading audit…");
    try {
      const a = await audit(30);
      const list = Array.isArray(a)
        ? a
        : ((a as { rows?: unknown; audit?: unknown }).rows ??
          (a as { audit?: unknown }).audit ??
          []);
      setRows(Array.isArray(list) ? (list as Record<string, unknown>[]) : []);
      setTotals(await stats());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Audit unavailable");
    } finally {
      setBusy("");
    }
  }

  const tone: Tone = err && !result?.decision ? "error" : toneOf(result?.decision);
  const card =
    tone === "approve"
      ? "bg-safe-bg text-safe border-safe"
      : tone === "block" || tone === "error"
        ? "bg-alert-bg text-alert border-alert"
        : tone === "step"
          ? "bg-wait-bg text-wait border-wait"
          : "bg-paper text-fg border-line";

  const synth = result?.detection?.synthetic_score;
  const match = result?.verification?.match_score;
  const tool = result?.tool?.status;

  return (
    <main className="min-h-screen px-4 py-5 md:px-8 md:py-8">
      <header className="mx-auto mb-6 flex max-w-6xl flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold tracking-wide text-gold uppercase">UnClone Gate</p>
          <h1 className="font-display text-4xl leading-tight text-ink md:text-5xl">
            Before money moves, the voice is checked.
          </h1>
          <p className="mt-2 max-w-xl text-muted">
            Mrs. Sharma is on the line with her bank’s voice agent to release a ₹50,000 pension transfer.
            A clone of her voice, or a fake bank bot, must not get that tool. DetectifAI has to approve first.
          </p>
        </div>
        <div
          className={`rounded-full border px-4 py-2 text-sm font-semibold ${
            healthOk === true
              ? "border-safe bg-safe-bg text-safe"
              : healthOk === false
                ? "border-alert bg-alert-bg text-alert"
                : "border-line bg-paper text-muted"
          }`}
        >
          <span className="inline-flex items-center gap-2">
            <Radio className="size-4" aria-hidden />
            {healthText}
          </span>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-5 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="rounded-[var(--radius)] border border-line bg-paper p-5 shadow-sm md:p-7">
          <p className="text-sm font-semibold tracking-wide text-muted uppercase">For you</p>
          <h2 className="font-display mt-1 text-3xl text-ink">Your protected line</h2>

          <div className={`mt-5 rounded-[var(--radius)] border-2 px-5 py-8 text-center ${card}`}>
            <div className="mx-auto mb-3 flex size-16 items-center justify-center rounded-full bg-paper/70">
              {tone === "approve" ? (
                <ShieldCheck className="size-9" />
              ) : tone === "block" || tone === "error" ? (
                <ShieldAlert className="size-9" />
              ) : tone === "step" ? (
                <ShieldQuestion className="size-9" />
              ) : (
                <ShieldCheck className="size-9 text-gold" />
              )}
            </div>
            <p className="font-display text-4xl leading-none md:text-5xl">
              {result?.decision ? titleOf(String(result.decision)) : "Tap and speak"}
            </p>
            <p className="mx-auto mt-4 max-w-md text-lg leading-snug">
              {result?.reason ||
                err ||
                "Hold the button, say what you need, then run the check. Nothing here is assumed until the gate answers."}
            </p>
            {result?.agent_reply_text ? (
              <p className="mx-auto mt-3 max-w-md text-base">Assistant: {result.agent_reply_text}</p>
            ) : null}
          </div>

          <div className="mt-5 rounded-2xl border border-line bg-cream px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-semibold text-ink">Calling agent</span>
              <span
                className={`rounded-full px-3 py-1 text-xs font-bold tracking-wide ${
                  badge?.badge === "VERIFIED_AGENT"
                    ? "bg-safe-bg text-safe"
                    : badge?.badge
                      ? "bg-alert-bg text-alert"
                      : "bg-cream-2 text-muted"
                }`}
              >
                {badge?.badge || "NOT CHECKED"}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted">
              {badge?.reason || "A badge appears only after the handshake is verified."}
            </p>
          </div>

          <div className="mt-5 grid gap-3">
            <button
              type="button"
              onClick={() => (recording === "senior" ? stopRec() : startRec("senior"))}
              className={`flex min-h-16 items-center justify-center gap-3 rounded-2xl text-xl font-bold text-paper ${
                recording === "senior" ? "rec-pulse bg-alert" : "bg-ink"
              }`}
            >
              {recording === "senior" ? <Square className="size-6" /> : <Mic className="size-6" />}
              {recording === "senior" ? "Stop" : "Tap and speak"}
            </button>
            <p className="text-center text-sm text-muted">
              {blob ? `Clip ready · ${(blob.size / 1024).toFixed(0)} KB` : "3 to 8 seconds. Or upload a consented clip."}
            </p>
            <label className="flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-line bg-cream text-sm font-semibold text-ink">
              <Upload className="size-4" />
              Upload audio
              <input
                type="file"
                accept="audio/*"
                className="sr-only"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) setBlob(f);
                }}
              />
            </label>
            <div className="grid grid-cols-2 gap-2">
              <select
                value={action}
                onChange={(e) => setAction(e.target.value)}
                className="min-h-12 rounded-xl border border-line bg-paper px-3 text-base"
              >
                <option value="CHECK_BALANCE">Check balance</option>
                <option value="TRANSFER_FUNDS">Transfer funds</option>
              </select>
              <input
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                inputMode="numeric"
                className="min-h-12 rounded-xl border border-line bg-paper px-3 text-base"
                aria-label="Amount in rupees"
              />
            </div>
            <button
              type="button"
              disabled={!!busy}
              onClick={() => {
                if (!blob) return setErr("Record or upload a clip first.");
                if (!speakerId) return setErr("Enroll a voice on the right first.");
                void run("Running the gate…", () => checkCall(blob, speakerId, action, amount));
              }}
              className="min-h-14 rounded-2xl bg-safe text-lg font-bold text-paper disabled:opacity-50"
            >
              Check this voice
            </button>
            <button
              type="button"
              disabled={!!busy}
              onClick={() => {
                if (!blob) return setErr("Record or upload a clip first.");
                if (!speakerId) return setErr("Enroll a voice on the right first.");
                void run("Gate first, then the assistant…", () => agentTurn(blob, speakerId));
              }}
              className="min-h-12 rounded-2xl border border-ink text-base font-semibold text-ink disabled:opacity-50"
            >
              Full assistant turn
            </button>
          </div>
        </section>

        <section className="rounded-[var(--radius)] bg-ink p-5 text-cream md:p-6">
          <p className="text-sm font-semibold tracking-wide text-gold-bright uppercase">Judge console</p>
          <h2 className="font-display mt-1 text-3xl">What the gate actually returned</h2>

          <label className="mt-4 block text-xs font-semibold tracking-wide text-cream-2 uppercase">
            Backend URL
          </label>
          <div className="mt-1 flex gap-2">
            <input
              value={backend}
              onChange={(e) => setBackendState(e.target.value)}
              placeholder="https://your-api.onrender.com"
              className="min-h-11 flex-1 rounded-xl border border-ink-soft bg-ink-soft px-3 text-sm text-cream outline-none"
            />
            <button type="button" onClick={saveBackend} className="min-h-11 rounded-xl bg-gold px-3 text-sm font-bold text-ink">
              Save
            </button>
            <button type="button" onClick={() => void onHealth()} className="min-h-11 rounded-xl border border-cream-2 px-3 text-sm font-semibold">
              Health
            </button>
          </div>

          <div className="mt-4 grid gap-3 rounded-2xl bg-ink-soft p-4">
            <p className="text-xs font-semibold tracking-wide text-gold-bright uppercase">Enroll</p>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Name"
              className="min-h-11 rounded-xl border border-ink bg-ink px-3 text-sm text-cream"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => (recording === "enroll" ? stopRec() : startRec("enroll"))}
                className={`min-h-11 flex-1 rounded-xl text-sm font-bold text-ink ${
                  recording === "enroll" ? "rec-pulse bg-alert text-paper" : "bg-cream"
                }`}
              >
                {recording === "enroll" ? "Stop recording" : "Record enrollment"}
              </button>
              <label className="flex min-h-11 cursor-pointer items-center rounded-xl border border-cream-2 px-3 text-sm">
                File
                <input
                  type="file"
                  accept="audio/*"
                  className="sr-only"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) setEnrollBlob(f);
                  }}
                />
              </label>
            </div>
            <button
              type="button"
              disabled={!!busy}
              onClick={() => {
                if (!name.trim()) return setErr("Enter a name.");
                if (!enrollBlob) return setErr("Record an enrollment clip.");
                void run("Enrolling…", () => enroll(enrollBlob, name.trim()));
              }}
              className="min-h-11 rounded-xl bg-gold text-sm font-bold text-ink disabled:opacity-50"
            >
              Enroll speaker
            </button>
            <p className="break-all text-xs text-cream-2">
              {speakerId ? `speaker_id ${speakerId}` : enrollBlob ? "Clip ready, not enrolled yet." : "No speaker enrolled."}
            </p>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3">
            <Meter label="Synthetic" value={synth} warnHigh />
            <Meter label="Match" value={match} />
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
            <dt className="text-cream-2">Decision</dt>
            <dd className="text-right font-semibold">{result?.decision || "—"}</dd>
            <dt className="text-cream-2">Tool</dt>
            <dd className="flex items-center justify-end gap-1 font-semibold">
              {tool === "EXECUTED" ? <Unlock className="size-4" /> : <Lock className="size-4" />}
              {tool || "LOCKED"}
            </dd>
            <dt className="text-cream-2">Latency</dt>
            <dd className="text-right">
              {result?.detection?.latency_ms ?? "—"} / {result?.verification?.latency_ms ?? "—"} ms
            </dd>
            <dt className="text-cream-2">Steps skipped</dt>
            <dd className="text-right">{fmtNum(result?.cost?.agent_steps_skipped ?? totals?.steps_skipped)}</dd>
            <dt className="text-cream-2">Est. INR</dt>
            <dd className="text-right">
              {fmtInr(result?.cost?.est_inr) ?? fmtInr(totals?.est_inr) ?? "—"}
            </dd>
          </dl>
          <p className="mt-1 text-xs text-cream-2">
            {result?.cost?.assumption || "Assumption comes from the backend, not this page."}
          </p>

          <div className="mt-4 grid gap-2">
            <p className="text-xs font-semibold tracking-wide text-gold-bright uppercase">Credential</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="min-h-10 rounded-lg bg-cream px-3 text-sm font-bold text-ink"
                onClick={() =>
                  void run("Issuing credential…", async () => {
                    const data = await issueCredential();
                    const token = String(data.credential || data.token || "");
                    if (token) setCred(token);
                    return data;
                  })
                }
              >
                Issue
              </button>
              <button
                type="button"
                className="min-h-10 rounded-lg border border-cream-2 px-3 text-sm font-semibold"
                onClick={async () => {
                  if (!cred.trim()) return setErr("No credential to verify.");
                  setBusy("Verifying handshake…");
                  try {
                    const data = await verifyCredential(cred.trim());
                    setBadge(data);
                    setResult(data);
                  } catch (e) {
                    setErr(e instanceof Error ? e.message : "Verify failed");
                  } finally {
                    setBusy("");
                  }
                }}
              >
                Verify
              </button>
              <button
                type="button"
                className="min-h-10 rounded-lg border border-cream-2 px-3 text-sm font-semibold"
                onClick={async () => {
                  if (!cred.trim()) return setErr("Issue a credential, then replay it.");
                  setBusy("Replaying credential…");
                  try {
                    const data = await verifyCredential(cred.trim());
                    setBadge(data);
                    setResult(data);
                  } catch (e) {
                    setErr(e instanceof Error ? e.message : "Replay failed");
                  } finally {
                    setBusy("");
                  }
                }}
              >
                Replay
              </button>
            </div>
            <textarea
              value={cred}
              onChange={(e) => setCred(e.target.value)}
              rows={2}
              placeholder="Signed credential"
              className="w-full rounded-xl border border-ink-soft bg-ink-soft p-2 text-xs text-cream"
            />
          </div>

          <pre className="mt-4 max-h-40 overflow-auto rounded-xl bg-ink-soft p-3 text-xs leading-relaxed text-cream-2">
            {result ? JSON.stringify(result, null, 2) : "Waiting for a real response."}
          </pre>

          <div className="mt-4 flex items-center justify-between">
            <p className="text-xs font-semibold tracking-wide text-gold-bright uppercase">Audit</p>
            <button type="button" onClick={() => void loadLogs()} className="text-xs font-semibold text-gold-bright">
              Refresh
            </button>
          </div>
          <div className="mt-2 max-h-40 overflow-auto rounded-xl border border-ink-soft">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-ink-soft text-cream-2">
                <tr>
                  <th className="p-2 font-medium">Time</th>
                  <th className="p-2 font-medium">Decision</th>
                  <th className="p-2 font-medium">Tool</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="p-3 text-cream-2">
                      Empty. Nothing logged yet.
                    </td>
                  </tr>
                ) : (
                  rows.map((r, i) => (
                    <tr key={i} className="border-t border-ink-soft">
                      <td className="p-2">{String(r.ts || r.time || r.created_at || "—")}</td>
                      <td className="p-2">{String(r.decision || "—")}</td>
                      <td className="p-2">{String(r.tool_status || (r.tool as { status?: string } | undefined)?.status || "—")}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {busy ? (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-ink/50 px-6">
          <div className="flex items-center gap-3 rounded-2xl bg-paper px-5 py-4 text-lg font-semibold text-ink">
            <Loader2 className="size-5 animate-spin" />
            {busy}
          </div>
        </div>
      ) : null}
      {err ? (
        <p className="mx-auto mt-4 max-w-6xl rounded-xl bg-alert-bg px-4 py-3 text-sm font-medium text-alert">
          Fail closed. {err}
        </p>
      ) : null}
    </main>
  );
}

function fmtNum(v: unknown) {
  return typeof v === "number" ? String(v) : "—";
}

function fmtInr(v: unknown) {
  return typeof v === "number" ? `₹${v.toFixed(2)}` : null;
}

function Meter({ label, value, warnHigh }: { label: string; value?: number; warnHigh?: boolean }) {
  const n = typeof value === "number" ? Math.max(0, Math.min(1, value)) : null;
  const hot = n != null && (warnHigh ? n >= 0.5 : n < 0.5);
  return (
    <div className="rounded-2xl bg-ink-soft p-3">
      <div className="flex justify-between text-xs text-cream-2">
        <span>{label}</span>
        <span className="font-semibold text-cream">{n == null ? "—" : `${(n * 100).toFixed(1)}%`}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink">
        <div
          className={`h-full ${hot ? "bg-alert" : "bg-gold-bright"}`}
          style={{ width: n == null ? "0%" : `${n * 100}%` }}
        />
      </div>
    </div>
  );
}
