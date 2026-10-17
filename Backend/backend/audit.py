"""SQLite Audit Logger and Cost Savings Telemetry Storage.
Provides immutable incident records aligned with RBI Model Risk Guidelines and DPDP compliance.
Tracks official live demo counters: checks_run, clones_blocked, agent_steps_skipped, agent_time_saved_inr.
Supports active challenge latency and verdict telemetry for Stage B step-up verification.
Conforms to Day 2 Multilingual Contract specifications.
"""

import sqlite3
import json
import time
from typing import Dict, Any, List, Optional
from backend.config import SQLITE_DB_PATH, ASSUMED_COST_PER_MIN_INR


def init_db():
    """Initializes SQLite database schemas for audit logs and single-use credentials.
    Ensures audit_logs table has event_id TEXT PRIMARY KEY along with all Day 2 contract
    and legacy backward-compatibility columns.
    """
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()

        # Check existing table info if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    event_id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    device TEXT DEFAULT 'phone1',
                    source TEXT DEFAULT 'live_mic',
                    lang TEXT DEFAULT 'kn',
                    decision TEXT NOT NULL,
                    reason_key TEXT DEFAULT NULL,
                    synthetic_score REAL DEFAULT NULL,
                    match_score REAL DEFAULT NULL,
                    detection_latency_ms REAL DEFAULT 0.0,
                    verification_latency_ms REAL DEFAULT 0.0,
                    gate_overhead_ms REAL DEFAULT 0.0,
                    response_delay_ms REAL DEFAULT NULL,
                    transcript_text TEXT DEFAULT NULL,
                    transcript_english TEXT DEFAULT NULL,
                    intent_amount REAL DEFAULT NULL,
                    intent_payee TEXT DEFAULT NULL,
                    tool_status TEXT DEFAULT 'LOCKED',
                    steps_skipped INTEGER DEFAULT 0,
                    est_inr REAL DEFAULT 0.0,
                    credits_remaining INTEGER DEFAULT NULL,
                    badge TEXT DEFAULT NULL,
                    id INTEGER DEFAULT NULL,
                    request_id TEXT DEFAULT NULL,
                    speaker_id TEXT DEFAULT NULL,
                    action TEXT DEFAULT NULL,
                    reason TEXT DEFAULT '',
                    is_synthetic INTEGER DEFAULT NULL,
                    matched INTEGER DEFAULT NULL,
                    latency_ms INTEGER DEFAULT 0,
                    seconds_avoided REAL DEFAULT 0.0,
                    raw_detection TEXT DEFAULT '{}',
                    raw_verification TEXT DEFAULT '{}',
                    challenge_latency_ms INTEGER DEFAULT NULL,
                    challenge_verdict TEXT DEFAULT NULL,
                    active_challenge_latency_ms INTEGER DEFAULT NULL,
                    active_challenge_verdict TEXT DEFAULT NULL,
                    created_at REAL DEFAULT 0.0
                )
            """)
        else:
            cursor.execute("PRAGMA table_info(audit_logs)")
            cols_info = cursor.fetchall()
            existing_cols = {col[1] for col in cols_info}
            pk_cols = [col[1] for col in cols_info if col[5] > 0]

            # If event_id is not primary key, migrate table to have event_id TEXT PRIMARY KEY
            if "event_id" not in pk_cols:
                cursor.execute("""
                    CREATE TABLE audit_logs_new (
                        event_id TEXT PRIMARY KEY,
                        ts TEXT NOT NULL,
                        device TEXT DEFAULT 'phone1',
                        source TEXT DEFAULT 'live_mic',
                        lang TEXT DEFAULT 'kn',
                        decision TEXT NOT NULL,
                        reason_key TEXT DEFAULT NULL,
                        synthetic_score REAL DEFAULT NULL,
                        match_score REAL DEFAULT NULL,
                        detection_latency_ms REAL DEFAULT 0.0,
                        verification_latency_ms REAL DEFAULT 0.0,
                        gate_overhead_ms REAL DEFAULT 0.0,
                        response_delay_ms REAL DEFAULT NULL,
                        transcript_text TEXT DEFAULT NULL,
                        transcript_english TEXT DEFAULT NULL,
                        intent_amount REAL DEFAULT NULL,
                        intent_payee TEXT DEFAULT NULL,
                        tool_status TEXT DEFAULT 'LOCKED',
                        steps_skipped INTEGER DEFAULT 0,
                        est_inr REAL DEFAULT 0.0,
                        credits_remaining INTEGER DEFAULT NULL,
                        badge TEXT DEFAULT NULL,
                        id INTEGER DEFAULT NULL,
                        request_id TEXT DEFAULT NULL,
                        speaker_id TEXT DEFAULT NULL,
                        action TEXT DEFAULT NULL,
                        reason TEXT DEFAULT '',
                        is_synthetic INTEGER DEFAULT NULL,
                        matched INTEGER DEFAULT NULL,
                        latency_ms INTEGER DEFAULT 0,
                        seconds_avoided REAL DEFAULT 0.0,
                        raw_detection TEXT DEFAULT '{}',
                        raw_verification TEXT DEFAULT '{}',
                        challenge_latency_ms INTEGER DEFAULT NULL,
                        challenge_verdict TEXT DEFAULT NULL,
                        active_challenge_latency_ms INTEGER DEFAULT NULL,
                        active_challenge_verdict TEXT DEFAULT NULL,
                        created_at REAL DEFAULT 0.0
                    )
                """)
                col_list = [
                    "ts", "device", "source", "lang", "decision", "reason_key",
                    "synthetic_score", "match_score", "detection_latency_ms", "verification_latency_ms",
                    "gate_overhead_ms", "response_delay_ms", "transcript_text", "transcript_english",
                    "intent_amount", "intent_payee", "tool_status", "steps_skipped", "est_inr",
                    "credits_remaining", "badge", "id", "request_id", "speaker_id", "action", "reason",
                    "is_synthetic", "matched", "latency_ms", "seconds_avoided", "raw_detection", "raw_verification",
                    "challenge_latency_ms", "challenge_verdict", "active_challenge_latency_ms", "active_challenge_verdict", "created_at"
                ]
                common_cols = [c for c in col_list if c in existing_cols]
                common_str = ", ".join(common_cols)
                cursor.execute(f"""
                    INSERT OR IGNORE INTO audit_logs_new (event_id, {common_str})
                    SELECT COALESCE(event_id, request_id, 'evt_' || id), {common_str}
                    FROM audit_logs
                """)
                cursor.execute("DROP TABLE audit_logs")
                cursor.execute("ALTER TABLE audit_logs_new RENAME TO audit_logs")
            else:
                # Add any missing columns if needed
                required_cols = [
                    ("event_id", "TEXT PRIMARY KEY"),
                    ("ts", "TEXT DEFAULT ''"),
                    ("device", "TEXT DEFAULT 'phone1'"),
                    ("source", "TEXT DEFAULT 'live_mic'"),
                    ("lang", "TEXT DEFAULT 'kn'"),
                    ("decision", "TEXT DEFAULT 'BLOCK'"),
                    ("reason_key", "TEXT DEFAULT NULL"),
                    ("synthetic_score", "REAL DEFAULT NULL"),
                    ("match_score", "REAL DEFAULT NULL"),
                    ("detection_latency_ms", "REAL DEFAULT 0.0"),
                    ("verification_latency_ms", "REAL DEFAULT 0.0"),
                    ("gate_overhead_ms", "REAL DEFAULT 0.0"),
                    ("response_delay_ms", "REAL DEFAULT NULL"),
                    ("transcript_text", "TEXT DEFAULT NULL"),
                    ("transcript_english", "TEXT DEFAULT NULL"),
                    ("intent_amount", "REAL DEFAULT NULL"),
                    ("intent_payee", "TEXT DEFAULT NULL"),
                    ("tool_status", "TEXT DEFAULT 'LOCKED'"),
                    ("steps_skipped", "INTEGER DEFAULT 0"),
                    ("est_inr", "REAL DEFAULT 0.0"),
                    ("credits_remaining", "INTEGER DEFAULT NULL"),
                    ("badge", "TEXT DEFAULT NULL"),
                    ("id", "INTEGER DEFAULT NULL"),
                    ("request_id", "TEXT DEFAULT NULL"),
                    ("speaker_id", "TEXT DEFAULT NULL"),
                    ("action", "TEXT DEFAULT NULL"),
                    ("reason", "TEXT DEFAULT ''"),
                    ("is_synthetic", "INTEGER DEFAULT NULL"),
                    ("matched", "INTEGER DEFAULT NULL"),
                    ("latency_ms", "INTEGER DEFAULT 0"),
                    ("seconds_avoided", "REAL DEFAULT 0.0"),
                    ("raw_detection", "TEXT DEFAULT '{}'"),
                    ("raw_verification", "TEXT DEFAULT '{}'"),
                    ("challenge_latency_ms", "INTEGER DEFAULT NULL"),
                    ("challenge_verdict", "TEXT DEFAULT NULL"),
                    ("active_challenge_latency_ms", "INTEGER DEFAULT NULL"),
                    ("active_challenge_verdict", "TEXT DEFAULT NULL"),
                    ("created_at", "REAL DEFAULT 0.0"),
                ]
                for col_name, col_type in required_cols:
                    if col_name not in existing_cols:
                        cursor.execute(f"ALTER TABLE audit_logs ADD COLUMN {col_name} {col_type}")

        # Trigger ensuring id and request_id are never NULL (synced from rowid and event_id)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS audit_logs_sync_compat AFTER INSERT ON audit_logs
            FOR EACH ROW
            BEGIN
                UPDATE audit_logs 
                SET id = COALESCE(NEW.id, rowid),
                    request_id = COALESCE(NEW.request_id, NEW.event_id)
                WHERE rowid = NEW.rowid AND (NEW.id IS NULL OR NEW.request_id IS NULL);
            END;
        """)

        # Single-use credential registry (prevents replay attacks)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS used_credentials (
                jti TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                org TEXT NOT NULL,
                used_at REAL NOT NULL
            )
        """)
        conn.commit()


# Ensure database exists upon module import
init_db()


def log_audit_event(
    request_id: str,
    ts: str,
    speaker_id: Optional[str],
    action: str,
    decision: str,
    reason: str,
    detection: Dict[str, Any],
    verification: Dict[str, Any],
    tool_status: str,
    cost: Dict[str, Any],
    challenge_latency_ms: Optional[int] = None,
    challenge_verdict: Optional[str] = None,
    active_challenge_latency_ms: Optional[int] = None,
    active_challenge_verdict: Optional[str] = None,
    active_challenge: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> int:
    """Logs an audit event to the SQLite database. Preserves backward compatibility
    with legacy test suites while populating the new 22-column contract schema.
    Returns integer audit row ID.
    """
    synth_raw = detection.get("synthetic_score") if detection.get("synthetic_score") is not None else detection.get("score")
    match_raw = verification.get("match_score") if verification.get("match_score") is not None else (verification.get("similarity") if verification.get("similarity") is not None else verification.get("score"))
    synth_score = float(synth_raw) if synth_raw is not None else None
    match_score = float(match_raw) if match_raw is not None else None
    is_synth = (1 if detection.get("is_synthetic") else 0) if detection.get("is_synthetic") is not None else ((1 if synth_score >= 0.5 else 0) if synth_score is not None else None)
    matched = (1 if verification.get("matched") else 0) if verification.get("matched") is not None else ((1 if match_score >= 0.5 else 0) if match_score is not None else None)
    det_lat = float(detection.get("latency_ms") or 0.0)
    ver_lat = float(verification.get("latency_ms") or 0.0)
    latency = int(det_lat + ver_lat)

    steps_skipped = int(cost.get("agent_steps_skipped", cost.get("steps_skipped", 0)))
    seconds_avoided = float(cost.get("agent_seconds_avoided", cost.get("seconds_avoided", 0.0)))
    est_inr = float(cost.get("est_inr", 0.0))

    # Resolve active challenge telemetry
    c_dict = active_challenge or kwargs.get("challenge") or {}
    c_lat = challenge_latency_ms
    if c_lat is None:
        c_lat = active_challenge_latency_ms
    if c_lat is None:
        c_lat = c_dict.get("latency_ms") or c_dict.get("latency") or kwargs.get("challenge_latency")

    c_verdict = challenge_verdict
    if c_verdict is None:
        c_verdict = active_challenge_verdict
    if c_verdict is None:
        c_verdict = c_dict.get("verdict") or kwargs.get("verdict")

    event_id = kwargs.get("event_id") or request_id or f"req_{int(time.time()*1000)}"

    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO audit_logs (
                event_id, ts, device, source, lang, decision, reason_key,
                synthetic_score, match_score, detection_latency_ms, verification_latency_ms,
                gate_overhead_ms, response_delay_ms, transcript_text, transcript_english,
                intent_amount, intent_payee, tool_status, steps_skipped, est_inr,
                credits_remaining, badge,
                request_id, speaker_id, action, reason, is_synthetic, matched, latency_ms,
                seconds_avoided, raw_detection, raw_verification,
                challenge_latency_ms, challenge_verdict, active_challenge_latency_ms, active_challenge_verdict,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            ts,
            kwargs.get("device", "phone1"),
            kwargs.get("source", "live_mic"),
            kwargs.get("lang", "kn"),
            decision,
            kwargs.get("reason_key") or ("approved" if decision in ("APPROVE", "PAY") else ("synthetic_blocked" if "BLOCK" in decision else "uncertain_challenge")),
            synth_score,
            match_score,
            det_lat,
            ver_lat,
            float(kwargs.get("gate_overhead_ms") or 0.0),
            kwargs.get("response_delay_ms"),
            kwargs.get("transcript_text"),
            kwargs.get("transcript_english"),
            kwargs.get("intent_amount"),
            kwargs.get("intent_payee"),
            tool_status,
            steps_skipped,
            est_inr,
            kwargs.get("credits_remaining"),
            kwargs.get("badge"),
            request_id,
            speaker_id,
            action,
            reason,
            is_synth,
            matched,
            latency,
            seconds_avoided,
            json.dumps(detection.get("raw", {})),
            json.dumps(verification.get("raw", {})),
            c_lat,
            c_verdict,
            c_lat,
            c_verdict,
            time.time()
        ))
        conn.commit()
        return cursor.lastrowid


def update_audit_challenge(
    audit_id: int,
    challenge_latency_ms: Optional[int] = None,
    challenge_verdict: Optional[str] = None,
    active_challenge_latency_ms: Optional[int] = None,
    active_challenge_verdict: Optional[str] = None
) -> bool:
    """Updates an existing audit log entry with Stage B active challenge latency and verdict."""
    c_lat = challenge_latency_ms if challenge_latency_ms is not None else active_challenge_latency_ms
    c_verdict = challenge_verdict if challenge_verdict is not None else active_challenge_verdict
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE audit_logs
            SET challenge_latency_ms = ?,
                challenge_verdict = ?,
                active_challenge_latency_ms = ?,
                active_challenge_verdict = ?
            WHERE id = ? OR rowid = ?
        """, (c_lat, c_verdict, c_lat, c_verdict, audit_id, audit_id))
        conn.commit()
        return cursor.rowcount > 0


def get_recent_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent audit logs for the Judge Telemetry Console.
    Includes both legacy keys, Section 4 contract keys, and active challenge telemetry.
    """
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, request_id, event_id, ts, speaker_id, action, decision, reason,
                   synthetic_score, match_score, is_synthetic, matched,
                   latency_ms, tool_status, steps_skipped, seconds_avoided, est_inr,
                   challenge_latency_ms, challenge_verdict,
                   active_challenge_latency_ms, active_challenge_verdict
            FROM audit_logs
            ORDER BY COALESCE(id, rowid) DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("id") is None and "rowid" in d:
                d["id"] = d["rowid"]
            # Add contract keys from Blueprint Section 4
            d["time"] = d["ts"]
            d["latency"] = d["latency_ms"]
            d["scores"] = {
                "synthetic": d["synthetic_score"],
                "match": d["match_score"]
            }
            d["blocked_parameters"] = {
                "action": d["action"],
                "speaker_id": d["speaker_id"]
            } if d["tool_status"] == "LOCKED" else None

            c_lat = d.get("challenge_latency_ms") if d.get("challenge_latency_ms") is not None else d.get("active_challenge_latency_ms")
            c_verdict = d.get("challenge_verdict") if d.get("challenge_verdict") is not None else d.get("active_challenge_verdict")
            d["challenge_latency_ms"] = c_lat
            d["challenge_verdict"] = c_verdict
            d["active_challenge_latency_ms"] = c_lat
            d["active_challenge_verdict"] = c_verdict
            d["challenge_latency"] = c_lat
            d["verdict"] = c_verdict
            result.append(d)
        return result


def get_telemetry_stats(limit: int = 50) -> Dict[str, Any]:
    """Computes total counts, approvals, blocks, and operational cost savings.
    Returns the 4 official live demo counters from Slide 4:
      1. checks_run (total checks evaluated)
      2. clones_blocked (total synthetic clones caught)
      3. agent_steps_skipped (conversational turns saved)
      4. agent_time_saved_inr (total INR saved at Rs 10/min)
    Includes detailed logs and backwards-compatible contract aliases.
    """
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_checks,
                SUM(CASE WHEN UPPER(decision) IN ('APPROVE', 'PAY') THEN 1 ELSE 0 END) as total_approved,
                SUM(CASE WHEN UPPER(decision) LIKE 'BLOCK%' THEN 1 ELSE 0 END) as total_blocked,
                SUM(CASE 
                    WHEN decision = 'BLOCK_ALERT' THEN 1
                    WHEN decision LIKE 'BLOCK%' AND (is_synthetic = 1 OR (synthetic_score IS NOT NULL AND synthetic_score >= 0.5)) THEN 1
                    WHEN challenge_verdict IN ('BLOCK', 'CLONE', 'FAIL', 'SYNTHETIC') THEN 1
                    ELSE 0 
                END) as clones_blocked,
                SUM(CASE WHEN UPPER(decision) IN ('STEP_UP', 'EXTRA_CHECK') THEN 1 ELSE 0 END) as total_step_up,
                SUM(COALESCE(steps_skipped, 0)) as total_steps_skipped,
                SUM(COALESCE(seconds_avoided, 0.0)) as total_seconds_avoided,
                SUM(COALESCE(est_inr, 0.0)) as total_est_inr
            FROM audit_logs
        """)
        row = cursor.fetchone()

        total_checks = int(row[0] or 0)
        total_approved = int(row[1] or 0)
        total_blocked = int(row[2] or 0)
        clones_blocked = int(row[3] or 0)
        total_step_up = int(row[4] or 0)
        steps_skipped = int(row[5] or 0)
        seconds_avoided = float(row[6] or 0.0)
        est_inr = round(float(row[7] or 0.0), 2)

        detailed_logs = get_recent_audit_logs(limit=limit)

        return {
            # 4 Official Live Demo Counters (Slide 4)
            "checks_run": total_checks,
            "clones_blocked": clones_blocked,
            "agent_steps_skipped": steps_skipped,
            "agent_time_saved_inr": est_inr,

            # Detailed logs
            "logs": detailed_logs,
            "detailed_logs": detailed_logs,

            # Blueprint Section 4 Totals
            "checks": total_checks,
            "blocks": total_blocked,
            "approvals": total_approved,
            "steps_skipped": steps_skipped,
            "seconds_avoided": seconds_avoided,
            "est_inr": est_inr,

            # Extended / Frontend telemetry compatibility keys
            "total_checks": total_checks,
            "total_approved": total_approved,
            "total_blocked": total_blocked,
            "total_step_up": total_step_up,
            "agent_seconds_avoided": seconds_avoided,
            "est_cost_savings_inr": est_inr,
            "assumption": f"Rs {ASSUMED_COST_PER_MIN_INR:.2f} per min (editable)"
        }


def record_used_credential(jti: str, agent_id: str, org: str) -> bool:
    """Records a single-use token JTI. Returns False if already used (replay attack)."""
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO used_credentials (jti, agent_id, org, used_at) VALUES (?, ?, ?, ?)",
                (jti, agent_id, org, time.time())
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Token was already recorded! Replay attempt!


def reset_audit_logs() -> bool:
    """Resets the audit logs and used credentials tables for live demo resets."""
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audit_logs")
        cursor.execute("DELETE FROM used_credentials")
        conn.commit()
    return True


# ==============================================================================
# Day 2 Contract Methods (/api/latest-state, /api/assumptions)
# ==============================================================================
def record_contract_event(event_dict: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
    """Records an event in the exact Day 2 Contract shape.
    Accepts event_dict dictionary (or keyword args).
    Ensures all 22 required columns are cleanly populated in SQLite audit database.
    """
    event = dict(event_dict) if event_dict is not None else dict(kwargs.get("event", kwargs))

    det = event.get("detection") if isinstance(event.get("detection"), dict) else {}
    ver = event.get("verification") if isinstance(event.get("verification"), dict) else {}
    tool = event.get("tool") if isinstance(event.get("tool"), dict) else {}
    cost = event.get("cost") if isinstance(event.get("cost"), dict) else {}
    transcript = event.get("transcript") if isinstance(event.get("transcript"), dict) else {}
    intent = event.get("intent") if isinstance(event.get("intent"), dict) else {}

    event_id = event.get("event_id") or event.get("request_id") or f"req_{int(time.time()*1000)}"
    ts = event.get("ts") or event.get("time") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    device = event.get("device") or "phone1"
    source = event.get("source") or "live_mic"
    lang = event.get("lang") or "kn"
    decision = event.get("decision") or "BLOCK"
    reason_key = event.get("reason_key") or "api_error"

    synth_raw = event.get("synthetic_score") if event.get("synthetic_score") is not None else det.get("synthetic_score", det.get("score"))
    match_raw = event.get("match_score") if event.get("match_score") is not None else ver.get("match_score", ver.get("similarity", ver.get("score")))
    synth_score = float(synth_raw) if synth_raw is not None else None
    match_score = float(match_raw) if match_raw is not None else None

    det_lat = float(event.get("detection_latency_ms") if event.get("detection_latency_ms") is not None else det.get("latency_ms", 0.0))
    ver_lat = float(event.get("verification_latency_ms") if event.get("verification_latency_ms") is not None else ver.get("latency_ms", 0.0))
    gate_overhead_ms = float(event.get("gate_overhead_ms") or 0.0)
    response_delay_ms = event.get("response_delay_ms")

    transcript_text = event.get("transcript_text") if event.get("transcript_text") is not None else transcript.get("text")
    transcript_english = event.get("transcript_english") if event.get("transcript_english") is not None else transcript.get("english")

    intent_amount = event.get("intent_amount") if event.get("intent_amount") is not None else intent.get("amount")
    intent_payee = event.get("intent_payee") if event.get("intent_payee") is not None else intent.get("payee")

    tool_status = event.get("tool_status") if event.get("tool_status") is not None else tool.get("status", "LOCKED")
    steps_skipped = int(event.get("steps_skipped") if event.get("steps_skipped") is not None else cost.get("steps_skipped", cost.get("agent_steps_skipped", 0)))
    est_inr = float(event.get("est_inr") if event.get("est_inr") is not None else cost.get("est_inr", 0.0))
    seconds_avoided = float(event.get("seconds_avoided") if event.get("seconds_avoided") is not None else cost.get("seconds_avoided", (120.0 if steps_skipped else 0.0)))
    credits_remaining = event.get("credits_remaining")
    badge = event.get("badge")

    speaker_id = event.get("speaker_id")
    action = intent.get("action") if isinstance(intent, dict) and intent.get("action") else event.get("action", "TRANSFER_FUNDS")
    reason = event.get("reason", "")
    is_synth = 1 if (synth_score is not None and synth_score >= 0.5) else 0
    matched = 1 if (match_score is not None and match_score >= 0.5) else 0

    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO audit_logs (
                event_id, ts, device, source, lang, decision, reason_key,
                synthetic_score, match_score, detection_latency_ms, verification_latency_ms,
                gate_overhead_ms, response_delay_ms, transcript_text, transcript_english,
                intent_amount, intent_payee, tool_status, steps_skipped, est_inr,
                credits_remaining, badge,
                request_id, speaker_id, action, reason, is_synthetic, matched, latency_ms,
                seconds_avoided, raw_detection, raw_verification,
                challenge_latency_ms, challenge_verdict, active_challenge_latency_ms, active_challenge_verdict,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            ts,
            device,
            source,
            lang,
            decision,
            reason_key,
            synth_score,
            match_score,
            det_lat,
            ver_lat,
            gate_overhead_ms,
            response_delay_ms,
            transcript_text,
            transcript_english,
            intent_amount,
            intent_payee,
            tool_status,
            steps_skipped,
            est_inr,
            credits_remaining,
            badge,
            event_id,
            speaker_id,
            action,
            reason,
            is_synth,
            matched,
            int(det_lat + ver_lat),
            seconds_avoided,
            json.dumps(det.get("raw") or {}),
            json.dumps(ver.get("raw") or {}),
            None,
            None,
            None,
            None,
            time.time()
        ))
        conn.commit()


def get_events_since(since_event_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Returns events occurring strictly after `since_event_id` in the Day 2 Contract shape.
    Each event dictionary contains all 22 required columns as well as nested contract objects.
    """
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        threshold_rowid = 0
        if since_event_id:
            cursor.execute(
                "SELECT rowid FROM audit_logs WHERE event_id = ? OR request_id = ? ORDER BY rowid DESC LIMIT 1",
                (since_event_id, since_event_id)
            )
            r = cursor.fetchone()
            if r:
                threshold_rowid = r["rowid"]

        cursor.execute("""
            SELECT rowid, * FROM audit_logs
            WHERE rowid > ?
            ORDER BY rowid ASC
            LIMIT ?
        """, (threshold_rowid, limit))

        rows = cursor.fetchall()
        events = []
        for row in rows:
            d = dict(row)
            event_id = d.get("event_id") or d.get("request_id")
            device = d.get("device") or "phone1"
            source = d.get("source") or "live_mic"
            lang = d.get("lang") or "kn"
            decision = d.get("decision")
            reason_key = d.get("reason_key") or "approved"
            synth_score = d.get("synthetic_score")
            match_score = d.get("match_score")
            det_lat = float(d.get("detection_latency_ms") or d.get("latency_ms") or 0.0)
            ver_lat = float(d.get("verification_latency_ms") or 0.0)
            gate_overhead = float(d.get("gate_overhead_ms") or 0.0)
            resp_delay = d.get("response_delay_ms")
            t_text = d.get("transcript_text")
            t_eng = d.get("transcript_english")
            i_amount = d.get("intent_amount")
            i_payee = d.get("intent_payee")
            tool_stat = d.get("tool_status") or "LOCKED"
            steps_sk = int(d.get("steps_skipped") or 0)
            est_inr_val = float(d.get("est_inr") or 0.0)
            credits_rem = d.get("credits_remaining")
            badge_val = d.get("badge")

            raw_det = {}
            if d.get("raw_detection"):
                try:
                    raw_det = json.loads(d["raw_detection"])
                except Exception:
                    pass
            raw_ver = {}
            if d.get("raw_verification"):
                try:
                    raw_ver = json.loads(d["raw_verification"])
                except Exception:
                    pass

            c_lat = d.get("challenge_latency_ms") if d.get("challenge_latency_ms") is not None else d.get("active_challenge_latency_ms")
            c_verdict = d.get("challenge_verdict") if d.get("challenge_verdict") is not None else d.get("active_challenge_verdict")

            events.append({
                # All 22 contract columns
                "event_id": event_id,
                "ts": d.get("ts"),
                "device": device,
                "source": source,
                "lang": lang,
                "decision": decision,
                "reason_key": reason_key,
                "synthetic_score": synth_score,
                "match_score": match_score,
                "detection_latency_ms": det_lat,
                "verification_latency_ms": ver_lat,
                "gate_overhead_ms": gate_overhead,
                "response_delay_ms": resp_delay,
                "transcript_text": t_text,
                "transcript_english": t_eng,
                "intent_amount": i_amount,
                "intent_payee": i_payee,
                "tool_status": tool_stat,
                "steps_skipped": steps_sk,
                "est_inr": est_inr_val,
                "credits_remaining": credits_rem,
                "badge": badge_val,

                # Nested Day 2 contract structures
                "reason": d.get("reason") or "",
                "detection": {
                    "synthetic_score": synth_score,
                    "latency_ms": det_lat,
                    "raw": raw_det
                },
                "verification": {
                    "match_score": match_score,
                    "latency_ms": ver_lat,
                    "raw": raw_ver
                },
                "gate_overhead_ms": gate_overhead,
                "challenge": {
                    "latency_ms": c_lat,
                    "verdict": c_verdict
                } if (c_lat is not None or c_verdict is not None) else None,
                "transcript": {
                    "text": t_text,
                    "english": t_eng
                } if t_text else None,
                "intent": {
                    "amount": i_amount,
                    "payee": i_payee
                } if i_amount is not None else None,
                "tool": {
                    "name": "pay_upi",
                    "status": tool_stat
                },
                "cost": {
                    "steps_skipped": steps_sk,
                    "est_inr": est_inr_val,
                    "assumption": {"rs_per_min": 10.0, "minutes": 2.0}
                }
            })
        return events


def get_contract_stats(assumed_rs_per_min: float = 10.0, assumed_minutes: float = 2.0) -> Dict[str, Any]:
    """Returns official stats conforming to GET /api/latest-state contract:
    { checks, pay, extra, block, steps_skipped, est_inr }
    """
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_checks,
                SUM(CASE WHEN UPPER(decision) IN ('PAY', 'APPROVE') THEN 1 ELSE 0 END) as total_pay,
                SUM(CASE WHEN UPPER(decision) IN ('EXTRA_CHECK', 'STEP_UP') THEN 1 ELSE 0 END) as total_extra,
                SUM(CASE WHEN UPPER(decision) LIKE 'BLOCK%' THEN 1 ELSE 0 END) as total_block,
                SUM(COALESCE(steps_skipped, 0)) as total_steps_skipped
            FROM audit_logs
        """)
        row = cursor.fetchone()
        checks = int(row[0] or 0)
        pay = int(row[1] or 0)
        extra = int(row[2] or 0)
        block = int(row[3] or 0)
        steps_skipped = int(row[4] or 0)
        est_inr = round(float(steps_skipped * assumed_minutes * assumed_rs_per_min), 2)

        return {
            "checks": checks,
            "pay": pay,
            "extra": extra,
            "block": block,
            "steps_skipped": steps_skipped,
            "est_inr": est_inr
        }
