"""SQLite Audit Logger and Cost Savings Telemetry Storage.
Provides immutable incident records aligned with RBI Model Risk Guidelines and DPDP compliance.
Tracks official live demo counters: checks_run, clones_blocked, agent_steps_skipped, agent_time_saved_inr.
Supports active challenge latency and verdict telemetry for Stage B step-up verification.
"""

import sqlite3
import json
import time
from typing import Dict, Any, List, Optional
from backend.config import SQLITE_DB_PATH, ASSUMED_COST_PER_MIN_INR

def init_db():
    """Initializes SQLite database schemas for audit logs and single-use credentials."""
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Audit records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                speaker_id TEXT,
                action TEXT,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                synthetic_score REAL,
                match_score REAL,
                is_synthetic INTEGER,
                matched INTEGER,
                latency_ms INTEGER,
                tool_status TEXT,
                steps_skipped INTEGER DEFAULT 0,
                seconds_avoided REAL DEFAULT 0.0,
                est_inr REAL DEFAULT 0.0,
                raw_detection TEXT,
                raw_verification TEXT,
                challenge_latency_ms INTEGER DEFAULT NULL,
                challenge_verdict TEXT DEFAULT NULL,
                active_challenge_latency_ms INTEGER DEFAULT NULL,
                active_challenge_verdict TEXT DEFAULT NULL,
                created_at REAL NOT NULL
            )
        """)

        # Schema migration check: ensure active challenge columns exist in existing databases
        cursor.execute("PRAGMA table_info(audit_logs)")
        existing_cols = {col[1] for col in cursor.fetchall()}
        new_cols = [
            ("challenge_latency_ms", "INTEGER DEFAULT NULL"),
            ("challenge_verdict", "TEXT DEFAULT NULL"),
            ("active_challenge_latency_ms", "INTEGER DEFAULT NULL"),
            ("active_challenge_verdict", "TEXT DEFAULT NULL"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE audit_logs ADD COLUMN {col_name} {col_type}")

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
    synth_raw = detection.get("synthetic_score")
    match_raw = verification.get("match_score")
    synth_score = float(synth_raw) if synth_raw is not None else None
    match_score = float(match_raw) if match_raw is not None else None
    is_synth = (1 if detection.get("is_synthetic") else 0) if detection.get("is_synthetic") is not None else None
    matched = (1 if verification.get("matched") else 0) if verification.get("matched") is not None else None
    latency = int((detection.get("latency_ms") or 0) + (verification.get("latency_ms") or 0))

    steps_skipped = int(cost.get("agent_steps_skipped", 0))
    seconds_avoided = float(cost.get("agent_seconds_avoided", 0.0))
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

    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (
                request_id, ts, speaker_id, action, decision, reason,
                synthetic_score, match_score, is_synthetic, matched, latency_ms,
                tool_status, steps_skipped, seconds_avoided, est_inr,
                raw_detection, raw_verification,
                challenge_latency_ms, challenge_verdict,
                active_challenge_latency_ms, active_challenge_verdict,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id, ts, speaker_id, action, decision, reason,
            synth_score, match_score, is_synth, matched, latency,
            tool_status, steps_skipped, seconds_avoided, est_inr,
            json.dumps(detection.get("raw", {})),
            json.dumps(verification.get("raw", {})),
            c_lat, c_verdict,
            c_lat, c_verdict,
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
            WHERE id = ?
        """, (c_lat, c_verdict, c_lat, c_verdict, audit_id))
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
            SELECT id, request_id, ts, speaker_id, action, decision, reason,
                   synthetic_score, match_score, is_synthetic, matched,
                   latency_ms, tool_status, steps_skipped, seconds_avoided, est_inr,
                   challenge_latency_ms, challenge_verdict,
                   active_challenge_latency_ms, active_challenge_verdict
            FROM audit_logs
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
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
                SUM(CASE WHEN decision = 'APPROVE' THEN 1 ELSE 0 END) as total_approved,
                SUM(CASE WHEN decision LIKE 'BLOCK%' THEN 1 ELSE 0 END) as total_blocked,
                SUM(CASE 
                    WHEN decision = 'BLOCK_ALERT' THEN 1
                    WHEN decision LIKE 'BLOCK%' AND (is_synthetic = 1 OR (synthetic_score IS NOT NULL AND synthetic_score >= 0.5)) THEN 1
                    WHEN challenge_verdict IN ('BLOCK', 'CLONE', 'FAIL', 'SYNTHETIC') THEN 1
                    ELSE 0 
                END) as clones_blocked,
                SUM(CASE WHEN decision = 'STEP_UP' THEN 1 ELSE 0 END) as total_step_up,
                SUM(steps_skipped) as total_steps_skipped,
                SUM(seconds_avoided) as total_seconds_avoided,
                SUM(est_inr) as total_est_inr
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

