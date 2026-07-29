"""
Inbox Triage — real Instagram comments read + reply.

Comments-first (no 24-hour window, unlike DMs). Needs the
instagram_business_manage_comments scope on the connected token — if it's
missing (the account was connected before the scope was added), the Graph API
returns a permission error and we surface a 403 so the UI can prompt re-auth.

Endpoints:
  GET  /api/inbox/comments  — recent comments across the account's latest media
  POST /api/inbox/reply     — post a public reply to one comment
"""

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.scrapers.instagram_api import (
    load_connection, refresh_if_stale, fetch_recent_comments, reply_to_comment,
)

router = APIRouter()

_RECONNECT_MSG = (
    "Instagram isn't returning comment access, even though your account already "
    "consented to instagram_business_manage_comments — reconnecting won't change that. "
    "In your Meta App Dashboard, open the app's Instagram product → Permissions and "
    "Features, and confirm instagram_business_manage_comments is added/enabled there "
    "(and has completed App Review/Business Verification if Advanced Access is required)."
)


def _token() -> tuple[str, str]:
    conn = load_connection()
    if not conn:
        raise HTTPException(status_code=409, detail="No Instagram account connected.")
    conn = refresh_if_stale(conn)
    return conn["access_token"], (conn.get("username") or "")


@router.get("/comments")
def comments() -> dict:
    token, username = _token()
    try:
        items = fetch_recent_comments(token, own_username=username)
    except PermissionError:
        # Comments exist but the API returned none — token lacks the scope.
        raise HTTPException(status_code=403, detail=_RECONNECT_MSG)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        # Missing-scope / permission errors can also come back as explicit 400/403.
        if status in (400, 403):
            raise HTTPException(status_code=403, detail=_RECONNECT_MSG)
        raise HTTPException(status_code=502, detail="Instagram API error fetching comments.")
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Could not reach Instagram. Try again.")
    return {"comments": items, "total": len(items)}


class ReplyRequest(BaseModel):
    comment_id: str
    message: str


@router.post("/reply")
def reply(req: ReplyRequest) -> dict:
    message = req.message.strip()
    if not req.comment_id or not message:
        raise HTTPException(status_code=422, detail="comment_id and message are required.")
    token, _ = _token()
    try:
        result = reply_to_comment(token, req.comment_id, message)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        if status in (400, 403):
            raise HTTPException(status_code=403, detail=_RECONNECT_MSG)
        raise HTTPException(status_code=502, detail="Instagram rejected the reply. Try again.")
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Could not reach Instagram. Try again.")
    return {"ok": True, "id": result.get("id", "")}
