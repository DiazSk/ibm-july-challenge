"""
Onboarding endpoints — self-serve Instagram account analysis.

Two paths:
  POST /start   — handle-based (Instaloader scrapes public profile)
  POST /upload  — ZIP upload (Instagram official data export)

Both paths run the 3-stage pipeline in a FastAPI BackgroundTask and
report progress via a polling endpoint.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, Form
from pydantic import BaseModel

router = APIRouter()

_PROJECT_ROOT   = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH   = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH  = _PROJECT_ROOT / "data" / "clusters.json"
_DEMO_PROFILE   = _PROJECT_ROOT / "data" / "demo_brand_profile.json"
_DEMO_CLUSTERS  = _PROJECT_ROOT / "data" / "demo_clusters.json"
_SCRAPED_DIR    = _PROJECT_ROOT / "scraped_dataset"

# In-memory job store (single-server, demo-scale)
_jobs: dict[str, dict] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _update_job(job_id: str, pct: int, message: str, status: str = "running") -> None:
    existing = _jobs.get(job_id, {})
    _jobs[job_id] = {**existing, "progress": pct, "message": message, "status": status}


def _clear_caches() -> None:
    """
    Invalidate all LRU-cached singletons so they reload the newly-written
    brand_profile.json on next request.
    """
    try:
        from api.dependencies import (
            get_caption_generator, get_image_generator, get_why_engine,
            get_moment_analyzer, get_direction_generator, get_voice_timeline,
            get_strategic_insights, get_script_generator,
            get_recovery_brief_generator,
        )
        for fn in (
            get_caption_generator, get_image_generator, get_why_engine,
            get_moment_analyzer, get_direction_generator, get_voice_timeline,
            get_strategic_insights, get_script_generator,
            get_recovery_brief_generator,
        ):
            try:
                fn.cache_clear()
            except Exception:
                pass
    except Exception:
        pass

    try:
        from api.routers.discover import _compute_voice_timeline, _compute_strategic_insights
        _compute_voice_timeline.cache_clear()
        _compute_strategic_insights.cache_clear()
    except Exception:
        pass


# ── Background tasks ──────────────────────────────────────────────────────────

def _run_handle_pipeline(job_id: str, handle: str, brand_name: str) -> None:
    """Scrape a public Instagram profile then run the full 3-stage pipeline."""
    try:
        _update_job(job_id, 5, "Connecting to Instagram...")

        from src.scrapers.instaloader_scraper import scrape_profile
        _update_job(job_id, 10, f"Fetching posts for @{handle.lstrip('@')}...")
        n = scrape_profile(handle)

        _update_job(job_id, 30, f"Fetched {n} posts. Processing captions...")
        from src.data.pipeline import run_pipeline
        records = run_pipeline()
        if not records:
            raise RuntimeError("No posts with usable captions found.")

        _update_job(job_id, 50, "Clustering your content...")
        from src.embeddings.cluster import run_clustering
        run_clustering()

        _update_job(job_id, 65, "IBM Granite is building your brand voice...")
        from src.embeddings.profile_extractor import BrandProfileExtractor
        ig_handle = handle if handle.startswith("@") else f"@{handle}"
        extractor = BrandProfileExtractor(
            brand_name=brand_name,
            ig_handle=ig_handle,
            brand_bio=f"{brand_name} — Instagram creator analyzed by StyleSync.",
        )
        extractor.build_brand_profile()

        _clear_caches()
        _update_job(job_id, 100, "Your brand profile is ready!", status="done")
        _jobs[job_id]["handle"] = ig_handle

    except Exception as exc:
        current_pct = _jobs.get(job_id, {}).get("progress", 0)
        _update_job(job_id, current_pct, str(exc), status="error")


def _run_export_pipeline(
    job_id    : str,
    zip_bytes : bytes,
    account   : str,
    brand_name: str,
) -> None:
    """Parse an Instagram data export ZIP then run the full 3-stage pipeline."""
    try:
        _update_job(job_id, 5, "Reading your Instagram data export...")

        # Write ZIP to a temp file, parse it with the existing ig_scraper logic
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(zip_bytes)
            tmp_path = tmp.name

        try:
            # Clear previous scraped data
            _SCRAPED_DIR.mkdir(exist_ok=True)
            for f in _SCRAPED_DIR.glob("ig_text_*.json"):
                f.unlink()

            sys.path.insert(0, str(_PROJECT_ROOT))
            from ig_scraper import parse_instagram_export
            parse_instagram_export(tmp_path, account=account.lstrip("@"))
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        _update_job(job_id, 30, "Posts extracted. Processing captions...")
        from src.data.pipeline import run_pipeline
        records = run_pipeline()
        if not records:
            raise RuntimeError(
                "No posts with usable captions found in the export. "
                "Make sure you exported 'Posts' and 'Reels' in JSON format."
            )

        _update_job(job_id, 50, "Clustering your content...")
        from src.embeddings.cluster import run_clustering
        run_clustering()

        _update_job(job_id, 65, "IBM Granite is building your brand voice...")
        from src.embeddings.profile_extractor import BrandProfileExtractor
        ig_handle = account if account.startswith("@") else f"@{account}"
        extractor = BrandProfileExtractor(
            brand_name=brand_name,
            ig_handle=ig_handle,
            brand_bio=f"{brand_name} — Instagram creator analyzed by StyleSync.",
        )
        extractor.build_brand_profile()

        _clear_caches()
        _update_job(job_id, 100, "Your brand profile is ready!", status="done")
        _jobs[job_id]["handle"] = ig_handle

    except Exception as exc:
        current_pct = _jobs.get(job_id, {}).get("progress", 0)
        _update_job(job_id, current_pct, str(exc), status="error")


# ── Request models ─────────────────────────────────────────────────────────────

class OnboardHandleRequest(BaseModel):
    handle    : str
    brand_name: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_onboard(req: OnboardHandleRequest, background_tasks: BackgroundTasks):
    """
    Start an onboarding pipeline for a public Instagram account.
    Returns a job_id to poll via GET /status/{job_id}.
    """
    handle = req.handle.strip().lstrip("@")
    if not handle:
        raise HTTPException(status_code=422, detail="handle is required")
    brand_name = req.brand_name.strip() or handle.replace("_", " ").title()

    job_id = str(uuid4())
    _jobs[job_id] = {
        "status"  : "queued",
        "progress": 0,
        "message" : "Starting...",
        "handle"  : f"@{handle}",
    }
    background_tasks.add_task(_run_handle_pipeline, job_id, handle, brand_name)
    return {"job_id": job_id}


@router.post("/upload")
async def upload_export(
    background_tasks: BackgroundTasks,
    file      : UploadFile,
    account   : str = Form(default="my_account"),
    brand_name: str = Form(default=""),
):
    """
    Start an onboarding pipeline from an Instagram data export ZIP.
    Returns a job_id to poll via GET /status/{job_id}.
    """
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(
            status_code=422,
            detail="Please upload a .zip file from Instagram's data export.",
        )
    account    = account.strip().lstrip("@") or "my_account"
    brand_name = brand_name.strip() or account.replace("_", " ").title()

    zip_bytes = await file.read()
    job_id    = str(uuid4())
    _jobs[job_id] = {
        "status"  : "queued",
        "progress": 0,
        "message" : "Starting...",
        "handle"  : f"@{account}",
    }
    background_tasks.add_task(_run_export_pipeline, job_id, zip_bytes, account, brand_name)
    return {"job_id": job_id}


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Poll the progress of an onboarding job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _jobs[job_id]


@router.get("/has-profile")
async def has_profile():
    """
    Check whether a brand profile already exists.
    Used by the root page to decide whether to show onboarding or the app.
    """
    exists = _PROFILE_PATH.exists() and _CLUSTERS_PATH.exists()
    handle = None
    if exists:
        try:
            p = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
            handle = p.get("ig_handle", "")
        except Exception:
            pass
    return {"has_profile": exists, "handle": handle}


@router.post("/reset-demo")
async def reset_to_demo():
    """
    Restore the pre-loaded @hot_cakesbakes demo profile and clear all caches.
    Useful for demos where judges want to see the default account.
    """
    if not _DEMO_PROFILE.exists() or not _DEMO_CLUSTERS.exists():
        raise HTTPException(
            status_code=404,
            detail="Demo data files not found. Run the pipeline once first.",
        )
    shutil.copy(_DEMO_PROFILE, _PROFILE_PATH)
    shutil.copy(_DEMO_CLUSTERS, _CLUSTERS_PATH)
    _clear_caches()
    return {"status": "reset", "handle": "@hot_cakesbakes"}
