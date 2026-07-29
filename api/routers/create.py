"""
Create tab endpoints — Blank Page Solver + Caption Generator + Image Direction.

All Granite calls are synchronous (Ollama), so endpoints use plain `def`
(not `async def`). FastAPI automatically runs sync endpoints in a thread
pool, keeping the event loop unblocked.
"""

import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import (
    get_caption_generator,
    get_baseline_caption_generator,
    get_direction_generator,
    get_image_generator,
    get_moment_analyzer,
    get_script_generator,
    get_voice_refiner,
    get_persona_simulator,
    get_resonance_synthesizer,
    get_brand_guardian,
    get_sentence_embedder,
)

router = APIRouter()

_CLUSTERS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "clusters.json"
_PROFILE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "brand_profile.json"
_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "workbench.db"

_WB_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS workbench_assets (
    id           TEXT PRIMARY KEY,
    asset_type   TEXT NOT NULL,
    cluster_label TEXT,
    cluster_id   INTEGER,
    content      TEXT NOT NULL,
    pinned       INTEGER NOT NULL DEFAULT 0,
    source_tab   TEXT,
    actual_outcome       TEXT,
    recovery_brief_generated INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@lru_cache(maxsize=1)
def _get_wb_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_WB_CREATE_TABLE_SQL)
    conn.commit()
    return conn


def _extract_caption_text(content) -> str:
    """Pulls a representative caption string out of any asset content shape."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return str(content.get("caption") or content.get("hook") or "")
    return ""


def _build_performance_context(cluster_id: int) -> tuple[str | None, int]:
    """
    Queries workbench_assets for this cluster's real, user-reported outcomes
    (set via the Workbench drawer's outcome pills). Returns (performance_context
    string or None, count of rows used) — None/0 when no outcomes are tagged
    yet, so a fresh account gets byte-identical generation to before this
    feature existed.
    """
    conn = _get_wb_conn()
    rows = conn.execute(
        "SELECT content, actual_outcome FROM workbench_assets "
        "WHERE cluster_id = ? AND actual_outcome IS NOT NULL AND actual_outcome != '' "
        "ORDER BY created_at DESC LIMIT 5",
        (cluster_id,),
    ).fetchall()

    if not rows:
        return None, 0

    succeeded, underperforming = [], []
    for row in rows:
        try:
            content = json.loads(row["content"])
        except (json.JSONDecodeError, TypeError):
            content = row["content"]
        text = _extract_caption_text(content)
        if not text:
            continue
        if row["actual_outcome"] == "succeeded":
            succeeded.append(text)
        elif row["actual_outcome"] in ("underperformed", "failed"):
            underperforming.append(text)

    if not succeeded and not underperforming:
        return None, 0

    parts = []
    if succeeded:
        parts.append(
            f"{len(succeeded)} of your recent posts in this pillar succeeded. "
            f"Successful example: '{succeeded[0][:150]}'"
        )
    if underperforming:
        parts.append(
            f"{len(underperforming)} underperformed or failed. "
            f"Underperforming example: '{underperforming[0][:150]}'"
        )
    return " ".join(parts), len(rows)


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
    previous_captions: list[str] = []


class ScriptRequest(BaseModel):
    reference_caption: str
    views: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    # Story is generate-only — see the ScriptFormat note in frontend/lib/types.ts.
    format: Literal["Reel", "Carousel", "Static", "Story"] = "Reel"
    cluster_id: int = 0


class ImagePromptRequest(BaseModel):
    caption: str
    product: str


class VoiceRefineRequest(BaseModel):
    transcript: str
    cluster_id: int = 0


class ResonanceCheckRequest(BaseModel):
    captions: list[str]


class GuardianReviewRequest(BaseModel):
    caption: str
    cluster_id: int = 0


class DriftCompareRequest(BaseModel):
    product: str
    occasion: str
    desired_feel: str = ""
    cluster_id: int = 0


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/analyze-moment")
def analyze_moment(req: AnalyzeMomentRequest) -> dict:
    """
    Granite Call #6 — MomentAnalyzer.
    Extracts emotional_core, business_signal, best_cluster_id, cluster_reason,
    plus `similar_posts` — past posts covering the same ground, each with how it
    actually performed. Additive: existing consumers ignore the new key.
    """
    if not req.moment_text.strip():
        raise HTTPException(status_code=422, detail="moment_text is required")

    result = get_moment_analyzer().analyze(req.moment_text)

    # The repetition guard is an aid, not the point of the endpoint — a failure
    # here (missing data file, embedder load) must not cost the creator her
    # analysis. Degrade to an empty list.
    try:
        from src.data.repetition import find_similar_posts

        result["similar_posts"] = find_similar_posts(
            req.moment_text,
            json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8")),
            json.loads(_PROFILE_PATH.read_text(encoding="utf-8")),
            get_sentence_embedder(),
        )
    except Exception:
        result["similar_posts"] = []

    return result


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
def generate_captions(req: CaptionsRequest) -> dict:
    """
    Granite Call #2 — CaptionGenerator.
    Returns {captions, used_real_outcomes} — 3 caption variants with
    per-attribute reasoning, plus a count of real user-reported outcomes
    (from the Workbench's outcome pills) that were factored into this
    generation, closing the loop between reported performance and future
    generation without any new persistent-state/cache-invalidation design —
    it's queried fresh on every request.
    """
    if not req.product.strip():
        raise HTTPException(status_code=422, detail="product is required")
    if not req.occasion.strip():
        raise HTTPException(status_code=422, detail="occasion is required")

    performance_context, used_real_outcomes = _build_performance_context(req.cluster_id)

    captions = get_caption_generator().generate(
        product             = req.product.strip(),
        occasion            = req.occasion.strip(),
        desired_feel        = req.desired_feel.strip() or "on-brand and engaging",
        cluster_id          = req.cluster_id,
        previous_captions   = req.previous_captions or None,
        performance_context = performance_context,
    )
    return {"captions": captions, "used_real_outcomes": used_real_outcomes}


@router.post("/script")
def generate_script(req: ScriptRequest) -> dict:
    """
    Granite Call #9 — ScriptGenerator (structure) + CaptionGenerator (caption).
    Returns a structured content script (Reel/Carousel/Static) inspired by a
    high-performing reference post. The caption field is generated by the
    CaptionGenerator for quality parity with the Caption Brief.
    """
    if not req.reference_caption.strip():
        raise HTTPException(status_code=422, detail="reference_caption is required")

    script = get_script_generator().generate(
        reference_caption = req.reference_caption.strip(),
        metrics           = {
            "views"   : req.views,
            "reach"   : req.reach,
            "likes"   : req.likes,
            "comments": req.comments,
            "shares"  : req.shares,
            "saves"   : req.saves,
        },
        content_format = req.format,
        cluster_id     = req.cluster_id,
    )

    # Replace the script-generated caption with a high-quality one from
    # CaptionGenerator — same prompt and logic as the Caption Brief tab.
    # Use the script's hook as product context (it captures what the new
    # post is actually about) and the cluster's tone as the desired feel.
    #
    # Stories are exempt: they have no caption field on Instagram at all, and
    # script_generator._normalize_story deliberately strips one if Granite emits it.
    # Running this block for a Story would put it straight back.
    if req.format == "Story":
        return script

    try:
        cap_gen = get_caption_generator()
        clusters = cap_gen.cluster_profiles()
        cluster_profile = next(
            (c for c in clusters if c["cluster_id"] == req.cluster_id),
            clusters[0],
        )
        tone = cluster_profile["profile"].get("tone_descriptors", [])
        desired_feel = ", ".join(tone[:3]) if tone else "on-brand and engaging"

        hook = script.get("hook") or req.reference_caption[:100]
        captions = cap_gen.generate(
            product      = hook,
            occasion     = f"New {req.format} post",
            desired_feel = desired_feel,
            cluster_id   = req.cluster_id,
        )
        if captions:
            script["caption"] = captions[0]["caption"]
    except Exception:
        pass  # keep the script-generated caption as fallback

    return script


@router.post("/voice-refine")
def voice_refine(req: VoiceRefineRequest) -> dict:
    """
    Granite Call #12 — VoiceRefiner.
    Takes a raw spoken transcript and returns a polished on-brand caption
    calibrated to the given content cluster's brand voice.
    """
    if not req.transcript.strip():
        raise HTTPException(status_code=422, detail="transcript is required")

    try:
        brand_profile = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Brand profile not found: {exc}")

    return get_voice_refiner().refine(
        transcript   = req.transcript.strip(),
        cluster_id   = req.cluster_id,
        brand_profile= brand_profile,
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


def _build_persona_groundings(clusters: dict) -> dict[str, str]:
    """
    Grounds each simulator persona in one of the creator's own real content
    clusters, picked by engagement_rate/avg_views — not a generic archetype.
    """
    from api.routers.discover import _DEMO_ENGAGEMENT

    engagement = clusters.get("cluster_engagement") or _DEMO_ENGAGEMENT
    entries = list(engagement.values())
    if not entries:
        generic = "This persona represents a typical Instagram follower for this brand."
        return {"devotee": generic, "skeptic": generic, "casual_scroller": generic}

    devotee_cluster = max(entries, key=lambda e: e.get("engagement_rate", 0))
    skeptic_cluster = min(entries, key=lambda e: e.get("engagement_rate", 0))
    scroller_cluster = max(entries, key=lambda e: e.get("avg_views", 0))

    def describe(e: dict, flavor: str) -> str:
        return (
            f"This persona behaves like the '{e.get('cluster_name', 'Unknown')}' audience — "
            f"{flavor} (engagement rate {e.get('engagement_rate', 0)}%, "
            f"avg {e.get('avg_saves', 0)} saves and {e.get('avg_comments', 0)} comments per post)."
        )

    return {
        "devotee": describe(devotee_cluster, "your most engaged, highest-converting content pillar"),
        "skeptic": describe(skeptic_cluster, "your least-engaged content pillar — what tends NOT to resonate"),
        "casual_scroller": describe(
            scroller_cluster,
            "high-reach content that gets seen widely but doesn't always convert to saves or comments",
        ),
    }


@router.post("/resonance-check")
def run_resonance_check(req: ResonanceCheckRequest) -> dict:
    """
    Granite Call #16 (×4) — PersonaSimulator ×3 + ResonanceSynthesizer ×1.
    Simulates 3 audience personas, each grounded in a real content cluster from
    this creator's own data, reacting to the draft captions — then synthesizes
    a winner + one concrete, actionable fix.
    """
    if len(req.captions) < 2:
        raise HTTPException(status_code=422, detail="captions must contain at least 2 items")

    try:
        clusters = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Clusters data not found: {exc}")

    groundings = _build_persona_groundings(clusters)
    simulator = get_persona_simulator()

    persona_reactions = [
        simulator.react(req.captions, "The Devotee", groundings["devotee"]),
        simulator.react(req.captions, "The Casual Scroller", groundings["casual_scroller"]),
        simulator.react(req.captions, "The Skeptic", groundings["skeptic"]),
    ]

    synthesis = get_resonance_synthesizer().synthesize(persona_reactions, req.captions)

    return {"persona_reactions": persona_reactions, "synthesis": synthesis}


_SEVERITY_RANK = {"none": 0, "minor": 1, "major": 2}


def _critique_score(critique: dict) -> int:
    return _SEVERITY_RANK.get(critique.get("severity", "minor"), 1) + len(critique.get("issues") or [])


@router.post("/guardian-review")
def run_guardian_review(req: GuardianReviewRequest) -> dict:
    """
    Granite Call #18 (up to x4) — BrandGuardian.
    Adversarial critique -> refine loop on ONE already-generated caption,
    hard-capped at 2 rounds. Returns immediately if approved early; otherwise
    returns the best-so-far version (by severity + issue count), never
    silently pretending a non-converged result fully passed review.
    """
    caption = req.caption.strip()
    if not caption:
        raise HTTPException(status_code=422, detail="caption is required")

    guardian = get_brand_guardian()
    history: list[dict] = []

    c0 = guardian.critique(caption, req.cluster_id)
    history.append({"round": 0, "caption": caption, "critique": c0})
    if c0["verdict"] == "approve":
        return {
            "final_caption": caption,
            "converged": True,
            "rounds_used": 0,
            "best_so_far": False,
            "history": history,
        }

    r1 = guardian.refine(caption, c0, req.cluster_id)
    v1 = r1["refined_caption"]
    c1 = guardian.critique(v1, req.cluster_id)
    history.append({"round": 1, "caption": v1, "critique": c1})
    if c1["verdict"] == "approve":
        return {
            "final_caption": v1,
            "converged": True,
            "rounds_used": 1,
            "best_so_far": False,
            "history": history,
        }

    # Hard cap — no round 3, regardless of round 2's outcome.
    r2 = guardian.refine(v1, c1, req.cluster_id)
    v2 = r2["refined_caption"]
    c2 = guardian.critique(v2, req.cluster_id)
    history.append({"round": 2, "caption": v2, "critique": c2})

    best_caption = v1 if _critique_score(c1) < _critique_score(c2) else v2
    return {
        "final_caption": best_caption,
        "converged": False,
        "rounds_used": 2,
        "best_so_far": True,
        "history": history,
    }


# ── The Drift Test: head-to-head brand-voice match ─────────────────────────────

# brand_drift's coarse cosine bands → honest topical labels (never a raw %). This
# is the SECONDARY axis: it shows both captions are on the right *topic*.
_TOPICAL_LABELS = {
    "similar": "on topic",
    "diverging": "loosely related",
    "very_different": "off topic",
}


def _cluster_vocab(cluster_id: int) -> tuple[dict, list[str]]:
    """(vocabulary_patterns, avoided_terms) for a cluster, from brand_profile.json."""
    gen = get_caption_generator()
    profiles = gen.cluster_profiles()
    cluster = next((c for c in profiles if c["cluster_id"] == cluster_id), profiles[0])
    p = cluster["profile"]
    return p.get("vocabulary_patterns", {}), p.get("avoided_terms", [])


def _score_side(caption: str, vocab: dict, avoided: list[str], clusters_data: dict, embedder) -> dict:
    """
    PRIMARY: brand-voice fidelity (deterministic, uses the creator's own vocab —
    this is what reliably separates a plain LLM from StyleSync). SECONDARY:
    embedding topical band (shows the baseline is on-topic but off-voice).
    """
    from src.generation.brand_drift import detect_nearest_cluster_and_signal
    from src.generation.voice_fidelity import score_voice_fidelity

    fidelity = score_voice_fidelity(caption, vocab, avoided)
    _, topical = detect_nearest_cluster_and_signal([caption], clusters_data, embedder)
    return {
        "caption": caption,
        **fidelity,  # score, match_label, matched_words, matched_phrases, avoided_violations
        "topical_label": _TOPICAL_LABELS.get(topical["direction"], "loosely related"),
    }


@router.post("/drift-compare")
def drift_compare(req: DriftCompareRequest) -> dict:
    """
    The Drift Test — the hero shot. Runs the SAME brief through a plain-LLM
    baseline (no brand grounding) and StyleSync (Granite Call #2, full brand +
    memory grounding), then scores BOTH against the creator's real brand profile.

    Hero metric is brand-voice fidelity (0-100): does the caption use the
    creator's own signature phrases and recurring words and avoid their banned
    terms? A plain LLM has never seen the profile, so it scores near zero while
    StyleSync scores high — a reliable, deterministic, no-extra-LLM contrast. The
    matched phrases/words returned are the explanation. Both captions are usually
    on-topic (secondary embedding band), which is the point: on-topic ≠ on-voice.
    """
    if not req.product.strip():
        raise HTTPException(status_code=422, detail="product is required")
    if not req.occasion.strip():
        raise HTTPException(status_code=422, detail="occasion is required")

    try:
        clusters_data = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Clusters data not found: {exc}")

    embedder = get_sentence_embedder()
    vocab, avoided = _cluster_vocab(req.cluster_id)

    baseline_text = get_baseline_caption_generator().generate(
        product=req.product.strip(),
        occasion=req.occasion.strip(),
    )

    ss_variants = get_caption_generator().generate(
        product      = req.product.strip(),
        occasion     = req.occasion.strip(),
        desired_feel = req.desired_feel.strip() or "on-brand and engaging",
        cluster_id   = req.cluster_id,
    )
    stylesync_text = ss_variants[0]["caption"] if ss_variants else ""

    return {
        "baseline": _score_side(baseline_text, vocab, avoided, clusters_data, embedder),
        "stylesync": _score_side(stylesync_text, vocab, avoided, clusters_data, embedder),
    }
