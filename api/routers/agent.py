"""
JARVIS Agent router — POST /api/agent/chat

Implements the two-call Granite flow:
  Call 1 (Granite #13): intent routing → {response, tool?}
  If tool != null: dispatch tool → inject result → Call 2 (Granite #13 again)
  Call 2: synthesize tool result into natural spoken response

All Granite calls are synchronous (Ollama), so plain `def` endpoints.
"""

import json
import re
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import (
    get_caption_generator,
    get_inspiration_synthesizer,
    get_jarvis_agent,
    get_why_engine,
)
from api.routers.discover import _DEMO_ENGAGEMENT
from src.generation.jarvis_agent import (
    append_message,
    clear_session,
    get_history,
    search_creators,
)

router = APIRouter()

# ── Caption intent pre-filter ─────────────────────────────────────────────────
# Granite 3.1 8B sometimes generates a caption directly instead of returning the
# JSON tool call.  This pre-filter detects unambiguous "write me a caption" intent
# and synthesises the tool call before Granite is consulted, ensuring
# action_result.type == "caption" is always set for those requests.

_CAPTION_INTENT_RE = re.compile(
    r"\b(write|create|generate|make|craft|give\s+me|draft|compose)\b.{0,60}\b(caption|post|copy)\b"
    r"|\bcaption\s+(for|about|on)\b",
    re.IGNORECASE,
)
_CLUSTER_HINT: list[tuple[re.Pattern, int]] = [
    (re.compile(r"\bbomboloni\b", re.IGNORECASE), 4),
    (re.compile(r"\bnutella\b", re.IGNORECASE), 3),
    (re.compile(r"\brasmalai\b|\bkunafa\b|\bbiscuit\s+pudding\b", re.IGNORECASE), 1),
    (re.compile(r"\bbehind[\s-]+(the[\s-]+)?scenes?\b|\bour\s+story\b", re.IGNORECASE), 2),
]
_STRIP_META_RE = re.compile(
    r"\b(write|create|generate|make|craft|give|me|a|an|draft|compose|caption|post|copy|for|please|the|my)\b",
    re.IGNORECASE,
)


def _detect_caption_intent(user_msg: str) -> dict | None:
    """
    Returns a synthetic generate_caption tool call when the user clearly wants a
    caption, bypassing Granite intent routing.  CaptionGenerator (with full cluster
    voice injection) still runs for the actual generation.
    Returns None for everything else so Granite handles it normally.
    """
    if not _CAPTION_INTENT_RE.search(user_msg):
        return None
    cluster_id = 0  # Homemade Classics default
    for pattern, cid in _CLUSTER_HINT:
        if pattern.search(user_msg):
            cluster_id = cid
            break
    topic = _STRIP_META_RE.sub(" ", user_msg)
    topic = " ".join(topic.split()).strip() or user_msg.strip()
    return {
        "response": None,
        "tool": {"name": "generate_caption", "params": {"topic": topic, "cluster_id": cluster_id}},
    }


_PROJECT_ROOT  = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH  = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"
_DB_PATH       = _PROJECT_ROOT / "data" / "workbench.db"


# ── Request / Response ────────────────────────────────────────────────────────

class AgentChatRequest(BaseModel):
    messages  : list[dict]  # [{role, content}] — only the latest turn is required
    session_id: str
    user_message: str = ""  # convenience: last user message (extracted if missing)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_brand_data() -> tuple[dict, dict]:
    """Return (brand_profile, cluster_engagement). Raises HTTPException on failure."""
    try:
        profile  = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
        clusters = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))
        engagement = clusters.get("cluster_engagement") or _DEMO_ENGAGEMENT
        return profile, engagement
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Brand profile not found: {exc}")


def _get_wb_conn() -> sqlite3.Connection:
    """Lightweight workbench DB connection for agent read/write."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
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
        )
    """)
    conn.commit()
    return conn


def _dispatch_tool(
    tool_name: str,
    params: dict,
    brand_profile: dict,
    cluster_engagement: dict,
) -> tuple[str, dict | None]:
    """
    Execute a JARVIS tool.
    Returns (tool_result_text, action_result_dict | None).
    tool_result_text is injected back into Granite for Call 2.
    action_result_dict is sent to the frontend for structured display.
    """
    try:
        if tool_name == "generate_caption":
            topic      = params.get("topic", "")
            cluster_id = int(params.get("cluster_id", 0))

            gen     = get_caption_generator()
            caps    = gen.generate(
                product      = topic,
                occasion     = "Instagram post",
                desired_feel = "on-brand and engaging",
                cluster_id   = cluster_id,
            )
            best = caps[0]["caption"] if caps else "Could not generate a caption."
            return (
                f"Generated caption:\n\n{best}",
                {"type": "caption", "data": {"caption": best, "cluster_id": cluster_id}},
            )

        elif tool_name == "analyze_post":
            caption     = params.get("caption", "")
            post_type   = params.get("post_type", "Reel")
            if post_type not in ("Reel", "Carousel", "Static"):
                post_type = "Reel"

            result = get_why_engine().analyze(
                caption  = caption,
                post_type= post_type,
                views=0, reach=0, likes=0, comments=0, shares=0, saves=0,
            )
            summary = (
                f"Verdict: {result.get('verdict_label', '—')}\n"
                f"Diagnosis: {result.get('diagnosis', '—')}\n"
                f"What failed: {result.get('what_failed', '—')}\n"
                f"Change next time: {result.get('change_next_time', '—')}"
            )
            return summary, {"type": "post_mortem", "data": result}

        elif tool_name == "search_inspiration":
            topic = params.get("topic", "trending content")
            niche = brand_profile.get("brand_bio", "artisan bakery")[:40]

            snippets = search_creators(topic, niche)
            ideas    = get_inspiration_synthesizer().synthesize(snippets, topic, brand_profile)
            ideas_text = "\n".join(
                f"{i+1}. {idea.get('title','')}: {idea.get('what_to_post','')}"
                for i, idea in enumerate(ideas)
            )
            return (
                f"Found {len(ideas)} inspiration ideas:\n{ideas_text}",
                {"type": "inspiration", "data": {"ideas": ideas, "topic": topic}},
            )

        elif tool_name == "read_workbench":
            asset_type = params.get("asset_type") or None
            conn = _get_wb_conn()
            if asset_type:
                rows = conn.execute(
                    "SELECT * FROM workbench_assets WHERE asset_type = ? ORDER BY created_at DESC LIMIT 10",
                    (asset_type,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM workbench_assets ORDER BY created_at DESC LIMIT 10"
                ).fetchall()
            conn.close()

            if not rows:
                return "No saved assets found.", {"type": "workbench_items", "data": {"items": []}}

            items = []
            lines = []
            for row in rows:
                d     = dict(row)
                content_preview = str(d.get("content", ""))[:80]
                lines.append(f"- [{d['asset_type']}] {content_preview} ({d['created_at'][:10]})")
                items.append(d)
            return (
                f"Saved assets:\n" + "\n".join(lines),
                {"type": "workbench_items", "data": {"items": items}},
            )

        elif tool_name == "save_to_workbench":
            import uuid
            content    = params.get("content", "")
            asset_type = params.get("asset_type", "caption")
            asset_id   = str(uuid.uuid4())
            conn = _get_wb_conn()
            conn.execute(
                "INSERT INTO workbench_assets (id, asset_type, content, source_tab) VALUES (?, ?, ?, ?)",
                (asset_id, asset_type, content, "jarvis"),
            )
            conn.commit()
            conn.close()
            return (
                f"Saved to workbench as {asset_type}.",
                {"type": "saved", "data": {"id": asset_id}},
            )

        else:
            return f"Unknown tool: {tool_name}", None

    except Exception as exc:
        return f"Tool error: {exc}", None


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/chat")
def agent_chat(req: AgentChatRequest) -> dict:
    """
    Granite Calls #13 (× 1–2) — JarvisAgent.

    If the last message in req.messages is a user message, uses that as the
    user turn. Otherwise, req.user_message is used as the current turn.
    """
    # Extract the current user message
    user_msg = req.user_message.strip()
    if not user_msg and req.messages:
        last = req.messages[-1]
        if last.get("role") == "user":
            user_msg = last["content"].strip()
    if not user_msg:
        raise HTTPException(status_code=422, detail="No user message provided")

    brand_profile, cluster_engagement = _load_brand_data()
    agent = get_jarvis_agent()

    # Retrieve server-side session history + append current turn
    history = get_history(req.session_id)
    messages_for_call = history + [{"role": "user", "content": user_msg}]

    # ── Call 1: Intent routing ────────────────────────────────────────────
    call1 = _detect_caption_intent(user_msg) or agent.chat(messages_for_call)
    tool  = call1.get("tool")
    resp1 = call1.get("response")

    if not tool or not isinstance(tool, dict):
        # Direct answer — no tool needed
        final_response = resp1 or "I'm not sure how to answer that. Could you rephrase?"
        append_message(req.session_id, "user",      user_msg)
        append_message(req.session_id, "assistant", final_response)
        return {"response": final_response, "action_result": None, "session_id": req.session_id}

    # ── Tool dispatch ─────────────────────────────────────────────────────
    tool_name   = tool.get("name", "")
    tool_params = tool.get("params", {})

    tool_result_text, action_result = _dispatch_tool(
        tool_name, tool_params, brand_profile, cluster_engagement
    )

    # ── Call 2: Synthesize tool result ────────────────────────────────────
    messages_for_call2 = messages_for_call + [
        {"role": "assistant", "content": f"[Tool: {tool_name}]\n{tool_result_text}"},
        {"role": "user",      "content": (
            "Using only the tool result above, give a brief conversational response "
            "to my original request. 2–3 sentences, spoken aloud style."
        )},
    ]
    call2 = agent.chat(messages_for_call2)
    final_response = call2.get("response") or tool_result_text.split("\n")[0]

    # Update session history
    append_message(req.session_id, "user",      user_msg)
    append_message(req.session_id, "assistant", final_response)

    return {
        "response"     : final_response,
        "action_result": action_result,
        "session_id"   : req.session_id,
    }


@router.delete("/session/{session_id}", status_code=204)
def clear_agent_session(session_id: str) -> None:
    """Clear JARVIS conversation history for a session."""
    clear_session(session_id)


@router.get("/session/{session_id}")
def get_agent_session(session_id: str) -> dict:
    """Return current message history for a session (for panel state restore)."""
    return {"messages": get_history(session_id), "session_id": session_id}
