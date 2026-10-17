"""Unit tests for Voice Biometric Enrollment & Acoustic Liveness Engine.
Verifies fundamental pitch (f0), autocorrelation lag, 4kHz vocoder detection,
and deterministic clone detection on voice divergence.
"""

import math
import struct
import unittest
import wave
import io
from pathlib import Path

from backend.voice_enrollment import (
    extract_voice_biometrics,
    enroll_user_voice,
    get_enrolled_profile,
    reset_enrolled_voice,
    evaluate_incoming_audio_against_enrollment
)

def create_synthetic_sine_wav(freq_hz: float = 150.0, duration_sec: float = 1.0, sr: int = 16000) -> bytes:
    """Generates a pure sine wave audio buffer."""
    n_samples = int(duration_sec * sr)
    samples = []
    for i in range(n_samples):
        val = int(32767.0 * 0.6 * math.sin(2.0 * math.pi * freq_hz * i / float(sr)))
        samples.append(val)
    raw = struct.pack(f"<{n_samples}h", *samples)
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(raw)
    return bio.getvalue()


class TestVoiceBiometrics(unittest.TestCase):
    def setUp(self):
        reset_enrolled_voice()

    def tearDown(self):
        reset_enrolled_voice()

    def test_extract_voice_biometrics_pitch(self):
        wav_150 = create_synthetic_sine_wav(freq_hz=150.0, duration_sec=1.0)
        bio = extract_voice_biometrics(wav_150)
        self.assertIsNotNone(bio)
        self.assertAlmostEqual(bio["f0_hz"], 150.0, delta=20.0)
        self.assertGreater(bio["rms"], 0.0)
        self.assertLessEqual(bio["mag_4k"], 10.0)

    def test_enrollment_lifecycle(self):
        wav = create_synthetic_sine_wav(freq_hz=140.0, duration_sec=1.0)
        profile = enroll_user_voice(
            wav_bytes=wav,
            speaker_name="Ramesh Patel",
            speaker_id="senior_user_01",
            lang="kn"
        )
        self.assertTrue(profile["enrolled"])
        self.assertEqual(profile["speaker_id"], "senior_user_01")
        self.assertEqual(profile["lang"], "kn")

        # Check retrieval
        active = get_enrolled_profile()
        self.assertIsNotNone(active)
        self.assertEqual(active["speaker_id"], "senior_user_01")

        # Check reset
        reset_enrolled_voice()
        self.assertIsNone(get_enrolled_profile())

    def test_evaluate_matching_vs_divergent_pitch(self):
        wav_farmer = create_synthetic_sine_wav(freq_hz=130.0, duration_sec=1.0)
        enroll_user_voice(wav_farmer, speaker_name="Ramesh", speaker_id="farmer_01", lang="kn")

        # 1. Matching speaker
        eval_same = evaluate_incoming_audio_against_enrollment(wav_farmer, device="phone1")
        self.assertFalse(eval_same["detection"]["is_synthetic"])
        self.assertTrue(eval_same["verification"]["matched"])
        self.assertLess(eval_same["detection"]["synthetic_score"], 0.20)

        # 2. Divergent speaker (female / different pitch: 260Hz vs 130Hz)
        wav_impostor = create_synthetic_sine_wav(freq_hz=260.0, duration_sec=1.0)
        eval_diff = evaluate_incoming_audio_against_enrollment(wav_impostor, device="phone1")
        self.assertTrue(eval_diff["detection"]["is_synthetic"])
        self.assertFalse(eval_diff["verification"]["matched"])
        self.assertGreaterEqual(eval_diff["detection"]["synthetic_score"], 0.62)

    def test_phone2_scammer_always_flagged(self):
        wav = create_synthetic_sine_wav(freq_hz=140.0, duration_sec=1.0)
        eval_p2 = evaluate_incoming_audio_against_enrollment(wav, device="phone2")
        self.assertTrue(eval_p2["detection"]["is_synthetic"])
        self.assertFalse(eval_p2["verification"]["matched"])
        self.assertGreaterEqual(eval_p2["detection"]["synthetic_score"], 0.62)


if __name__ == "__main__":
    unittest.main()
