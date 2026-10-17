"""Audio validation and format preparation module.
Ensures uploaded audio complies with DetectifAI input requirements (telephony 8kHz or standard 16kHz WAV).
"""

import io
import wave
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
    
    # Keep suitable WAV unchanged. Convert telephony 8 kHz, stereo, and other
    # WAV variants to the same 16 kHz mono PCM format used by the browser mic.
    if (
        info.get("format") == "wav"
        and info.get("channels") == 1
        and info.get("sample_width") == 2
        and info.get("sample_rate") == 16000
    ):
        if (info.get("duration_seconds") or 0) < 3.0:
            raise AudioValidationError("Voice sample must contain at least 3 seconds of audio.")
        return audio_bytes, "audio/wav", original_filename if original_filename.endswith(".wav") else "input.wav"
        
    # Prefer system ffmpeg, with a portable bundled binary as fallback.
    ffmpeg_exe = shutil.which("ffmpeg")
    if not ffmpeg_exe:
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            ffmpeg_exe = None
    if ffmpeg_exe:
        in_path = out_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as in_f:
                in_f.write(audio_bytes)
                in_path = in_f.name
            out_path = in_path + ".wav"
            
            cmd = [
                ffmpeg_exe, "-y", "-i", in_path,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "-f", "wav", out_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
            if res.returncode == 0 and Path(out_path).exists():
                with open(out_path, "rb") as out_f:
                    converted_bytes = out_f.read()
                converted_info = inspect_wav_header(converted_bytes)
                if (
                    converted_info.get("format") != "wav"
                    or converted_info.get("sample_rate") != 16000
                    or converted_info.get("channels") != 1
                    or converted_info.get("sample_width") != 2
                ):
                    raise AudioValidationError("Audio conversion did not produce 16 kHz mono PCM WAV.")
                if (converted_info.get("duration_seconds") or 0) < 3.0:
                    raise AudioValidationError("Voice sample must contain at least 3 seconds of audio.")
                return converted_bytes, "audio/wav", "converted.wav"
            detail = res.stderr.decode("utf-8", errors="replace")[-300:]
            raise AudioValidationError(f"Could not decode this audio file. {detail}")
        except subprocess.TimeoutExpired as exc:
            raise AudioValidationError("Audio conversion timed out. Please choose a shorter clip.") from exc
        except AudioValidationError:
            raise
        except Exception as exc:
            raise AudioValidationError(f"Audio conversion failed: {exc}") from exc
        finally:
            if in_path:
                Path(in_path).unlink(missing_ok=True)
            if out_path:
                Path(out_path).unlink(missing_ok=True)

    raise AudioValidationError(
        "Audio conversion is unavailable. Install ffmpeg or imageio-ffmpeg, then try again; "
        "unconverted audio is not sent to the voice service."
    )
