export type Decision = "APPROVE" | "BLOCK_ALERT" | "STEP_UP" | "BLOCK" | string;

export type CheckResponse = {
  request_id?: string;
  ts?: string;
  decision?: Decision;
  reason?: string;
  detection?: {
    is_synthetic?: boolean;
    synthetic_score?: number;
    raw?: unknown;
    latency_ms?: number;
  };
  verification?: {
    match_score?: number;
    matched?: boolean;
    raw?: unknown;
    latency_ms?: number;
  };
  tool?: { name?: string; status?: string; result?: unknown };
  cost?: {
    agent_steps_skipped?: number;
    agent_seconds_avoided?: number;
    est_inr?: number;
    assumption?: string;
  };
  audit_id?: number;
  transcript?: string;
  agent_reply_text?: string;
  intent?: string;
  speaker_id?: string;
  name?: string;
  badge?: string;
  checks?: Record<string, boolean>;
  error?: string;
  fail_closed?: boolean;
  [key: string]: unknown;
};

const KEY = "unclone.backend";

export function getBackend(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(KEY) || "";
}

export function setBackend(url: string) {
  localStorage.setItem(KEY, url.replace(/\/$/, ""));
}

async function parse(res: Response): Promise<CheckResponse> {
  const text = await res.text();
  let data: CheckResponse = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { error: text || `HTTP ${res.status}`, fail_closed: true };
  }
  if (!res.ok && !data.error) {
    data.error = `HTTP ${res.status}`;
    data.fail_closed = true;
  }
  return data;
}

function base() {
  const b = getBackend();
  if (!b) throw Object.assign(new Error("Set the backend URL in the judge console."), { fail_closed: true });
  return b;
}

export async function health(): Promise<CheckResponse> {
  const res = await fetch(`${base()}/api/health`);
  return parse(res);
}

export async function enroll(audio: Blob, name: string) {
  const fd = new FormData();
  fd.append("audio", audio, "enroll.webm");
  fd.append("name", name);
  return parse(await fetch(`${base()}/api/enroll`, { method: "POST", body: fd }));
}

export async function checkCall(audio: Blob, speakerId: string, action: string, amount: string) {
  const fd = new FormData();
  fd.append("audio", audio, "check.webm");
  fd.append("speaker_id", speakerId);
  fd.append("action", action);
  if (amount) fd.append("amount", amount);
  return parse(await fetch(`${base()}/api/check`, { method: "POST", body: fd }));
}

export async function agentTurn(audio: Blob, speakerId: string) {
  const fd = new FormData();
  fd.append("audio", audio, "turn.webm");
  fd.append("speaker_id", speakerId);
  return parse(await fetch(`${base()}/api/agent/turn`, { method: "POST", body: fd }));
}

export async function issueCredential() {
  return parse(
    await fetch(`${base()}/api/credential/issue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_id: "sbi-pension-bot",
        org: "Demo Bank",
        allowed_actions: ["CHECK_BALANCE", "TRANSFER_FUNDS"],
        limit_inr: 50000,
      }),
    }),
  );
}

export async function verifyCredential(credential: string) {
  return parse(
    await fetch(`${base()}/api/handshake/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential }),
    }),
  );
}

export async function audit(limit = 20) {
  return parse(await fetch(`${base()}/api/audit?limit=${limit}`));
}

export async function stats() {
  return parse(await fetch(`${base()}/api/stats`));
}
