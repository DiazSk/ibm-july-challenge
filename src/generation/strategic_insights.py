"""
Strategic Insights — Granite invocation #8.

Computes a "richness score" per content cluster from brand_profile.json,
detects investment/resonance mismatches (high volume + low richness, or
low volume + high richness), then calls Granite to generate a plain-English
strategic recommendation with one actionable experiment.

Richness formula (pure Python, no LLM):
  vocabulary_depth = len(signature_phrases) * 3 + len(recurring_words) * 1
  tone_complexity  = len(tone_descriptors)
  structural_spec  = min(len(avoided_terms), 3)
  richness_score   = vocabulary_depth + tone_complexity + structural_spec

A cluster with normalized_richness >> volume_pct is underutilized.
A cluster with volume_pct >> normalized_richness is over-invested.

Run standalone:
    python src/generation/strategic_insights.py
"""

import json
import re
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"

_CLUSTER_ID_LABELS = {
    0: "Homemade Classics",
    1: "Fusion Specials",
    2: "Behind the Scenes",
    3: "Nutella Series",
    4: "Bomboloni",
}

_TENSION_THRESHOLD = 15.0  # percentage-point gap that flags a mismatch

_TEMPLATE = """\
You are a creative strategist advising {brand_name}, a homemade artisan bakery.

Below is an analysis of how they distribute their creative investment across \
5 content territories. "Volume %" is how often they post in each territory. \
"Richness %" reflects how developed and distinct that territory's voice is.

{richness_table}

Investment vs. richness mismatches detected:
{tension_lines}

Write a 3-4 sentence strategic recommendation in plain English. Be specific — \
name the clusters and use the percentages. Then suggest one concrete, low-effort \
experiment the brand owner can run in the next 2 weeks. Speak directly to them, \
warmly, as a peer creative — not as a consultant.

Return ONLY valid JSON — no preamble, no markdown fences:
{{
  "strategic_brief": "<3-4 sentences>",
  "experiment": "<1-2 sentences: one specific, low-effort experiment>",
  "underutilized_cluster": <cluster_id integer or null>,
  "overused_cluster": <cluster_id integer or null>
}}
"""

_PROMPT = PromptTemplate(
    input_variables=["brand_name", "richness_table", "tension_lines"],
    template=_TEMPLATE,
)


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


class StrategicInsights:
    """
    Turns K-Means cluster output into a plain-English creative strategy by
    detecting where a brand is over- and under-investing relative to voice richness.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm   = OllamaLLM(model=model, temperature=0.2, num_predict=500)
        self._chain = _PROMPT | self._llm

    def compute_richness_scores(
        self, brand_profile: dict, clusters_data: dict
    ) -> list[dict]:
        """
        Pure Python — no LLM.

        Returns list of dicts per cluster:
          {cluster_id, pillar, tones, post_count, volume_pct,
           richness_score, normalized_richness, avg_hook_len}
        """
        total_posts = sum(cp["post_count"] for cp in brand_profile["cluster_profiles"])
        scores = []

        for cp in brand_profile["cluster_profiles"]:
            p = cp.get("profile", {})
            if p.get("parse_error"):
                continue

            voc = p.get("vocabulary_patterns", {})
            vocabulary_depth = (
                len(voc.get("signature_phrases", [])) * 3
                + len(voc.get("recurring_words", [])) * 1
            )
            tone_complexity = len(p.get("tone_descriptors", []))
            structural_spec = min(len(p.get("avoided_terms", [])), 3)
            richness_score  = vocabulary_depth + tone_complexity + structural_spec

            volume_pct = cp["post_count"] / total_posts * 100

            cluster_posts = clusters_data["clusters"].get(str(cp["cluster_id"]), [])
            avg_hook_len  = (
                sum(len(post["marketing_hook"]) for post in cluster_posts) / len(cluster_posts)
                if cluster_posts else 0
            )

            pillar = _CLUSTER_ID_LABELS.get(cp["cluster_id"], f"Cluster {cp['cluster_id']}")
            tones      = p.get("tone_descriptors", [])

            scores.append({
                "cluster_id"         : cp["cluster_id"],
                "pillar"             : pillar,
                "tones"              : tones[:2],
                "post_count"         : cp["post_count"],
                "volume_pct"         : round(volume_pct, 1),
                "richness_score"     : richness_score,
                "avg_hook_len"       : round(avg_hook_len),
            })

        # Add rank metadata (1 = highest) for chart and tension detection
        by_vol      = sorted(scores, key=lambda s: s["volume_pct"],    reverse=True)
        by_richness = sorted(scores, key=lambda s: s["richness_score"], reverse=True)
        vol_rank     = {s["cluster_id"]: i + 1 for i, s in enumerate(by_vol)}
        richness_rank = {s["cluster_id"]: i + 1 for i, s in enumerate(by_richness)}
        n = len(scores)
        for s in scores:
            s["volume_rank"]   = vol_rank[s["cluster_id"]]
            s["richness_rank"] = richness_rank[s["cluster_id"]]
            # Inverted scores (higher = better) for chart display
            s["volume_score"]   = n - vol_rank[s["cluster_id"]]     + 1
            s["richness_score_display"] = n - richness_rank[s["cluster_id"]] + 1

        return scores

    def detect_tensions(self, scores: list[dict]) -> list[str]:
        """
        Rank-based tension detection using pre-computed ranks in the scores dict.
        A gap of ≥2 ranks is a meaningful mismatch.  Rank 1 = highest.
        """
        tensions = []
        for s in sorted(scores, key=lambda x: x["cluster_id"]):
            vr   = s["volume_rank"]
            rr   = s["richness_rank"]
            diff = vr - rr  # positive → ranks higher in richness than in volume

            if diff >= 2:
                tensions.append(
                    f"C{s['cluster_id']} ({s['pillar']}): richness rank #{rr} "
                    f"but volume rank #{vr} — a well-developed voice you're underusing "
                    f"({s['volume_pct']:.0f}% of posts)."
                )
            elif diff <= -2:
                tensions.append(
                    f"C{s['cluster_id']} ({s['pillar']}): volume rank #{vr} "
                    f"but richness rank #{rr} — you post here often "
                    f"({s['volume_pct']:.0f}%) but this voice is less developed than others."
                )

        return tensions if tensions else ["Voice investment and richness are well balanced."]

    def generate_strategy_brief(
        self, scores: list[dict], tensions: list[str], brand_profile: dict
    ) -> dict:
        """
        Granite Call #8 — strategic recommendation.
        Returns {strategic_brief, experiment, underutilized_cluster, overused_cluster}.
        """
        header = f"{'Cluster':<30} {'Posts':>6} {'Volume %':>9} {'Vol Rank':>9} {'Rich Rank':>10}"
        sep    = "─" * (len(header) + 2)
        rows   = [header, sep]
        for s in sorted(scores, key=lambda x: x["cluster_id"]):
            name = f"C{s['cluster_id']} {s['pillar']}"
            rows.append(
                f"{name:<30} {s['post_count']:>6} {s['volume_pct']:>9.1f}"
                f" {s['volume_rank']:>9} {s['richness_rank']:>10}"
            )

        raw = self._chain.invoke({
            "brand_name"   : brand_profile["brand_name"],
            "richness_table": "\n".join(rows),
            "tension_lines" : "\n".join(f"  • {t}" for t in tensions),
        })

        try:
            return _parse_json(raw)
        except (json.JSONDecodeError, ValueError):
            return {
                "strategic_brief"     : raw.strip(),
                "experiment"          : "Re-run the analysis for structured output.",
                "underutilized_cluster": None,
                "overused_cluster"    : None,
            }


# ── Standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    profile  = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))
    clusters = json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))

    engine   = StrategicInsights()
    scores   = engine.compute_richness_scores(profile, clusters)
    tensions = engine.detect_tensions(scores)

    print("Richness scores:")
    for s in scores:
        print(
            f"  C{s['cluster_id']} {s['pillar']:<20}: "
            f"volume={s['volume_pct']}%  richness={s['normalized_richness']}%"
        )

    print("\nTensions:")
    for t in tensions:
        print(f"  {t}")

    print("\nGenerating strategy brief…")
    brief = engine.generate_strategy_brief(scores, tensions, profile)
    print(f"\nStrategic brief:\n{brief['strategic_brief']}")
    print(f"\nExperiment:\n{brief['experiment']}")
    print(f"\nUnderutilized: C{brief.get('underutilized_cluster')}")
    print(f"Overused:       C{brief.get('overused_cluster')}")
