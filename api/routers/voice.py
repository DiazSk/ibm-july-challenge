"""
Voice endpoints — Whisper STT + Kokoro TTS.

POST /api/voice/transcribe   — audio blob → transcript text
POST /api/voice/synthesize   — response text → WAV bytes

Both are synchronous (plain def) because the underlying models are not async.
Models are loaded once via @lru_cache singletons in api/dependencies.py.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

from api.dependencies import get_voice_transcriber, get_voice_synthesizer

router = APIRouter()

# Whisper runs synchronously on a worker thread, so an unbounded upload holds a
# worker for as long as it takes to decode. A push-to-talk clip is a few hundred
# KB; 10 MB is already far more than any legitimate recording.
_MAX_AUDIO_BYTES = 10 * 1024 * 1024


@router.post("/transcribe")
def transcribe_audio(audio: UploadFile = File(...)) -> dict:
    """
    Transcribe a recorded audio file via faster-whisper (Whisper small).

    Accepts any format MediaRecorder produces:
      Chrome → audio/webm;codecs=opus
      Firefox → audio/ogg;codecs=opus
      Safari  → audio/mp4

    Returns: {"transcript": "..."}
    """
    try:
        # Read one byte past the cap so an oversized upload is rejected without
        # pulling the whole thing into memory first.
        audio_bytes = audio.file.read(_MAX_AUDIO_BYTES + 1)
        if len(audio_bytes) > _MAX_AUDIO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Audio too large (limit {_MAX_AUDIO_BYTES // (1024 * 1024)} MB).",
            )
        if len(audio_bytes) < 500:
            return {"transcript": ""}

        # Infer suffix from content-type; .webm is fine as a generic fallback
        ct = (audio.content_type or "").lower()
        if "mp4" in ct:
            suffix = ".mp4"
        elif "ogg" in ct:
            suffix = ".ogg"
        else:
            suffix = ".webm"

        transcript = get_voice_transcriber().transcribe(audio_bytes, suffix=suffix)
        return {"transcript": transcript}

    except HTTPException:
        raise  # 413 and friends are deliberate — don't relabel them as 500
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class SynthRequest(BaseModel):
    text : str
    voice: str = "bm_fable"


@router.post("/synthesize")
def synthesize_speech(req: SynthRequest) -> Response:
    """
    Convert text to speech via Kokoro TTS.

    Strips emojis server-side before synthesis.
    Returns raw audio/wav bytes — browser plays via Audio(objectURL).
    """
    try:
        wav_bytes = get_voice_synthesizer().synthesize(req.text, voice=req.voice)
        return Response(
            content      = wav_bytes,
            media_type   = "audio/wav",
            headers      = {"Cache-Control": "no-store"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
