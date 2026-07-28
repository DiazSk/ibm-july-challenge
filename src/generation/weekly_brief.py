"""
Weekly Brief Planner — Granite invocation #17.

Composes a *weekly slate* of varied content ideas from three sources:
  - trend  : a live niche angle (from the TrendAgent, #22)
  - winner : double down on a pattern that actually worked (tagged winners)
  - pillar : the underutilized-but-rich content pillar

Each idea is a light card — scenario + why-now + pillar + format + source —
NOT a finished draft. The router lands these in the Workbench; the creator
clicks "Develop this" to run the existing Blank Page Solver -> Caption ->
Image chain on demand. Failed posts are passed as an explicit avoid-list.

Input:  cluster_label, cluster_context, pillar_labels, winners, losers,
        trend_angles, brand_name, n
Output: list[{scenario_text, rationale, cluster_id, pillar, format, source}]

Run standalone (offline self-check):
    python src/generation/weekly_brief.py
"""

import json
import re

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

OLLAMA_MODEL = "granite3.1-dense:8b"

_FORMATS = {"Reel", "Carousel", "Static"}

_TEMPLATE = """\
You are the weekly content planner for {brand_name}, a homemade artisanal bakery on Instagram.

Plan {n} DISTINCT content ideas for the coming week. The ideas must be varied — \
span at least 3 different content pillars and mix formats (Reel / Carousel / Static). \
Do NOT propose near-duplicate ideas.

Content pillars (use the exact id + name):
{pillar_labels_block}

This pillar is underutilized relative to how richly-developed its voice is — \
give it at least one idea (source "pillar"):
Pillar: {cluster_label}
{cluster_context}

Ideas modelled on posts that ACTUALLY WORKED for this brand — reuse these winning \
patterns for source "winner" ideas:
{winners_block}

Posts that UNDERPERFORMED — AVOID these hooks/angles/patterns entirely:
{losers_block}

Current niche trend angles — base source "trend" ideas on these:
{trend_angles_block}

For each idea, set "source" to exactly one of: trend, winner, pillar — matching \
which input above it came from. Cover all three source types when the inputs allow. \
Each "scenario_text" is a natural, first-person 2-3 sentence description of a real \
moment ("what's happening in the kitchen"), not a caption or marketing pitch.

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "ideas": [
    {{"scenario_text": "<2-3 sentence realistic moment>",
      "rationale": "<1 sentence: why this, why now>",
      "cluster_id": <integer pillar id from the list above>,
      "format": "Reel" or "Carousel" or "Static",
      "source": "trend" or "winner" or "pillar"}}
  ]
}}
"""

_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "n", "pillar_labels_block", "cluster_label", "cluster_context",
        "winners_block", "losers_block", "trend_angles_block",
    ],
    template=_TEMPLATE,
)


def _insert_missing_commas(text: str) -> str:
    """Insert commas Granite 3.1 drops: between a value and the next key, and
    between adjacent objects in an array."""
    text = re.sub(r'([}\]"0-9])(\s*\n\s*)("[\w ]+"\s*:)', r"\1,\2\3", text)  # value → key
    text = re.sub(r'(\})(\s*\n?\s*)(\{)', r"\1,\2\3", text)                    # } { in an array
    return text


def _repair_truncated_json(text: str) -> str:
    """Close strings/brackets left open by a truncated response."""
    stack: list[str] = []
    in_str = esc = False
    for ch in text:
        if in_str:
            if esc:            esc = False
            elif ch == "\\":   esc = True
            elif ch == '"':    in_str = False
        elif ch == '"':        in_str = True
        elif ch in "{[":       stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack: stack.pop()
    repaired = (text + ('"' if in_str else "")).rstrip()
    if repaired.endswith(","):
        repaired = repaired[:-1]
    elif repaired.endswith(":"):
        repaired += " null"
    return repaired + "".join(reversed(stack))


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback only after strict parse fails, so it can't corrupt valid JSON.
    # ponytail: same repair lives in profile_extractor.py; unify into one
    # json-repair util if a third copy shows up.
    return json.loads(_repair_truncated_json(_insert_missing_commas(text)))


def _norm(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def dedupe_diverse(cards: list[dict], n: int) -> list[dict]:
    """
    Drop near-duplicate scenarios (token-overlap Jaccard > 0.6 with a kept card).
    Keeps original order; returns up to n cards.
    # ponytail: cheap token-overlap dedup; swap for embeddings only if it misses.
    """
    kept: list[dict] = []
    kept_tokens: list[set[str]] = []
    for c in cards:
        toks = _norm(c.get("scenario_text", ""))
        if not toks:
            continue
        dup = any(
            len(toks & kt) / len(toks | kt) > 0.6
            for kt in kept_tokens if (toks | kt)
        )
        if dup:
            continue
        kept.append(c)
        kept_tokens.append(toks)
        if len(kept) >= n:
            break
    return kept


class WeeklyBriefPlanner:
    """
    Composes a varied weekly slate of light idea cards from trend/winner/pillar
    sources. Never raises — falls back to a single pillar idea if Granite's
    output can't be parsed.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm = OllamaLLM(model=model, temperature=0.5, num_predict=1400)
        self._chain = _PROMPT | self._llm

    def generate(
        self,
        cluster_label: str,
        cluster_context: str,
        pillar_labels: dict,           # {cluster_id: label}
        winners: list[dict],           # [{caption, hook_pattern}]
        losers: list[dict],
        trend_angles: list[dict],      # [{angle, cluster, format, why_now}]
        brand_name: str,
        underutilized_id: int = 0,
        n: int = 5,
    ) -> list[dict]:
        """Granite Call #17. Returns up to n varied idea cards."""
        id_by_label = {str(v).strip().lower(): int(k) for k, v in pillar_labels.items()}

        pillar_labels_block = "\n".join(
            f"  {cid} - {label}" for cid, label in sorted(pillar_labels.items(), key=lambda x: int(x[0]))
        ) or "  0 - Content"
        winners_block = "\n".join(
            f"- (hook: {w.get('hook_pattern', '?')}) {(w.get('caption') or '')[:120]}" for w in winners[:4]
        ) or "(no tagged winners yet — skip 'winner' ideas, lean on trend + pillar)"
        losers_block = "\n".join(
            f"- (hook: {l.get('hook_pattern', '?')}) {(l.get('caption') or '')[:120]}" for l in losers[:4]
        ) or "(no tagged failures yet)"
        trend_angles_block = "\n".join(
            f"- {a.get('angle', '')} [{a.get('cluster', '')}, {a.get('format', '')}] — {a.get('why_now', '')}"
            for a in trend_angles[:5]
        ) or "(no external trend data this week — skip 'trend' ideas, lean on winner + pillar)"

        try:
            raw = self._chain.invoke({
                "brand_name": brand_name,
                "n": n,
                "pillar_labels_block": pillar_labels_block,
                "cluster_label": cluster_label,
                "cluster_context": cluster_context,
                "winners_block": winners_block,
                "losers_block": losers_block,
                "trend_angles_block": trend_angles_block,
            })
            ideas = (_parse_json(raw) or {}).get("ideas") or []
            cleaned = []
            for it in ideas:
                text = (it.get("scenario_text") or "").strip()
                if not text:
                    continue
                # Resolve pillar: trust cluster_id if valid, else map by label.
                cid = it.get("cluster_id")
                try:
                    cid = int(cid)
                except (TypeError, ValueError):
                    cid = None
                if cid not in pillar_labels:
                    cid = id_by_label.get(str(it.get("pillar", "")).strip().lower(), underutilized_id)
                fmt = it.get("format") if it.get("format") in _FORMATS else "Reel"
                src = it.get("source") if it.get("source") in ("trend", "winner", "pillar") else "pillar"
                cleaned.append({
                    "scenario_text": text,
                    "rationale": (it.get("rationale") or "").strip(),
                    "cluster_id": cid,
                    "pillar": pillar_labels.get(cid, cluster_label),
                    "format": fmt,
                    "source": src,
                })
            cards = dedupe_diverse(cleaned, n)
            if cards:
                return cards
        except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
            pass

        return [{
            "scenario_text": f"A behind-the-scenes look at how we make {cluster_label} this week.",
            "rationale": "Fallback idea — could not parse a specific plan.",
            "cluster_id": underutilized_id,
            "pillar": cluster_label,
            "format": "Reel",
            "source": "pillar",
        }]


# ── Offline self-check ────────────────────────────────────────────────────────

def _demo() -> None:
    # Exercise the deterministic pieces (dedup + card normalization) without Ollama.
    cards = [
        {"scenario_text": "We fried fresh bomboloni this morning and the smell filled the shop."},
        {"scenario_text": "This morning we fried fresh bomboloni and the smell filled the shop."},  # near-dup
        {"scenario_text": "A time-lapse of decorating a three-tier rasmalai cake for a wedding."},
        {"scenario_text": "Behind the scenes: sourcing pistachios for this week's kunafa."},
    ]
    kept = dedupe_diverse(cards, n=5)
    assert len(kept) == 3, f"expected near-duplicate dropped, got {len(kept)}"

    # Granite JSON quirks the parser must survive (else the whole slate falls back):
    assert _parse_json('{"a": "x"\n "b": "y"}') == {"a": "x", "b": "y"}            # missing comma: value→key
    assert _parse_json('{"ideas": [{"a": 1}\n {"a": 2}]}')["ideas"][1]["a"] == 2   # missing comma: } {
    assert _parse_json('{"ideas": [{"a": "x", "b": ["one"')["ideas"][0]["b"] == ["one"]  # truncated mid-array
    assert _parse_json('{"a": 1, "b": [2, 3]}') == {"a": 1, "b": [2, 3]}            # well-formed unaffected
    print("weekly_brief self-check passed.")


if __name__ == "__main__":
    _demo()
