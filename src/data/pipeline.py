"""
Data ingestion and normalization pipeline for @hot_cakesbakes.

Input:  scraped_dataset/ig_text_*.json   (raw from ig_scraper.py)
Output: data/cleaned/ig_text_*.json      (cleaned, hook/logistics split)

Run:
    python src/data/pipeline.py
"""

import json
import re
from pathlib import Path

import ftfy
import pandas as pd

# ── Paths (resolved from project root regardless of cwd) ───────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR       = _PROJECT_ROOT / "scraped_dataset"
CLEANED_DIR   = _PROJECT_ROOT / "data" / "cleaned"

BRAND_NAME    = "HotCakes Bakes"
IG_HANDLE     = "@hot_cakesbakes"

# ── Logistics detection ─────────────────────────────────────────────────────
# Paragraphs matching any of these patterns are classified as logistics,
# not marketing copy — phone numbers, location tags, ordering CTAs, etc.
_LOGISTICS_PATTERNS = [
    r"📍|📩|📞|☎️|📱|🚚|🛵",
    r"\b\d{10}\b",                                   # 10-digit phone number
    r"(?i)\bwhatsapp\b",
    r"(?i)\b(dm\s+(?:us\s+)?for|order\s+(?:now|here|via)|pre.?order)\b",
    r"(?i)\b(free\s+(?:home\s+)?delivery|pickup\s+available|home\s+delivery)\b",
    r"(?i)\b(taloja|navi\s*mumbai|mumbai)\b",
    r"(?i)\border\s+\d+\s*day",                      # "order 1 day prior"
    r"(?i)\bfollow\s+@\w+",                          # "Follow @hot_cakesbakes"
    r"(?i)\bfor\s+more\s+(delicious\s+)?updates\b",
]
_LOGISTICS_RE = re.compile("|".join(_LOGISTICS_PATTERNS))

# A paragraph containing only hashtags
_HASHTAG_ONLY_RE = re.compile(r"^(\s*#\w+\s*)+$")


def _is_logistics(paragraph: str) -> bool:
    return bool(_LOGISTICS_RE.search(paragraph))


def _is_hashtag_block(paragraph: str) -> bool:
    return bool(_HASHTAG_ONLY_RE.match(paragraph.strip()))


def split_caption(text: str) -> tuple[str, str]:
    """
    Split a cleaned caption into (marketing_hook, logistics).

    Strategy: walk paragraphs in order. Once any paragraph triggers the
    logistics detector, it and everything after is classified as logistics.
    Pure hashtag blocks are stripped from the hook entirely.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    hook_parts      : list[str] = []
    logistics_parts : list[str] = []
    in_logistics = False

    for para in paragraphs:
        if _is_hashtag_block(para):
            # Hashtag blocks belong to neither section as meaningful copy
            continue
        if in_logistics or _is_logistics(para):
            in_logistics = True
            logistics_parts.append(para)
        else:
            hook_parts.append(para)

    return "\n\n".join(hook_parts).strip(), "\n\n".join(logistics_parts).strip()


def clean_text(text: str) -> str:
    """
    Fix mojibake (â€™ → ', â€¦ → …) and normalize Unicode using ftfy.
    Preserves emoji characters — ftfy only repairs broken encodings.
    """
    return ftfy.fix_text(text).strip()


def process_file(path: Path) -> dict | None:
    """
    Load, clean, and split a single scraped JSON file.
    Returns None for posts with no usable marketing copy.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))

    caption_raw = raw.get("content", {}).get("caption_raw", "").strip()
    if not caption_raw:
        return None

    caption_clean          = clean_text(caption_raw)
    marketing_hook, logistics = split_caption(caption_clean)

    # Skip posts whose entire content is logistics/hashtags with no real copy
    if len(marketing_hook) < 15:
        return None

    return {
        "shortcode"      : raw.get("shortcode", ""),
        "source_url"     : raw.get("source_url", ""),
        "author"         : raw.get("author", "hot_cakesbakes"),
        "timestamp_utc"  : raw.get("timestamp_utc", ""),
        "caption_raw"    : caption_raw,
        "caption_clean"  : caption_clean,
        "marketing_hook" : marketing_hook,
        "logistics"      : logistics,
        "hashtags"       : raw.get("content", {}).get("hashtags", []),
        "mentions"       : raw.get("content", {}).get("mentions", []),
    }


def run_pipeline(
    raw_dir    : Path = RAW_DIR,
    output_dir : Path = CLEANED_DIR,
) -> list[dict]:
    """
    Process all scraped JSON files and write cleaned output.
    Returns list of processed records.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(raw_dir.glob("ig_text_*.json"))
    if not files:
        raise FileNotFoundError(f"No scraped files found in {raw_dir}")

    records : list[dict] = []
    skipped = 0

    for f in files:
        record = process_file(f)
        if record is None:
            skipped += 1
            continue
        out = output_dir / f.name
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        records.append(record)

    print(f"Pipeline complete: {len(records)} posts cleaned, {skipped} skipped (no copy)")
    return records


# ── CLI entrypoint ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    records = run_pipeline()

    if not records:
        raise SystemExit("No records produced — check scraped_dataset/ has content.")

    hooks = [r["marketing_hook"] for r in records]
    avg_len = sum(len(h) for h in hooks) / len(hooks)
    print(f"Average marketing_hook length: {avg_len:.0f} chars\n")

    df = pd.DataFrame(records)[["shortcode", "timestamp_utc", "marketing_hook"]]
    pd.set_option("display.max_colwidth", 90)
    print(df.head(8).to_string(index=False))
