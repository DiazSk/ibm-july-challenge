"""
Instagram account connection endpoints — OAuth connect + real-time sync.

The user authorizes their own Business/Creator account once; after that the
background poller (see api/main.py) keeps their brand profile fresh. This
router also exposes a manual "Sync now" trigger and connection status.
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import RedirectResponse

from src.scrapers.instagram_api import (
    build_authorize_url, exchange_code, load_connection, disconnect, sync_account,
)

router = APIRouter()

_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def run_sync_and_refresh(full: bool = False) -> int:
    """
    Sync the connected account then invalidate cached singletons so the app
    serves the freshly-rebuilt brand_profile.json. Single entry point shared
    by the /callback initial sync, the /sync endpoint, and the poller.
    """
    written = sync_account(full=full)
    from api.routers.onboard import _clear_caches
    _clear_caches()
    return written


@router.get("/login")
async def login():
    """Redirect the user to Instagram's OAuth consent screen."""
    try:
        return RedirectResponse(build_authorize_url())
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/callback")
async def callback(background_tasks: BackgroundTasks, code: str = "", error: str = ""):
    """OAuth redirect target. Exchanges the code, saves the token, kicks off the initial sync."""
    if error or not code:
        return RedirectResponse(f"{_FRONTEND_URL}/?ig_connected=0")
    try:
        conn = exchange_code(code)
    except Exception as exc:  # noqa: BLE001 — surface any exchange failure to the user
        raise HTTPException(status_code=400, detail=f"Instagram authorization failed: {exc}")
    background_tasks.add_task(run_sync_and_refresh, True)
    return RedirectResponse(f"{_FRONTEND_URL}/?ig_connected=1&handle={conn.get('username', '')}")


@router.get("/status")
async def status():
    """Connection status for the frontend."""
    conn = load_connection()
    if not conn:
        return {"connected": False}
    last = conn.get("last_sync_utc")
    exp  = conn.get("token_expires_at")
    return {
        "connected"        : True,
        "username"         : conn.get("username"),
        "last_sync"        : datetime.fromtimestamp(last, tz=timezone.utc).isoformat() if last else None,
        "token_expires_at" : datetime.fromtimestamp(exp, tz=timezone.utc).isoformat() if exp else None,
    }


@router.post("/sync")
async def sync_now(background_tasks: BackgroundTasks, full: bool = False):
    """
    Manually trigger a sync. `full=false` (default, same path the poller uses)
    fetches only new posts and rebuilds only if any arrived. `full=true`
    re-fetches everything and always rebuilds the profile — the "force a
    fresh rebuild" the dashboard button uses.
    """
    if not load_connection():
        raise HTTPException(status_code=409, detail="No Instagram account connected.")
    background_tasks.add_task(run_sync_and_refresh, full)
    return {"status": "syncing"}


@router.post("/disconnect")
async def disconnect_account():
    disconnect()
    return {"status": "disconnected"}
