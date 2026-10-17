"""
verify_localhost.py

Localhost Verification Suite for GramPay (BharatVoice Shield)
Tests all Day 2 endpoints and contract invariants directly against http://localhost:8000.
"""

import sys
import io
import os
import json
import time
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://localhost:8000"

def test_health():
    print("\n[1/7] Testing GET /api/health ...")
    r = requests.get(f"{BASE_URL}/api/health", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data.get("ok") is True, f"ok != True: {data}"
    assert data.get("detectif_reachable") is True, f"detectif not reachable: {data}"
    print(f"  --> OK: detectif_reachable={data.get('detectif_reachable')}, nemotron_configured={data.get('nemotron_configured')}")

def test_credits():
    print("\n[2/7] Testing GET /api/credits ...")
    r = requests.get(f"{BASE_URL}/api/credits", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert "available" in data or "credits" in data, f"Credits missing: {data}"
    creds = data.get("available", data.get("credits"))
    print(f"  --> OK: live credits available = {creds}")

def test_multilingual_challenges():
    print("\n[3/7] Testing GET /api/challenge/new for kn, hi, en ...")
    for lang in ["kn", "hi", "en"]:
        r = requests.get(f"{BASE_URL}/api/challenge/new?lang={lang}", timeout=5)
        assert r.status_code == 200, f"Failed for {lang}: {r.status_code}"
        data = r.json()
        assert data.get("lang") == lang
        assert len(data.get("words", [])) == 4, f"Expected 4 words, got {data.get('words')}"
        assert data.get("challenge_id"), "Missing challenge_id"
        print(f"  --> OK [{lang.upper()}]: challenge_id={data['challenge_id']}, words={data['words']}")

def test_demo_quick_test():
    print("\n[4/7] Testing 1-Click Demo Scenarios (/api/demo/quick-test) ...")
    
    # 4a. Authentic Farmer Voice
    r1 = requests.post(f"{BASE_URL}/api/demo/quick-test/authentic", timeout=10)
    assert r1.status_code == 200, f"Authentic failed: {r1.status_code}"
    d1 = r1.json()
    assert d1.get("decision") == "APPROVE", f"Expected APPROVE, got {d1.get('decision')}"
    assert d1.get("tool", {}).get("status") == "EXECUTED", f"Tool not EXECUTED: {d1}"
    print(f"  --> OK Case 1 (Authentic): decision={d1['decision']}, tool={d1.get('tool', {}).get('status')}")

    # 4b. AI Voice Clone Defense
    r2 = requests.post(f"{BASE_URL}/api/demo/quick-test/clone", timeout=10)
    assert r2.status_code == 200, f"Clone failed: {r2.status_code}"
    d2 = r2.json()
    assert d2.get("decision") in ("BLOCK", "BLOCK_ALERT"), f"Expected BLOCK, got {d2.get('decision')}"
    assert d2.get("tool", {}).get("status") == "LOCKED", f"Tool not LOCKED: {d2}"
    assert d2.get("cost", {}).get("est_inr", 0) > 0, f"Cost not saved: {d2}"
    print(f"  --> OK Case 2 (Clone Attack Blocked): decision={d2['decision']}, tool={d2.get('tool', {}).get('status')}, saved=Rs.{d2.get('cost', {}).get('est_inr')}")

    # 4c. Active Cognitive Challenge
    r3 = requests.post(f"{BASE_URL}/api/demo/quick-test/challenge", timeout=10)
    assert r3.status_code == 200, f"Challenge failed: {r3.status_code}"
    d3 = r3.json()
    assert d3.get("challenge_id"), f"No challenge_id: {d3}"
    print(f"  --> OK Case 3 (Dynamic Challenge): challenge_id={d3['challenge_id']}, phrase={d3.get('phrase')}")

def test_step_up_fix1_flow():
    print("\n[5/7] Testing Step-Up Active Challenge Fix 1 (Cached Audio Execution) ...")
    from backend.multilingual_config import save_pending_challenge, get_pending_challenge
    
    # Create synthetic tone as dummy original payment audio
    fake_audio = b"RIFF" + b"\x00" * 40 + b"WAVEfmt " + b"\x00" * 100
    ch_id = f"test_ch_{int(time.time())}"
    
    # Save pending challenge simulating /api/check EXTRA_CHECK
    save_pending_challenge(
        challenge_id=ch_id,
        audio_bytes=fake_audio,
        speaker_id="farmer_ramesh",
        lang="kn",
        device="phone1",
        source="live_mic"
    )
    assert get_pending_challenge(ch_id) is not None, "Pending challenge not cached!"
    print(f"  --> OK: Initial payment audio cached under challenge_id={ch_id}")

    # Submit challenge audio to /api/challenge/submit
    # Using a 5s genuine test file
    with open("clips/kn/genuine/kannada_farmer_genuine.wav", "rb") as f:
        clip_bytes = f.read()

    files = {"audio": ("challenge.wav", clip_bytes, "audio/wav")}
    data = {
        "challenge_id": ch_id,
        "speaker_id": "farmer_ramesh",
        "response_delay_ms": 650
    }
    r = requests.post(f"{BASE_URL}/api/challenge/submit", files=files, data=data, timeout=15)
    assert r.status_code == 200, f"Submit failed: {r.status_code} {r.text}"
    res = r.json()
    assert "decision" in res, f"No decision: {res}"
    print(f"  --> OK: /api/challenge/submit returned decision={res['decision']}, tool={res.get('tool', {}).get('status')}")

def test_latest_state():
    print("\n[6/7] Testing GET /api/latest-state ...")
    r = requests.get(f"{BASE_URL}/api/latest-state", timeout=5)
    assert r.status_code == 200, f"Latest state failed: {r.status_code}"
    data = r.json()
    assert "events" in data, f"No events list: {data}"
    assert "stats" in data, f"No stats: {data}"
    stats = data["stats"]
    print(f"  --> OK: Total Events={len(data['events'])}, Stats: checks={stats.get('checks')}, pay={stats.get('pay')}, block={stats.get('block')}, saved_inr=Rs.{stats.get('est_inr')}")

def test_assumptions():
    print("\n[7/7] Testing POST /api/assumptions ...")
    payload = {"rs_per_min": 15.0, "minutes": 2.5}
    r = requests.post(f"{BASE_URL}/api/assumptions", json=payload, timeout=5)
    assert r.status_code == 200, f"Assumptions failed: {r.status_code}"
    data = r.json()
    assert data.get("cost", {}).get("est_inr", 0) > 0
    print(f"  --> OK: Updated rate=Rs.{data['cost']['rs_per_min']}/min, call_duration={data['cost']['minutes']}m, total_saved_inr=Rs.{data['cost']['est_inr']}")

    # Restore baseline
    requests.post(f"{BASE_URL}/api/assumptions", json={"rs_per_min": 10.0, "minutes": 2.0}, timeout=5)

if __name__ == "__main__":
    print("=" * 70)
    print("  GRAMPAY: LOCALHOST 8000 COMPREHENSIVE VERIFICATION SUITE")
    print("=" * 70)
    try:
        test_health()
        test_credits()
        test_multilingual_challenges()
        test_demo_quick_test()
        test_step_up_fix1_flow()
        test_latest_state()
        test_assumptions()
        print("\n" + "=" * 70)
        print("  >>> ALL 7 LOCALHOST VERIFICATION SUITES PASSED (100% OK) <<<")
        print("=" * 70)
    except Exception as e:
        print(f"\n[!] Verification Failed: {e}", file=sys.stderr)
        sys.exit(1)
