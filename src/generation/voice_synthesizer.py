"""
VoiceSynthesizer — Kokoro TTS (the same engine Voicebox ships as its built-in).

Converts agent response text to a WAV blob.  Key behaviour:
  • Strips all emoji and non-ASCII decorative characters BEFORE synthesis so
    they are never spoken aloud.
  • Uses 'bm_fable' by default — British male voice (JARVIS-appropriate butler tone).
  • Returns raw WAV bytes; the browser plays them via new Audio(objectURL).

GPU: auto-detected. On RTX 4060: ~100ms per response. CPU: ~300-500ms.
Model auto-downloads to ~/.cache/huggingface/hub/ (~325 MB) on first call.
"""

import io
import platform
import re
import subprocess

import numpy as np
import soundfile as sf
from kokoro import KPipeline

# On macOS, the bundled espeakng-loader library ships with a hardcoded CI
# build path for its espeak-ng-data directory, so KPipeline's phoneme lookup
# fails with "No such file or directory" unless repointed at a real
# espeak-ng install (brew install espeak-ng). Must run AFTER importing
# kokoro, since misaki sets its (broken) defaults at import time.
if platform.system() == "Darwin":
    try:
        prefix = subprocess.run(
            ["brew", "--prefix", "espeak-ng"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
        if prefix:
            from phonemizer.backend.espeak.wrapper import EspeakWrapper
            EspeakWrapper.set_library(f"{prefix}/lib/libespeak-ng.dylib")
            EspeakWrapper.set_data_path(f"{prefix}/share/espeak-ng-data")
    except Exception:
        pass  # best-effort — falls back to the (possibly broken) bundled path


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

    def __init__(self, voice: str = "bm_fable"):
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
        # PCM_16 = 16-bit signed integer — universally supported by browsers.
        # soundfile handles float32→int16 conversion automatically.
        sf.write(buf, samples, _SAMPLE_RATE, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    @staticmethod
    def _clean(text: str) -> str:
        text = _EMOJI_RE.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text or "Got it."
