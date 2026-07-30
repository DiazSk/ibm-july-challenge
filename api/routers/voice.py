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
        audio_bytes = audio.file.read()
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
