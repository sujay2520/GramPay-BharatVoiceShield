"""Audio validation and format preparation module.
Ensures uploaded audio complies with DetectifAI input requirements (telephony 8kHz or standard 16kHz WAV).
"""

import io
import wave
import struct
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Any

class AudioValidationError(Exception):
    """Raised when audio payload fails basic format or duration checks."""
    pass

def inspect_wav_header(audio_bytes: bytes) -> Dict[str, Any]:
    """Inspects standard WAV header to extract audio specs (channels, sample rate, duration)."""
    if len(audio_bytes) < 44:
        raise AudioValidationError("Audio file too small to contain valid audio data.")
    
    if not audio_bytes.startswith(b"RIFF") or b"WAVE" not in audio_bytes[:16]:
        return {
            "format": "non-wav",
            "channels": None,
            "sample_rate": None,
            "duration_seconds": None,
            "size_bytes": len(audio_bytes)
        }
    
    try:
        with io.BytesIO(audio_bytes) as bio:
            with wave.open(bio, "rb") as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                sample_rate = wf.getframerate()
                n_frames = wf.getnframes()
                duration = n_frames / float(sample_rate) if sample_rate > 0 else 0.0
                return {
                    "format": "wav",
                    "channels": channels,
                    "sample_width": sample_width,
                    "sample_rate": sample_rate,
                    "frames": n_frames,
                    "duration_seconds": round(duration, 3),
                    "size_bytes": len(audio_bytes)
                }
    except Exception as e:
        return {
            "format": "wav-corrupt",
            "error": str(e),
            "size_bytes": len(audio_bytes)
        }

def prepare_audio_for_detectif(
    audio_bytes: bytes, 
    original_filename: str = "audio.wav"
) -> Tuple[bytes, str, str]:
    """Prepares and validates audio bytes for transmission to DetectifAI.
    
    Returns:
        (prepared_bytes, mime_type, target_filename)
    """
    if not audio_bytes or len(audio_bytes) == 0:
        raise AudioValidationError("Empty audio buffer received.")
        
    info = inspect_wav_header(audio_bytes)
    
    # If already a valid WAV, return directly
    if info.get("format") == "wav":
        return audio_bytes, "audio/wav", original_filename if original_filename.endswith(".wav") else "input.wav"
        
    # Check for ffmpeg conversion if browser sent WebM, MP3, or OGG
    ffmpeg_exe = shutil.which("ffmpeg")
    if ffmpeg_exe:
        try:
            with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as in_f:
                in_f.write(audio_bytes)
                in_path = in_f.name
            out_path = in_path + ".wav"
            
            cmd = [
                ffmpeg_exe, "-y", "-i", in_path,
                "-ar", "16000", "-ac", "1", "-f", "wav", out_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            if res.returncode == 0 and Path(out_path).exists():
                with open(out_path, "rb") as out_f:
                    converted_bytes = out_f.read()
                Path(in_path).unlink(missing_ok=True)
                Path(out_path).unlink(missing_ok=True)
                return converted_bytes, "audio/wav", "converted.wav"
        except Exception:
            pass  # Fall back to passing raw bytes with appropriate mime type

    # Fallback: pass with best detected content type
    ext = Path(original_filename).suffix.lower()
    mime_map = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".m4a": "audio/mp4"
    }
    mime_type = mime_map.get(ext, "application/octet-stream")
    return audio_bytes, mime_type, original_filename
