"""
Voice Timeline — Granite invocation #5.

Temporal analysis of how a brand's creative voice cluster distribution has
shifted across 8 months of Instagram posts. Granite narrates the evolution
in plain English, pointing to the most notable creative shift.

Input:  data/clusters.json (timestamp_utc + cluster assignments)
        data/brand_profile.json (cluster labels for narration context)
Output: (pct_df, monthly_counts) — percentage DataFrame for charting
        {"narrative": "...", "key_shift": "..."} — Granite narration

Run standalone:
    python src/generation/voice_timeline.py
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"

_PILLAR_LABELS = {
    "product_showcase"   : "Product Showcase",
    "behind_scenes"      : "Behind the Scenes",
    "seasonal_special"   : "Seasonal Special",
    "customer_connection": "Customer Connection",
    "brand_story"        : "Brand Story",
}

_TEMPLATE = """\
You are a creative strategist analyzing how a small bakery's Instagram content \
has evolved over several months.

Content cluster labels:
{cluster_labels}

Monthly post distribution (raw counts per cluster, YYYY-MM format):
{monthly_data_json}

Write 3-4 sentences in plain English describing how this brand's creative voice \
has evolved. Be specific — name the months and clusters. Highlight the single \
most interesting creative shift. Speak directly to the brand owner, warmly, as a \
peer — not as a consultant.

Return ONLY valid JSON — no preamble, no markdown fences:
{{"narrative": "<3-4 sentences describing the evolution>", "key_shift": "<one sentence: the single most notable shift>"}}
"""

_PROMPT = PromptTemplate(
    input_variables=["cluster_labels", "monthly_data_json"],
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


class VoiceTimeline:
    """
    Computes monthly cluster distribution from clusters.json and generates a
    Granite narrative describing the creative evolution of the brand's voice.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm   = OllamaLLM(model=model, temperature=0.3, num_predict=400)
        self._chain = _PROMPT | self._llm

    def compute_monthly_distribution(
        self, clusters_data: dict
    ) -> tuple[pd.DataFrame, dict]:
        """
        Returns (pct_df, raw_counts).

        pct_df       — wide DataFrame, month as index, columns C0..C4 as percentages
        raw_counts   — dict[YYYY-MM → dict[cluster_id → count]] for the Granite prompt
        """
        monthly: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

        for cid_str, posts in clusters_data["clusters"].items():
            cid = int(cid_str)
            for post in posts:
                month = post["timestamp_utc"][:7]
                monthly[month][cid] += 1

        all_months  = sorted(monthly.keys())
        cluster_ids = sorted({cid for counts in monthly.values() for cid in counts})

        rows = []
        for month in all_months:
            counts = monthly[month]
            total  = sum(counts.values()) or 1
            row    = {"month": month}
            for cid in cluster_ids:
                row[f"C{cid}"] = round(counts.get(cid, 0) / total * 100, 1)
            rows.append(row)

        pct_df = pd.DataFrame(rows).set_index("month")
        raw_counts = {month: dict(counts) for month, counts in monthly.items()}
        return pct_df, raw_counts

    def narrate_evolution(
        self, monthly_counts: dict, brand_profile: dict
    ) -> dict:
        """
        Granite Call #5 — plain-English narration of the brand's creative evolution.
        Returns {"narrative": "...", "key_shift": "..."}.
        """
        label_lines = []
        for cp in brand_profile["cluster_profiles"]:
            p = cp.get("profile", {})
            if p.get("parse_error"):
                continue
            raw_pillar = p.get("content_pillar", "product_showcase")
            pillar     = _PILLAR_LABELS.get(raw_pillar, raw_pillar.replace("_", " ").title())
            tones      = p.get("tone_descriptors", [])
            tone_str   = ", ".join(tones[:2]) if tones else ""
            label_lines.append(
                f"  C{cp['cluster_id']}: {pillar} ({cp['post_count']} posts total) — {tone_str}"
            )

        serializable = {
            month: {f"C{k}": v for k, v in counts.items()}
            for month, counts in sorted(monthly_counts.items())
        }

        raw = self._chain.invoke({
            "cluster_labels"   : "\n".join(label_lines),
            "monthly_data_json": json.dumps(serializable, indent=2),
        })

        try:
            return _parse_json(raw)
        except (json.JSONDecodeError, ValueError):
            return {
                "narrative" : raw.strip(),
                "key_shift" : "Could not parse structured response.",
            }


# ── Standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    clusters = json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))
    profile  = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))

    engine = VoiceTimeline()
    pct_df, raw_counts = engine.compute_monthly_distribution(clusters)

    print("Monthly distribution (%):")
    print(pct_df.to_string())

    print("\nGenerating Granite narrative…")
    result = engine.narrate_evolution(raw_counts, profile)
    print(f"\nNarrative:\n{result['narrative']}")
    print(f"\nKey shift:\n{result['key_shift']}")
