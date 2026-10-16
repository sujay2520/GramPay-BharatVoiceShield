"""Test suite for Day 2 Telephony & Voice Agent Bridge (UnClone Gate).

Validates:
1. ITU-T G.711 mu-law decoding and WAV encapsulation (pure Python, zero C dependencies).
2. Streaming telephony audio buffering and duration thresholds (1.5s gate trigger).
3. Twilio Media Streams protocol parsing and event building.
4. Voice agent pipeline adapters (LiveKit, Pipecat, Bolna).
5. FastAPI REST & WebSocket simulation endpoints.
"""

import io
import json
import base64
import struct
import wave
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from backend.main import app
from backend.telephony_bridge import (
    TelephonyAudioCodec,
    TelephonyAudioBuffer,
    TelephonyGateState,
    UnCloneTelephonyGate,
    TwilioMediaStreamBridge,
    LiveKitUnCloneGateAdapter,
    PipecatUnCloneGateProcessor,
    BolnaTelephonyGateBridge
)


class TestTelephonyCodec(unittest.TestCase):
    """Verifies standard G.711 mu-law codec and audio transformation utilities."""

    def test_mulaw_to_pcm16_conversion(self):
        # 0xFF is mu-law zero/minimum displacement, 0x00 is peak negative, 0x80 is peak positive
        test_mulaw = bytes([0xFF, 0x00, 0x80, 0x55])
        pcm16 = TelephonyAudioCodec.mulaw_to_pcm16(test_mulaw)
        self.assertEqual(len(pcm16), 8)  # 4 samples * 2 bytes = 8 bytes
        samples = struct.unpack("<4h", pcm16)
        self.assertEqual(len(samples), 4)

    def test_empty_mulaw_input(self):
        self.assertEqual(TelephonyAudioCodec.mulaw_to_pcm16(b""), b"")

    def test_pcm16_to_wav_header_validity(self):
        # Generate 0.5s of 8kHz silence
        raw_pcm = b"\x00\x00" * 4000
        wav_bytes = TelephonyAudioCodec.pcm16_to_wav(raw_pcm, sample_rate=8000, channels=1)
        
        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        self.assertIn(b"WAVE", wav_bytes[:16])

        with io.BytesIO(wav_bytes) as bio:
            with wave.open(bio, "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), 8000)
                self.assertEqual(wf.getnframes(), 4000)

    def test_resample_8k_to_16k(self):
        # 10 samples of 8kHz PCM16 -> should produce 20 samples of 16kHz PCM16
        input_pcm = struct.pack("<10h", *range(100, 1100, 100))
        upsampled = TelephonyAudioCodec.resample_8k_to_16k(input_pcm)
        self.assertEqual(len(upsampled), len(input_pcm) * 2)


class TestTelephonyBuffer(unittest.TestCase):
    """Verifies real-time chunk accumulation and 1.5s gating threshold."""

    def test_buffer_accumulation_and_threshold(self):
        # Target: 1.5 seconds @ 8000 Hz = 12000 samples = 24000 PCM bytes
        buf = TelephonyAudioBuffer(sample_rate=8000, gate_target_seconds=1.5)
        self.assertFalse(buf.is_gate_ready())
        self.assertEqual(buf.accumulated_seconds, 0.0)

        # 20ms chunk of 8kHz mu-law = 160 bytes
        chunk_20ms = b"\xFF" * 160

        # Feed 74 chunks (1.48s) -> still not ready
        for _ in range(74):
            buf.add_mulaw_chunk(chunk_20ms)
        self.assertFalse(buf.is_gate_ready())
        self.assertAlmostEqual(buf.accumulated_seconds, 1.48, places=2)

        # Feed 1 more chunk (75 chunks = 1.5s) -> ready!
        buf.add_mulaw_chunk(chunk_20ms)
        self.assertTrue(buf.is_gate_ready())
        self.assertGreaterEqual(buf.accumulated_seconds, 1.5)

    def test_export_wav_from_buffer(self):
        buf = TelephonyAudioBuffer(sample_rate=8000, gate_target_seconds=1.0)
        chunk = b"\x00" * 160
        for _ in range(50):
            buf.add_mulaw_chunk(chunk)
        
        wav_8k = buf.export_wav(target_sample_rate=8000)
        self.assertTrue(wav_8k.startswith(b"RIFF"))

        wav_16k = buf.export_wav(target_sample_rate=16000)
        self.assertTrue(wav_16k.startswith(b"RIFF"))
        # 16kHz output should be larger than 8kHz output
        self.assertGreater(len(wav_16k), len(wav_8k))


class TestTwilioProtocol(unittest.TestCase):
    """Verifies Twilio Media Streams JSON protocol parsing and outbound event generation."""

    def test_parse_and_extract_media(self):
        payload_bytes = b"HelloTwilio8kMuLawAudio"
        b64_payload = base64.b64encode(payload_bytes).decode("ascii")
        
        raw_msg = json.dumps({
            "event": "media",
            "sequenceNumber": "1",
            "media": {
                "track": "inbound",
                "chunk": "42",
                "timestamp": "123456",
                "payload": b64_payload
            },
            "streamSid": "MZ12345"
        })

        parsed = TwilioMediaStreamBridge.parse_twilio_message(raw_msg)
        self.assertEqual(parsed["event"], "media")
        
        extracted_bytes, seq = TwilioMediaStreamBridge.extract_media_payload(parsed)
        self.assertEqual(extracted_bytes, payload_bytes)
        self.assertEqual(seq, 42)

    def test_build_twilio_commands(self):
        media_evt = json.loads(TwilioMediaStreamBridge.build_twilio_media_event("MZ999", b"\x01\x02"))
        self.assertEqual(media_evt["event"], "media")
        self.assertEqual(media_evt["streamSid"], "MZ999")

        clear_evt = json.loads(TwilioMediaStreamBridge.build_twilio_clear_event("MZ999"))
        self.assertEqual(clear_evt["event"], "clear")
        self.assertEqual(clear_evt["streamSid"], "MZ999")

        mark_evt = json.loads(TwilioMediaStreamBridge.build_twilio_mark_event("MZ999", "gate_passed"))
        self.assertEqual(mark_evt["event"], "mark")
        self.assertEqual(mark_evt["mark"]["name"], "gate_passed")

        twiml_hangup = TwilioMediaStreamBridge.build_twilio_hangup_twiml()
        self.assertIn("<Hangup/>", twiml_hangup)
        self.assertIn("Security Alert", twiml_hangup)

        twiml_step_up = TwilioMediaStreamBridge.build_twilio_step_up_twiml()
        self.assertIn("<Gather", twiml_step_up)
        self.assertIn("PIN", twiml_step_up)


class TestVoiceAgentAdapters(unittest.TestCase):
    """Verifies LiveKit, Pipecat, and Bolna adapter logic."""

    def test_livekit_adapter_lifecycle(self):
        adapter = LiveKitUnCloneGateAdapter(session_id="lk_test_session", claimed_speaker="senior_user_01")
        # Send 10 chunks (200ms) -> should report BUFFERING
        dummy_frame = b"\x00\x00" * 320  # 20ms @ 16kHz
        for _ in range(10):
            res = adapter.on_livekit_audio_frame(dummy_frame)
            self.assertEqual(res["action"], "BUFFERING")

    def test_pipecat_processor_lifecycle(self):
        proc = PipecatUnCloneGateProcessor(session_id="pipe_test_session", claimed_speaker="senior_user_01")
        pass_res = proc.process_frame("TextFrame", b"Hello")
        self.assertEqual(pass_res["action"], "PASS_THROUGH")

        dummy_audio = b"\x00\x00" * 320
        res = proc.process_frame("AudioRawFrame", dummy_audio)
        self.assertEqual(res["action"], "BUFFERING")

    def test_bolna_bridge_routing(self):
        bridge = BolnaTelephonyGateBridge(session_id="bolna_test_session")
        chunk = b"\xFF" * 160
        res = bridge.route_twilio_chunk(chunk)
        self.assertEqual(res["route"], "BUFFERING_AT_UNCLONE_GATE")


class TestTelephonyEndpoints(unittest.TestCase):
    """Verifies FastAPI endpoints exposed by telephony_bridge."""

    def setUp(self):
        self.client = TestClient(app)

    def test_architecture_endpoint(self):
        resp = self.client.get("/api/telephony/architecture")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("supported_codecs", data)
        self.assertIn("downstream_voice_agents", data)
        self.assertIn("livekit", data["downstream_voice_agents"])
        self.assertIn("pipecat", data["downstream_voice_agents"])
        self.assertIn("bolna", data["downstream_voice_agents"])

    def test_simulation_endpoint(self):
        resp = self.client.post(
            "/api/telephony/simulate",
            json={
                "session_id": "sim_unit_test_01",
                "speaker_id": "senior_user_01",
                "action": "TRANSFER_FUNDS",
                "codec": "g711_mulaw_8k",
                "chunk_size_bytes": 160,
                "total_chunks": 80,
                "force_clone_attack": False
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["session_id"], "sim_unit_test_01")
        self.assertGreater(data["total_chunks_processed"], 0)
        self.assertIn("downstream_adapters", data)


if __name__ == "__main__":
    unittest.main()
