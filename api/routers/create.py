"""
Create tab endpoints — Blank Page Solver + Caption Generator + Image Direction.

All Granite calls are synchronous (Ollama), so endpoints use plain `def`
(not `async def`). FastAPI automatically runs sync endpoints in a thread
pool, keeping the event loop unblocked.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import (
    get_caption_generator,
    get_direction_generator,
    get_image_generator,
    get_moment_analyzer,
)

router = APIRouter()


# ── Request / Response models ─────────────────────────────────────────────────

class AnalyzeMomentRequest(BaseModel):
    moment_text: str


class DirectionsRequest(BaseModel):
    moment_analysis: dict[str, Any]
    moment_text: str


class CaptionsRequest(BaseModel):
    product: str
    occasion: str
    desired_feel: str = ""
    cluster_id: int = 0


class ImagePromptRequest(BaseModel):
    caption: str
    product: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/analyze-moment")
def analyze_moment(req: AnalyzeMomentRequest) -> dict:
    """
    Granite Call #6 — MomentAnalyzer.
    Extracts emotional_core, business_signal, best_cluster_id, cluster_reason.
    """
    if not req.moment_text.strip():
        raise HTTPException(status_code=422, detail="moment_text is required")
    return get_moment_analyzer().analyze(req.moment_text)


@router.post("/directions")
def generate_directions(req: DirectionsRequest) -> list:
    """
    Granite Call #7 — DirectionGenerator.
    Returns 3 distinct creative directions.
    """
    if not req.moment_text.strip():
        raise HTTPException(status_code=422, detail="moment_text is required")
    return get_direction_generator().generate(req.moment_analysis, req.moment_text)


@router.post("/captions")
def generate_captions(req: CaptionsRequest) -> list:
    """
    Granite Call #2 — CaptionGenerator.
    Returns 3 caption variants with per-attribute reasoning.
    """
    if not req.product.strip():
        raise HTTPException(status_code=422, detail="product is required")
    if not req.occasion.strip():
        raise HTTPException(status_code=422, detail="occasion is required")
    return get_caption_generator().generate(
        product      = req.product.strip(),
        occasion     = req.occasion.strip(),
        desired_feel = req.desired_feel.strip() or "on-brand and engaging",
        cluster_id   = req.cluster_id,
    )


@router.post("/image-prompt")
def generate_image_prompt(req: ImagePromptRequest) -> dict:
    """
    Granite Call #3 — ImagePromptGenerator.
    Returns {prompt, style_notes} for Midjourney / DALL-E 3.
    """
    if not req.caption.strip():
        raise HTTPException(status_code=422, detail="caption is required")
    return get_image_generator().generate(
        caption = req.caption.strip(),
        product = req.product.strip(),
    )
