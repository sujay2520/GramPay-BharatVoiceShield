"""Generate 3 clean, consented WAV test fixtures for DetectifAI forensics testing.

1. farmer_genuine_16s.wav: 16.0s duration, 16kHz 16-bit mono PCM. (Valid for DetectifAI speaker enrollment which requires >= 15s).
2. farmer_genuine_5s.wav: 5.0s duration, 16kHz 16-bit mono PCM. (Valid for DetectifAI verification/detection which requires >= 4s).
3. farmer_clone_synthetic_5s.wav: 5.0s duration, 16kHz 16-bit mono PCM with synthetic harmonic distortion.
"""

import math
import os
import struct
import wave
from pathlib import Path

DATA_AUDIO_DIR = Path(r"c:\Users\chandan.s\OneDrive\Desktop\Unclone\Backend\data_audio")
SAMPLE_RATE = 16000  # 16kHz standard for Aletheia and Eidos

def generate_audio_fixtures():
    DATA_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    files_to_generate = [
        ("farmer_genuine_16s.wav", 16.0, "genuine"),
        ("farmer_genuine_5s.wav", 5.0, "genuine"),
        ("farmer_clone_synthetic_5s.wav", 5.0, "clone"),
    ]
    
    generated = []
    
    for filename, duration_sec, profile_type in files_to_generate:
        filepath = DATA_AUDIO_DIR / filename
        n_samples = int(duration_sec * SAMPLE_RATE)
        
        with wave.open(str(filepath), "wb") as wf:
            wf.setnchannels(1)       # Mono
            wf.setsampwidth(2)      # 16-bit PCM (2 bytes)
            wf.setframerate(SAMPLE_RATE)
            
            for i in range(n_samples):
                t = float(i) / SAMPLE_RATE
                
                if profile_type == "genuine":
                    # Human vocal cord acoustics (Farmer Smt./Shri Sita Ramachandran)
                    # Natural vocal jitter and micro-flutter around 185 Hz
                    f0 = 185.0 + (1.8 * math.sin(2.0 * math.pi * 5.0 * t)) + (0.5 * math.sin(2.0 * math.pi * 1.7 * t))
                    # Natural syllabic cadence modulation (envelope)
                    envelope = 0.82 + 0.15 * math.sin(2.0 * math.pi * 3.2 * t)
                    
                    val = (
                        0.55 * math.sin(2.0 * math.pi * f0 * t) +
                        0.25 * math.sin(2.0 * math.pi * (f0 * 2.0) * t) +
                        0.12 * math.sin(2.0 * math.pi * (f0 * 3.0) * t) +
                        0.05 * math.sin(2.0 * math.pi * 1200.0 * t) +
                        0.03 * math.sin(2.0 * math.pi * 2400.0 * t)
                    ) * envelope
                elif profile_type == "clone":
                    # Neural vocoder clone: Target pitch 185Hz, rigid phase alignment (zero jitter)
                    # Characteristic 600Hz carrier ripple + high-order harmonic/phase distortion
                    f0 = 185.0
                    harmonic_distortion = 0.04 * (math.sin(2.0 * math.pi * 3200.0 * t) ** 3)
                    val = (
                        0.48 * math.sin(2.0 * math.pi * f0 * t) +
                        0.28 * math.sin(2.0 * math.pi * (f0 * 2.0) * t) +
                        0.10 * math.sin(2.0 * math.pi * (f0 * 3.0) * t) +
                        0.08 * math.sin(2.0 * math.pi * 600.0 * t + 0.5) +  # Neural vocoder carrier ripple
                        harmonic_distortion +
                        0.03 * math.sin(2.0 * math.pi * 4800.0 * t)        # High frequency metallic overtone
                    )
                else:
                    val = 0.0
                
                # Soft-clamping into 16-bit range
                clamped = max(-0.95, min(0.95, val))
                sample_val = int(clamped * 32767.0)
                wf.writeframes(struct.pack("<h", sample_val))
                
        generated.append(filepath)
    
    return generated

def verify_fixtures():
    print("=" * 75)
    print("VERIFYING GENERATED AUDIO FIXTURES WITH PYTHON WAVE MODULE:")
    print("=" * 75)
    
    expected_specs = {
        "farmer_genuine_16s.wav": {"duration": 16.0, "frames": 256000, "rate": 16000, "channels": 1, "sampwidth": 2},
        "farmer_genuine_5s.wav": {"duration": 5.0, "frames": 80000, "rate": 16000, "channels": 1, "sampwidth": 2},
        "farmer_clone_synthetic_5s.wav": {"duration": 5.0, "frames": 80000, "rate": 16000, "channels": 1, "sampwidth": 2},
    }
    
    all_ok = True
    for filename, specs in expected_specs.items():
        filepath = DATA_AUDIO_DIR / filename
        if not filepath.exists():
            print(f"FAILED: {filename} does not exist at {filepath}")
            all_ok = False
            continue
            
        with wave.open(str(filepath), "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            duration = nframes / float(framerate)
            size_bytes = filepath.stat().st_size
            
            channels_match = channels == specs["channels"]
            sampwidth_match = sampwidth == specs["sampwidth"]
            framerate_match = framerate == specs["rate"]
            nframes_match = nframes == specs["frames"]
            duration_match = abs(duration - specs["duration"]) < 1e-6
            
            status = "PASS" if (channels_match and sampwidth_match and framerate_match and nframes_match and duration_match) else "FAIL"
            if status != "PASS":
                all_ok = False
                
            print(f"[{status}] {filename:<32} | {duration:4.1f}s | {framerate}Hz | {channels}ch | {sampwidth*8}-bit | {nframes} frames | {size_bytes} bytes")
            
    print("=" * 75)
    return all_ok

if __name__ == "__main__":
    generate_audio_fixtures()
    ok = verify_fixtures()
    if not ok:
        exit(1)
    print("All fixtures verified successfully.")
