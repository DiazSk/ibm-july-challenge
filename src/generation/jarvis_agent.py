"""
JARVIS Agent — Granite invocations #13 and #14.

#13 (JarvisAgent.chat): Multi-turn conversational brain. Receives full conversation
    history + brand context in the system prompt, routes to tools when needed, and
    answers directly from context when it can.

#14 (InspirationSynthesizer.synthesize): Receives DuckDuckGo (via ddgs) web search
    snippets and synthesizes 3 brand-adapted content ideas.

Session store: module-level in-memory dict, demo scale (resets on server restart).

Run standalone:
    python src/generation/jarvis_agent.py
"""

import json
import re
from collections import deque
from pathlib import Path
from threading import Lock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama, OllamaLLM

from src.data.pillars import pillar_names as pillar_labels_from

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"

OLLAMA_MODEL = "granite3.1-dense:8b"

# ── Session store ─────────────────────────────────────────────────────────────

_SESSIONS: dict[str, deque] = {}
_SESSIONS_LOCK = Lock()
_MAX_HISTORY = 20  # 10 turns (user + assistant pairs)

_CLUSTER_NAMES = {
    0: "Homemade Classics",
    1: "Fusion Specials",
    2: "Behind the Scenes",
    3: "Nutella Series",
    4: "Bomboloni",
}



def get_history(session_id: str) -> list[dict]:
    with _SESSIONS_LOCK:
        return list(_SESSIONS.get(session_id, deque()))


def append_message(session_id: str, role: str, content: str) -> None:
    with _SESSIONS_LOCK:
        if session_id not in _SESSIONS:
            _SESSIONS[session_id] = deque(maxlen=_MAX_HISTORY)
        _SESSIONS[session_id].append({"role": role, "content": content})


def clear_session(session_id: str) -> None:
    with _SESSIONS_LOCK:
        _SESSIONS.pop(session_id, None)


# ── DuckDuckGo search ─────────────────────────────────────────────────────────

class WebSearchUnavailable(RuntimeError):
    """Raised when web research can't run, so callers can say so instead of guessing."""


_CREATOR_PLATFORMS = ("instagram.com", "tiktok.com", "pinterest.com", "youtube.com", "reddit.com")


def search_creators(topic: str, niche: str = "bakery", max_results: int = 8) -> list[str]:
    """
    Search for creator content/trends across Instagram/TikTok/etc. via DuckDuckGo.
    Returns snippets formatted as 'Title: body' strings.

    Raises WebSearchUnavailable when the optional `ddgs` package isn't installed.
    It previously returned [] in that case, which Granite happily dressed up into
    confident-sounding "research" with no sources behind it — the same failure
    that made the trend agent fabricate its briefings. Everything else in
    StyleSync runs locally; this is the one optional network-dependent path, so
    its absence has to be visible.
    """
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise WebSearchUnavailable(
            "Web research needs the optional `ddgs` package (pip install ddgs)."
        ) from exc

    try:
        # Plain queries return generic SEO/e-commerce spam far more often than
        # real creator content, so target the platforms creators actually post
        # on directly instead of trusting DDG's general ranking.
        queries = [
            f"site:instagram.com {niche} {topic}",
            f"site:tiktok.com {niche} {topic}",
            f"trending {niche} content {topic} instagram reel",
        ]
        results = []
        seen: set[str] = set()

        with DDGS() as ddgs:
            for query in queries:
                try:
                    hits = ddgs.text(query, max_results=max_results // 2, timelimit="y")
                    for h in (hits or []):
                        url = h.get("href", "")
                        if not url or url in seen:
                            continue
                        # Off-platform hits are almost always unrelated SEO/
                        # e-commerce spam, not real creator content — skip them.
                        if not any(p in url for p in _CREATOR_PLATFORMS):
                            continue
                        seen.add(url)
                        title = h.get("title", "")
                        body  = h.get("body", "")[:300]
                        results.append(f"{title}: {body}")
                except Exception:
                    pass

        return results[:max_results]
    except Exception:
        return []


# ── JSON parsing ──────────────────────────────────────────────────────────────

def _parse_agent_json(raw: str) -> dict:
    """
    Parse Granite's JSON output robustly.
    Returns {response: str|None, tool: None|{name, params}}.
    Falls back to treating raw text as the response if JSON is malformed.
    """
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    try:
        obj = json.loads(text)
        return {
            "response": obj.get("response"),
            "tool"    : obj.get("tool"),
        }
    except (json.JSONDecodeError, ValueError):
        # Treat raw text as plain response
        return {"response": raw.strip(), "tool": None}


# ── System prompt builder ─────────────────────────────────────────────────────

_SYSTEM_TEMPLATE = """\
You are JARVIS, the AI creative assistant for {brand_name} ({ig_handle}) on StyleSync.
You know this creator's Instagram account deeply and speak warmly and concisely.

BRAND CONTEXT
{cluster_block}
Brand tone: {tone}
Signature phrases: {phrases}

TOOLS — invoke by returning a JSON "tool" key.
For brand/strategy/performance questions: answer directly from context above (no tool).

  generate_caption   {{"topic": str, "cluster_id": int}}  — write an on-brand caption
  analyze_post       {{"caption": str, "post_type": str, "metrics_description": str}}  — diagnose post
  search_inspiration {{"topic": str}}  — research top creators, generate brand-adapted ideas
  read_workbench     {{"asset_type": str}}  — list saved creative assets
  save_to_workbench  {{"content": str, "asset_type": str}}  — save content (asset_type: caption|reel_script|carousel|static_script)
  plan_week          {{"steer": str}}  — hand off to the autonomous Autopilot agent, which plans AND produces this week's whole content batch on its own. Use when the creator asks to plan their week/content or run autopilot. "steer" is an optional focus (e.g. "lean into Ramadan gifting"), else "".
  diagnose_and_fix   {{"caption": str}}  — hand off to the autonomous Recovery agent: it diagnoses WHY a post underperformed and writes a recovery version. Use when the creator asks to fix/recover/save an underperforming post, or "why did X flop and fix it". Pass the caption if they quote one, else "" and it fixes their most recent flop.

Cluster IDs: {cluster_ids}

RULES
• Keep responses 2–3 sentences max. You are speaking aloud, not writing.
• Only cite numbers from the cluster context above — never invent metrics.
• When calling a tool, set "response" to null exactly.

Respond ONLY in valid JSON (no markdown, no preamble):
{{"response": "<spoken reply>", "tool": null}}
{{"response": null, "tool": {{"name": "<tool>", "params": {{...}}}}}}
"""


def _build_system_prompt(brand_profile: dict, cluster_engagement: dict) -> str:
    brand_name = brand_profile.get("brand_name", "the brand")
    ig_handle  = brand_profile.get("ig_handle", "")

    # Build cluster block
    lines   = []
    top_cid = max(cluster_engagement, key=lambda k: cluster_engagement[k].get("engagement_rate", 0))
    for cid, eng in sorted(cluster_engagement.items(), key=lambda x: int(x[0])):
        name    = eng.get("cluster_name", f"C{cid}")
        views   = eng.get("avg_views", 0)
        reach   = eng.get("avg_reach", 0)
        saves   = eng.get("avg_saves", 0)
        comments= eng.get("avg_comments", 0)
        eng_rt  = eng.get("engagement_rate", 0)
        n_posts = eng.get("post_count", "?")
        marker  = " ← top performer" if str(cid) == str(top_cid) else ""
        parts   = [f"{views} avg views"]
        if reach:    parts.append(f"{reach} avg reach")
        if saves:    parts.append(f"{saves} avg saves")
        if comments: parts.append(f"{comments} avg comments")
        parts.append(f"{eng_rt}% eng")
        lines.append(f"  C{cid} {name} ({n_posts} posts) — {', '.join(parts)}{marker}")
    cluster_block = "\n".join(lines)

    # Tone + phrases from first cluster_profile
    tone    = "warm, authentic, indulgent"
    phrases = "made with love, fresh from the oven"
    for cp in brand_profile.get("cluster_profiles", []):
        p = cp.get("profile", {})
        if p.get("tone_descriptors"):
            tone    = ", ".join(p["tone_descriptors"][:4])
            voc     = p.get("vocabulary_patterns", {})
            phrases = ", ".join(f'"{s}"' for s in voc.get("signature_phrases", [])[:3])
            break

    # The cluster-ID legend has to come from the profile, not a local dict. Tool
    # params are keyed by cluster_id, so a stale legend here doesn't just mislabel
    # a reply — it routes generate_caption to the wrong pillar's voice.
    labels = pillar_labels_from(brand_profile) or _CLUSTER_NAMES
    cluster_ids = ", ".join(f"{name}={cid}" for cid, name in sorted(labels.items()))

    return _SYSTEM_TEMPLATE.format(
        brand_name    = brand_name,
        ig_handle     = ig_handle,
        cluster_block = cluster_block,
        cluster_ids   = cluster_ids,
        tone          = tone,
        phrases       = phrases,
    )


# ── JarvisAgent ───────────────────────────────────────────────────────────────

class JarvisAgent:
    """
    Granite #13 — multi-turn conversational brain for StyleSync.

    Loads brand_profile.json once and caches the system prompt.
    Each .chat() call is a single Granite inference.
    The two-call flow (tool execution + synthesis) is handled by the API router.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm = ChatOllama(model=model, temperature=0.5, num_predict=500)
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        try:
            profile  = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
            clusters = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))
            from src.data.insights import resolve_cluster_engagement

            engagement = resolve_cluster_engagement(clusters, profile)
            return _build_system_prompt(profile, engagement)
        except Exception:
            return (
                "You are JARVIS, an AI creative assistant for StyleSync. "
                "Answer concisely. Respond only in JSON: "
                '{"response": "<reply>", "tool": null}'
            )

    def refresh_system_prompt(self) -> None:
        """Called after onboarding reset to pick up new brand profile."""
        self._system_prompt = self._load_system_prompt()

    def chat(self, messages: list[dict]) -> dict:
        """
        Granite Call #13.
        messages: list of {role: 'user'|'assistant', content: str}
        Returns: {response: str|None, tool: None|{name: str, params: dict}}
        """
        lc_messages = [SystemMessage(content=self._system_prompt)]
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            else:
                lc_messages.append(AIMessage(content=msg["content"]))

        raw = self._llm.invoke(lc_messages).content
        return _parse_agent_json(raw)


# ── InspirationSynthesizer ────────────────────────────────────────────────────

_INSPIRATION_TEMPLATE = """\
You are a creative strategist for {brand_name}, a homemade artisan bakery.

Brand profile:
  Content pillars: {cluster_names}
  Tone: {tone}
  Signature phrases: {phrases}

The creator wants inspiration around: "{topic}"

Here are snippets from trending creator content online:
{snippets_block}

Generate 3 distinct content ideas that:
1. Adapt the trending approach to {brand_name}'s specific voice and baked goods
2. Are executable for a solo home-baker (no professional studio or team)
3. Each idea uses a DIFFERENT angle (sensory, narrative, educational, or behind-the-scenes)

Return ONLY valid JSON — no preamble, no markdown fences:
[
  {{
    "title": "<5-8 words>",
    "angle": "<sensory|narrative|educational|behind-the-scenes>",
    "what_to_post": "<1-2 sentences describing the post>",
    "caption_hook": "<opening line in the brand voice>"
  }}
]
"""

_INSPIRATION_PROMPT = PromptTemplate(
    input_variables=["brand_name", "cluster_names", "tone", "phrases", "topic", "snippets_block"],
    template=_INSPIRATION_TEMPLATE,
)


class InspirationSynthesizer:
    """
    Granite #14 — synthesizes web search snippets into 3 brand-adapted content ideas.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm   = OllamaLLM(model=model, temperature=0.65, num_predict=700)
        self._chain = _INSPIRATION_PROMPT | self._llm

    def synthesize(self, snippets: list[str], topic: str, brand_profile: dict) -> list[dict]:
        """
        Granite Call #14.
        Returns list of {title, angle, what_to_post, caption_hook}.
        Falls back to a generic set if parse fails.
        """
        if not snippets:
            snippets_block = "(No web results available — generate ideas from brand context only.)"
        else:
            numbered = [f"[{i+1}] {s}" for i, s in enumerate(snippets[:8])]
            snippets_block = "\n".join(numbered)

        tone    = "warm, authentic, indulgent"
        phrases = "made with love"
        cluster_names = ", ".join(
            (pillar_labels_from(brand_profile) or _CLUSTER_NAMES).values()
        )
        for cp in brand_profile.get("cluster_profiles", []):
            p = cp.get("profile", {})
            if p.get("tone_descriptors"):
                tone    = ", ".join(p["tone_descriptors"][:3])
                voc     = p.get("vocabulary_patterns", {})
                phrases = ", ".join(f'"{s}"' for s in voc.get("signature_phrases", [])[:3])
                break

        raw = self._chain.invoke({
            "brand_name"    : brand_profile.get("brand_name", "the brand"),
            "cluster_names" : cluster_names,
            "tone"          : tone,
            "phrases"       : phrases,
            "topic"         : topic,
            "snippets_block": snippets_block,
        })

        try:
            text = raw.strip()
            fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if fence:
                text = fence.group(1).strip()
            start = text.find("[")
            end   = text.rfind("]")
            if start != -1 and end != -1:
                text = text[start : end + 1]
            ideas = json.loads(text)
            return ideas[:3]
        except (json.JSONDecodeError, ValueError):
            return [{"title": "Inspiration idea", "angle": "sensory",
                     "what_to_post": raw.strip()[:200], "caption_hook": ""}]


# ── Standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = JarvisAgent()

    print("=== Test 1: Brand question (no tool) ===")
    result = agent.chat([
        {"role": "user", "content": "What is my best performing content cluster?"}
    ])
    print(json.dumps(result, indent=2))

    print("\n=== Test 2: Caption generation request ===")
    result = agent.chat([
        {"role": "user", "content": "Write me a caption for fresh bomboloni"}
    ])
    print(json.dumps(result, indent=2))

    print("\n=== Test 3: Inspiration research request ===")
    result = agent.chat([
        {"role": "user", "content": "Research trending bakery content and give me ideas"}
    ])
    print(json.dumps(result, indent=2))
