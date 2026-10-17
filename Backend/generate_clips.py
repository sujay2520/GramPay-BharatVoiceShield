import os
import math
import wave
import struct

BASE_DIR = r"c:\Users\chandan.s\OneDrive\Desktop\Unclone\Backend\clips"
SAMPLE_RATE = 16000
DURATION = 5.0
NUM_SAMPLES = int(SAMPLE_RATE * DURATION)

CLIPS_SPEC = [
    # Kannada
    ("kn", "genuine", "kannada_farmer_genuine.wav", "genuine"),
    ("kn", "imposter", "kannada_imposter.wav", "imposter"),
    ("kn", "clone", "kannada_vocoder_clone.wav", "clone"),
    # Hindi
    ("hi", "genuine", "hindi_farmer_genuine.wav", "genuine"),
    ("hi", "imposter", "hindi_imposter.wav", "imposter"),
    ("hi", "clone", "hindi_vocoder_clone.wav", "clone"),
    # English
    ("en", "genuine", "english_farmer_genuine.wav", "genuine"),
    ("en", "imposter", "english_imposter.wav", "imposter"),
    ("en", "clone", "english_vocoder_clone.wav", "clone"),
]

def generate_pcm_data(profile: str, lang: str) -> bytes:
    cadence_rates = {"kn": 3.2, "hi": 3.6, "en": 3.0}
    cadence = cadence_rates.get(lang, 3.2)
    
    # Acoustic Profiles:
    # genuine: fundamental 130Hz with natural formants
    # imposter: fundamental 210Hz
    # clone: 130Hz with added 4kHz/8kHz harmonic vocoder artifacts
    if profile == "genuine":
        f0 = 130.0
        # Formants (center Hz, bandwidth Hz, amplitude factor)
        formants = [
            (500.0, 90.0, 1.0),
            (1500.0, 140.0, 0.65),
            (2500.0, 180.0, 0.35),
            (3500.0, 220.0, 0.15),
        ]
        has_vocoder_artifact = False
    elif profile == "imposter":
        f0 = 210.0
        # Higher voice profile
        formants = [
            (750.0, 110.0, 1.0),
            (2100.0, 170.0, 0.65),
            (3100.0, 220.0, 0.35),
            (3800.0, 260.0, 0.15),
        ]
        has_vocoder_artifact = False
    elif profile == "clone":
        f0 = 130.0
        formants = [
            (500.0, 90.0, 1.0),
            (1500.0, 140.0, 0.65),
            (2500.0, 180.0, 0.35),
            (3500.0, 220.0, 0.15),
        ]
        has_vocoder_artifact = True
    else:
        raise ValueError(f"Unknown profile: {profile}")

    # Build harmonic table up to Nyquist (8000 Hz)
    harmonics = []
    max_k = int((SAMPLE_RATE / 2.0) / f0)
    for k in range(1, max_k):
        fk = k * f0
        if fk >= (SAMPLE_RATE / 2.0):
            break
        base_decay = 1.0 / math.pow(k, 0.75)
        # Formant resonant filter boost
        formant_boost = 0.15
        for fc, bw, weight in formants:
            d = (fk - fc) / bw
            formant_boost += weight * math.exp(-0.5 * d * d)
        harmonics.append((fk, base_decay * formant_boost))

    fade_samples = int(SAMPLE_RATE * 0.05)  # 50 ms smooth fade in/out
    samples = []
    
    for i in range(NUM_SAMPLES):
        t = i / float(SAMPLE_RATE)
        
        # Fade envelope
        if i < fade_samples:
            fade = i / float(fade_samples)
        elif i > NUM_SAMPLES - fade_samples:
            fade = (NUM_SAMPLES - i) / float(fade_samples)
        else:
            fade = 1.0
            
        # Syllable and phrase natural envelope
        syllable = 0.65 + 0.35 * math.sin(2.0 * math.pi * cadence * t)
        phrase = 0.85 + 0.15 * math.sin(2.0 * math.pi * 0.6 * t)
        env = fade * syllable * phrase
        
        # Pitch modulation: subtle natural human micro-jitter vs robotic clone
        if has_vocoder_artifact:
            # Synthetic / robotic rigid pitch
            pitch_mod = 1.0 + 0.001 * math.sin(2.0 * math.pi * 1.5 * t)
        else:
            # Natural micro-prosody vibrato / drift
            pitch_mod = 1.0 + 0.008 * math.sin(2.0 * math.pi * 4.8 * t)
            
        # Synthesize harmonic voice base
        val = 0.0
        for fk, amp in harmonics:
            val += amp * math.sin(2.0 * math.pi * fk * pitch_mod * t)
            
        # Add vocoder artifacts for clone:
        # 1. 4000 Hz sharp carrier tone (characteristic neural vocoder artifact)
        # 2. 8000 Hz Nyquist alternating artifact ((-1)**i)
        # 3. 4000 Hz harmonic sidebands (ring modulation)
        if has_vocoder_artifact:
            # 4kHz harmonic artifact
            tone_4k = math.sin(2.0 * math.pi * 4000.0 * t)
            # 8kHz Nyquist artifact (alternating sign)
            tone_8k = (-1.0 if (i % 2 == 1) else 1.0)
            # Ring-modulated sideband around 4kHz
            sideband_4k = tone_4k * math.sin(2.0 * math.pi * f0 * t)
            
            vocoder_sum = 0.40 * tone_4k + 0.35 * tone_8k + 0.25 * sideband_4k
            val = 0.70 * val + 0.30 * vocoder_sum
            
        samples.append(val * env)
        
    # Normalize to int16 range with headroom
    max_val = max(abs(s) for s in samples) if samples else 1.0
    scale = 24000.0 / max_val if max_val > 0 else 1.0
    int16_samples = [int(s * scale) for s in samples]
    
    return struct.pack(f"<{len(int16_samples)}h", *int16_samples)

def create_clips():
    created_files = []
    for lang, subfolder, filename, profile in CLIPS_SPEC:
        folder_path = os.path.join(BASE_DIR, lang, subfolder)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, filename)
        
        pcm_bytes = generate_pcm_data(profile, lang)
        
        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)      # mono
            wf.setsampwidth(2)      # 16-bit
            wf.setframerate(SAMPLE_RATE)  # 16kHz
            wf.writeframes(pcm_bytes)
            
        created_files.append((file_path, profile))
    return created_files

def verify_clips():
    results = []
    print("Verifying all clips:")
    for lang, subfolder, filename, profile in CLIPS_SPEC:
        file_path = os.path.join(BASE_DIR, lang, subfolder, filename)
        if not os.path.exists(file_path):
            results.append((file_path, False, "File does not exist"))
            continue
            
        with wave.open(file_path, "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            duration = nframes / float(framerate)
            frames = wf.readframes(nframes)
            
            is_valid = (
                channels == 1 and
                sampwidth == 2 and
                framerate == 16000 and
                nframes == 80000 and
                len(frames) == 160000 and
                abs(duration - 5.0) < 1e-4
            )
            
            status = "VALID" if is_valid else "INVALID"
            detail = f"{channels}ch, {sampwidth*8}bit, {framerate}Hz, {nframes} frames, {duration:.2f}s"
            results.append((file_path, is_valid, detail))
            print(f"[{status}] {file_path} -> {detail}")
            
    all_ok = all(r[1] for r in results)
    print(f"\nVerification summary: {'ALL 9 FILES VALID' if all_ok else 'SOME FILES FAILED'}")
    return all_ok, results

if __name__ == "__main__":
    print(f"Creating directory structure and test audio clips in {BASE_DIR}...")
    create_clips()
    all_ok, results = verify_clips()
    if not all_ok:
        exit(1)
