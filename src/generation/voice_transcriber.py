"""
VoiceTranscriber — Whisper STT via faster-whisper.

Replaces browser SpeechRecognition. Receives a raw audio blob (audio/webm
from MediaRecorder), writes it to a temp file, runs faster-whisper, and
returns the plain-text transcript.

No VAD involved — user controls start/stop via push-to-talk, so mid-sentence
cuts are impossible.

GPU: auto-detects CUDA via torch.cuda.is_available().
     On RTX 4060: ~80ms for a 5-10s clip with 'small' model at float16.
CPU: falls back to int8 quantisation.
     On i7/M-series: ~300-600ms with 'small'.
"""

import os
import tempfile

try:
    import torch
    _CUDA = torch.cuda.is_available()
except ImportError:
    _CUDA = False

from faster_whisper import WhisperModel


class VoiceTranscriber:
    def __init__(self, model_size: str = "small"):
        device       = "cuda" if _CUDA else "cpu"
        compute_type = "float16" if _CUDA else "int8"
        self._model  = WhisperModel(
            model_size,
            device       = device,
            compute_type = compute_type,
        )

    def transcribe(self, audio_bytes: bytes, suffix: str = ".webm") -> str:
        """
        Transcribe raw audio bytes.  suffix must match the container format
        (.webm from Chrome MediaRecorder, .mp4 from Safari, .ogg from Firefox).
        """
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp = f.name
        try:
            segments, _ = self._model.transcribe(
                tmp,
                language  = "en",
                beam_size = 3,
            )
            return " ".join(s.text.strip() for s in segments).strip()
        finally:
            os.unlink(tmp)
