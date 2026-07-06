"""
VoiceSynthesizer — Kokoro TTS (the same engine Voicebox ships as its built-in).

Converts agent response text to a WAV blob.  Key behaviour:
  • Strips all emoji and non-ASCII decorative characters BEFORE synthesis so
    they are never spoken aloud.
  • Uses 'am_echo' by default — natural American male voice (JARVIS-appropriate).
  • Returns raw WAV bytes; the browser plays them via new Audio(objectURL).

GPU: auto-detected. On RTX 4060: ~100ms per response. CPU: ~300-500ms.
Model auto-downloads to ~/.cache/huggingface/hub/ (~325 MB) on first call.
"""

import io
import re

import numpy as np
import soundfile as sf
from kokoro import KPipeline


# Covers the main Unicode emoji blocks — extend if needed
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"   # Misc symbols, emoticons, transport, etc.
    "\U00002700-\U000027BF"   # Dingbats
    "\U0001FA00-\U0001FAFF"   # Chess, symbols
    "\U00002600-\U000026FF"   # Misc symbols
    "\U0001F1E0-\U0001F1FF"   # Flags
    "]+",
    flags=re.UNICODE,
)

_SAMPLE_RATE = 24_000  # Kokoro output rate


class VoiceSynthesizer:
    """
    Thin wrapper around Kokoro KPipeline.

    KPipeline is heavyweight (model load) so this class is used as a singleton
    via the @lru_cache pattern in api/dependencies.py.
    """

    def __init__(self, voice: str = "am_echo"):
        self._pipeline = KPipeline(lang_code="a")   # 'a' = American English
        self._voice    = voice

    def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """
        Strip emojis, synthesize to WAV, return bytes.

        voice: overrides the instance default if supplied.
        """
        v     = voice or self._voice
        clean = self._clean(text)

        chunks: list[np.ndarray] = []
        for _, _, audio in self._pipeline(
            clean,
            voice         = v,
            speed         = 1.0,
            split_pattern = r"\n+",
        ):
            if audio is not None and len(audio) > 0:
                chunks.append(audio)

        samples = np.concatenate(chunks) if chunks else np.zeros(
            _SAMPLE_RATE // 4, dtype=np.float32   # 0.25 s silence fallback
        )

        buf = io.BytesIO()
        sf.write(buf, samples, _SAMPLE_RATE, format="WAV")
        return buf.getvalue()

    @staticmethod
    def _clean(text: str) -> str:
        text = _EMOJI_RE.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text or "Got it."
