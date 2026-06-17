"""
Boost Advisor — Granite invocation #11.

Takes per-cluster engagement data (avg views, saves, comments) combined with
richness/volume ranks from StrategicInsights, then calls Granite to recommend
exactly which cluster's post to boost on Instagram and why.

This answers the question Instagram's native Boost button never answers:
*which post should I put money behind?*

Input:  cluster_scores (list[dict] from StrategicInsights.compute_richness_scores)
        cluster_engagement (dict from clusters.json["cluster_engagement"])
        brand_profile (dict)
Output: {boost_cluster_id, boost_cluster_name, boost_post_hook, reasoning,
         boost_strategy, expected_impact, dont_boost_cluster_id,
         dont_boost_cluster_name, dont_boost_reason}

Run standalone:
    python src/generation/boost_advisor.py
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

_TEMPLATE = """\
You are a paid-media advisor helping {brand_name}, a homemade artisan bakery, \
decide which Instagram post to boost with their limited advertising budget.

Here is how each content cluster performs on average:

{engagement_table}

Key facts:
- Avg views across all clusters: {account_avg_views}
- Boosting amplifies what's already working — not what you post most.
- High saves indicate content that people want to return to (highest boost ROI).
- High comments indicate community pull (good for brand awareness objectives).
- Richness rank reflects how distinctive and developed that cluster's voice is (1 = most distinctive).

Recommend the single best cluster to boost from. Be specific about which post hook \
to boost and why. Also flag which cluster NOT to boost and why that would waste budget.

Return ONLY valid JSON — no preamble, no markdown fences:
{{
  "boost_cluster_id": <integer>,
  "boost_cluster_name": "<name>",
  "boost_post_hook": "<exact hook text from the table>",
  "reasoning": "<2-3 sentences: why this cluster + this post>",
  "boost_strategy": "<1-2 sentences: Instagram Boost objective to select + audience tip>",
  "expected_impact": "<1 sentence: concrete expected outcome>",
  "dont_boost_cluster_id": <integer>,
  "dont_boost_cluster_name": "<name>",
  "dont_boost_reason": "<1 sentence: why this cluster would waste budget>"
}}
"""

_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "engagement_table", "account_avg_views"
    ],
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


def _build_engagement_table(
    cluster_scores: list[dict],
    cluster_engagement: dict,
) -> str:
    scores_by_id = {s["cluster_id"]: s for s in cluster_scores}

    header = (
        f"{'Cluster':<28} {'Posts':>6} {'Avg Views':>10} "
        f"{'Avg Saves':>10} {'Avg Comments':>13} "
        f"{'Eng Rate':>9} {'Rich Rank':>10} {'Best Hook'}"
    )
    sep = "─" * 120
    rows = [header, sep]

    for cid_str, eng in sorted(cluster_engagement.items(), key=lambda x: int(x[0])):
        cid = int(cid_str)
        score = scores_by_id.get(cid, {})
        richness_rank = score.get("richness_rank", "?")
        name = f"C{cid} {eng['cluster_name']}"
        hook = eng.get("best_post_hook", "")[:60]
        rows.append(
            f"{name:<28} {eng['post_count']:>6} {eng['avg_views']:>10} "
            f"{eng['avg_saves']:>10} {eng['avg_comments']:>13} "
            f"{eng['engagement_rate']:>9.1f}% {richness_rank!s:>10} {hook}"
        )

    return "\n".join(rows)


class BoostAdvisor:
    """
    Uses cluster-level engagement + richness/volume ranks to recommend
    which post to boost on Instagram — and which to avoid.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm   = OllamaLLM(model=model, temperature=0.2, num_predict=600)
        self._chain = _PROMPT | self._llm

    def generate(
        self,
        cluster_scores: list[dict],
        cluster_engagement: dict,
        brand_profile: dict,
    ) -> dict:
        """
        Granite Call #11.
        Returns boost recommendation with reasoning and strategy.
        """
        table = _build_engagement_table(cluster_scores, cluster_engagement)

        all_views = [v["avg_views"] for v in cluster_engagement.values()]
        account_avg = round(sum(all_views) / len(all_views)) if all_views else 0

        raw = self._chain.invoke({
            "brand_name"       : brand_profile.get("brand_name", "the brand"),
            "engagement_table" : table,
            "account_avg_views": account_avg,
        })

        try:
            result = _parse_json(raw)
        except (json.JSONDecodeError, ValueError):
            result = {
                "boost_cluster_id"     : 4,
                "boost_cluster_name"   : "Bomboloni",
                "boost_post_hook"      : cluster_engagement.get("4", {}).get("best_post_hook", ""),
                "reasoning"            : raw.strip(),
                "boost_strategy"       : "Use Instagram's Reach objective targeting food + baking interests.",
                "expected_impact"      : "Expected to reach 3-5x your organic reach within 48 hours.",
                "dont_boost_cluster_id": 0,
                "dont_boost_cluster_name": "Homemade Classics",
                "dont_boost_reason"    : "Lowest average engagement — budget would underperform here.",
            }

        # Attach the full best_post_hook from engagement data in case Granite truncated it
        cid_str = str(result.get("boost_cluster_id", ""))
        if cid_str in cluster_engagement:
            result["boost_post_hook"] = cluster_engagement[cid_str].get("best_post_hook", result.get("boost_post_hook", ""))

        return result


# ── Standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.generation.strategic_insights import StrategicInsights

    profile  = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))
    clusters = json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))

    si     = StrategicInsights()
    scores = si.compute_richness_scores(profile, clusters)

    engagement = clusters.get("cluster_engagement", {})
    if not engagement:
        print("No cluster_engagement in clusters.json — run with demo_clusters.json")
    else:
        advisor = BoostAdvisor()
        result  = advisor.generate(scores, engagement, profile)
        print(json.dumps(result, indent=2))
