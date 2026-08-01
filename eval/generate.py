"""
Produce the three-way caption set the fidelity scoring runs on.

For each of the 40 held-out posts:

  real      — the caption the account actually published (ground truth)
  stylesync — CaptionGenerator, grounded on the TRAIN-ONLY holdout profile
  baseline  — BaselineCaptionGenerator, brand-blind, same model, same brief

Both generators receive an identical brief, so any difference between them is
attributable to brand grounding and nothing else.

The brief is derived from the real caption by a separate Granite call at
temperature 0, explicitly instructed to state the subject in plain words and
drop the brand's phrasing. This matters: if the brief carried the caption's own
distinctive vocabulary, both generators would get that vocabulary for free and
the comparison would be compressed toward zero.

120 Granite calls on a local 8B model. Results are cached per shortcode, so an
interrupted run resumes where it stopped.

Run (after eval/holdout.py):
    python eval/generate.py
"""

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from langchain_core.prompts import PromptTemplate  # noqa: E402
from langchain_ollama import OllamaLLM  # noqa: E402

from src.generation.baseline_caption import BaselineCaptionGenerator  # noqa: E402
from src.generation.caption_generator import CaptionGenerator  # noqa: E402

ARTIFACTS = _PROJECT_ROOT / "eval" / "artifacts"
SPLIT_PATH = ARTIFACTS / "split.json"
HOLDOUT_PROFILE_PATH = ARTIFACTS / "profile_holdout.json"
CAPTIONS_PATH = ARTIFACTS / "captions.json"

OLLAMA_MODEL = "granite3.1-dense:8b"

# Held constant across every item so it is not a hidden channel for brand
# information into the StyleSync-only `desired_feel` slot.
DESIRED_FEEL = "natural"

_BRIEF_TEMPLATE = """\
Below is an Instagram caption from a home bakery.

Caption:
{caption}

Describe what this post is ABOUT, in plain factual words. State the item and \
the occasion only. Strip out all marketing language, adjectives, emoji, and \
any distinctive phrasing from the caption — another writer must be able to \
write their own caption from your description without echoing this one.

Return ONLY valid JSON, no preamble, no markdown fences:

{{"product": "<the item, 2-6 plain words>", "occasion": "<the context, 2-8 plain words>"}}
"""

_BRIEF_PROMPT = PromptTemplate(input_variables=["caption"], template=_BRIEF_TEMPLATE)


def _parse_brief(raw: str, fallback: str) -> dict:
    text = raw.strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    try:
        obj = json.loads(text)
        product = str(obj.get("product", "")).strip()
        occasion = str(obj.get("occasion", "")).strip()
        if product:
            return {"product": product, "occasion": occasion or "a general post"}
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    # Never fabricate: fall back to a truncated literal so the item is skipped
    # loudly at scoring time rather than silently scored against a guess.
    return {"product": fallback[:60], "occasion": "a general post", "brief_failed": True}


def load_cache() -> dict:
    if CAPTIONS_PATH.exists():
        return json.loads(CAPTIONS_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    CAPTIONS_PATH.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> None:
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    test = split["test"]

    brief_llm = OllamaLLM(model=OLLAMA_MODEL, temperature=0.0, num_predict=200)
    brief_chain = _BRIEF_PROMPT | brief_llm

    stylesync = CaptionGenerator(profile_path=HOLDOUT_PROFILE_PATH)
    baseline = BaselineCaptionGenerator()

    cache = load_cache()
    print(f"── {len(test)} held-out posts · {len(cache)} already cached\n")

    for i, item in enumerate(test, 1):
        sc = item["shortcode"]
        if sc in cache:
            print(f"  [{i:>2}/{len(test)}] {sc}  cached")
            continue

        real = item["real_caption"]
        cid = item["assigned_cluster"]

        brief = _parse_brief(brief_chain.invoke({"caption": real}), real)

        variants = stylesync.generate(
            product=brief["product"],
            occasion=brief["occasion"],
            desired_feel=DESIRED_FEEL,
            cluster_id=cid,
        )
        ss_caption = (variants[0].get("caption", "") if variants else "").strip()

        bl_caption = baseline.generate(
            product=brief["product"], occasion=brief["occasion"]
        ).strip()

        cache[sc] = {
            "shortcode": sc,
            "assigned_cluster": cid,
            "brief": brief,
            "real": real,
            "stylesync": ss_caption,
            "baseline": bl_caption,
        }
        save_cache(cache)

        flag = "  BRIEF-FAILED" if brief.get("brief_failed") else ""
        print(f"  [{i:>2}/{len(test)}] {sc}  c{cid}  "
              f"brief={brief['product'][:34]!r}{flag}")

    empties = [
        sc for sc, v in cache.items()
        if not v["stylesync"].strip() or not v["baseline"].strip()
    ]
    failed = [sc for sc, v in cache.items() if v["brief"].get("brief_failed")]

    print(f"\n── Done. {len(cache)} items cached → "
          f"{CAPTIONS_PATH.relative_to(_PROJECT_ROOT)}")
    if failed:
        print(f"   {len(failed)} brief extraction(s) fell back: {failed}")
    if empties:
        print(f"   {len(empties)} item(s) have an empty generation: {empties}")


if __name__ == "__main__":
    main()
