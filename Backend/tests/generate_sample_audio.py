"""Utility to generate clean, valid WAV audio files for local contract testing."""

import math
import struct
import wave
from pathlib import Path

def generate_wav(filepath: str, duration_sec: float = 1.5, freq_hz: float = 440.0, sample_rate: int = 16000):
    """Generates a standard 16-bit PCM mono WAV file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    n_samples = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)        # mono
        wf.setsampwidth(2)       # 16-bit
        wf.setframerate(sample_rate)
        
        for i in range(n_samples):
            # Harmonic frequency wave to mimic human vocal formant
            t = float(i) / sample_rate
            val = 0.6 * math.sin(2.0 * math.pi * freq_hz * t) + 0.3 * math.sin(2.0 * math.pi * (freq_hz * 2) * t)
            sample = int(val * 32767.0)
            wf.writeframes(struct.pack("<h", sample))

if __name__ == "__main__":
    generate_wav("tests/sample_human.wav", duration_sec=2.0, freq_hz=300.0)
    generate_wav("tests/sample_clone.wav", duration_sec=2.0, freq_hz=600.0)
    print("Generated sample WAV files in tests/")
