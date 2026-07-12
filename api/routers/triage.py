"""
Comment/DM Triage — paste a batch of comments/DMs, get classification +
drafted replies back. No live Instagram inbox API access without platform
approval, so this is a synchronous batch tool (like Resonance Simulator),
not a background job — the message count is capped to keep total latency
in the same band as that already-shipped synchronous feature.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import get_comment_triager

router = APIRouter()

MAX_MESSAGES = 20


class TriageRequest(BaseModel):
    messages: list[str]
    cluster_id: int = 0


@router.post("/run")
def run_triage(req: TriageRequest) -> dict:
    """
    Granite Call #20 (x ceil(N/5) chunks) — CommentTriager.
    Classifies each message (order_inquiry/compliment/complaint/spam) and
    drafts a brand-voice reply for every non-spam message.
    """
    messages = [m.strip() for m in req.messages if m.strip()]
    if not messages:
        raise HTTPException(status_code=422, detail="messages is required")
    if len(messages) > MAX_MESSAGES:
        raise HTTPException(status_code=422, detail=f"{MAX_MESSAGES} messages max per batch")

    results = get_comment_triager().triage_batch(messages, req.cluster_id)
    return {"results": results, "total": len(results)}
