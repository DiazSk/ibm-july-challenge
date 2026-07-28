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
# Classification is per LINE, not per paragraph. These captions routinely put a
# contact line directly under a line of real brand voice inside one paragraph,
# so paragraph granularity throws away the voice along with the phone number.
#
# Strong signals: a line matching any of these is contact/ordering information
# and never brand voice.
_STRONG_PATTERNS = [
    r"📍|📩|📞|☎️|📱|🚚|🛵",
    r"\b\d{10}\b",                                   # 10-digit phone number
    r"\bwhatsapp\b",
    r"\bdm\b",                                       # "DM to order", "DM to book yours"
    r"\border\s+(?:now|here|via)\b",
    r"\bpre.?order\b",
    r"\b(free\s+(?:home\s+)?delivery|pickup\s+available|home\s+delivery)\b",
    r"\border\s+\d+\s*day",                          # "order 1 day prior"
    r"\b(?:for|to)\s+orders?\b",                     # "For Orders" section header
    r"\bfollow\s+@\w+",                              # "Follow @hot_cakesbakes"
    r"\bfor\s+more\s+(delicious\s+)?updates\b",
]
_STRONG_RE = re.compile("|".join(_STRONG_PATTERNS), re.IGNORECASE)

# Weak signal: a place name. A bare "📍 Taloja" line is logistics, but
# "Fresh homemade Bomboloni available in Taloja." is marketing copy that happens
# to name the city — so this only condemns a line short enough to be an address.
# Treating it as a strong signal is what silently deleted 41 posts (6.3M reach),
# including the account's best-performing reel.
_LOCATION_RE      = re.compile(r"\b(taloja|navi\s*mumbai|mumbai)\b", re.IGNORECASE)
_LOCATION_MAX_LEN = 40

# Emoji ranges — used only to tell brand voice apart from SEO keyword spam.
_EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def _is_hashtag_block(line: str) -> bool:
    """
    Every token starts with '#'. Token-based rather than a `#\\w+` regex because
    tags like "#explorepage✨" carry trailing emoji, and one of those was enough
    to make a 164-character wall of hashtags read as brand voice.
    """
    tokens = line.split()
    return bool(tokens) and all(t.startswith("#") for t in tokens)


def _is_keyword_block(line: str) -> bool:
    """
    Comma-separated SEO keyword spam that trails many captions, e.g.
    "Homemade dessert,Italian Bomboloni,soft fluffy Bomboloni ,Taloja home baker".

    Left in, these dominate `recurring_words` and `signature_phrases` and the
    voice profile learns keyword spam instead of the brand's actual voice.
    Real copy in this corpus carries emoji and sentence punctuation; these don't.
    """
    if line.count(",") < 3 or len(line) <= 50:
        return False
    if _EMOJI_RE.search(line):
        return False
    return "." not in line


def _is_logistics(line: str) -> bool:
    if _STRONG_RE.search(line):
        return True
    return bool(_LOCATION_RE.search(line)) and len(line) < _LOCATION_MAX_LEN


def split_caption(text: str) -> tuple[str, str]:
    """
    Split a cleaned caption into (marketing_hook, logistics).

    Walks line by line. Contact/ordering lines go to logistics; hashtag-only and
    SEO keyword lines are dropped from both (they are neither voice nor useful
    logistics). Everything else is the hook. Blank lines are preserved so
    paragraph breaks in the surviving copy survive too.
    """
    hook_lines      : list[str] = []
    logistics_parts : list[str] = []

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            hook_lines.append("")
            continue
        if _is_hashtag_block(line) or _is_keyword_block(line):
            continue
        if _is_logistics(line):
            logistics_parts.append(line)
            continue
        hook_lines.append(line)

    hook = re.sub(r"\n{3,}", "\n\n", "\n".join(hook_lines)).strip()
    return hook, "\n".join(logistics_parts).strip()


def clean_text(text: str) -> str:
    """
    Fix mojibake (â€™ → ', â€¦ → …) and normalize Unicode using ftfy.
    Preserves emoji characters — ftfy only repairs broken encodings.
    """
    return ftfy.fix_text(text).strip()


_MIN_HOOK_CHARS = 15


def _has_reach(engagement: dict) -> bool:
    try:
        return float(engagement.get("reach") or 0) > 0
    except (TypeError, ValueError):
        return False


def process_file(path: Path) -> dict | None:
    """
    Load, clean, and split a single scraped JSON file.

    Returns None only for posts that have neither usable marketing copy nor real
    engagement metrics. A post with thin copy but real metrics is kept with an
    empty hook: clustering skips it (voice must stay caption-derived) but every
    analytics surface still counts it.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))

    caption_raw = raw.get("content", {}).get("caption_raw", "").strip()

    # Carry real engagement metrics through to the cleaned record. The Graph
    # API uses "saved"; normalize to "saves" so every downstream consumer
    # (cluster_engagement, insights, boost advisor) sees one name.
    engagement = dict(raw.get("engagement") or {})
    if "saved" in engagement and "saves" not in engagement:
        engagement["saves"] = engagement.pop("saved")

    caption_clean             = clean_text(caption_raw) if caption_raw else ""
    marketing_hook, logistics = split_caption(caption_clean) if caption_clean else ("", "")

    if len(marketing_hook) < _MIN_HOOK_CHARS:
        # No voice to learn from — but dropping the record entirely is what hid
        # 41 posts and 6.3M reach from every KPI, chart and recommendation.
        if not _has_reach(engagement):
            return None
        marketing_hook = ""

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
        "engagement"     : engagement,
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

    # Mirror raw_dir exactly: drop cleaned files from any previous run so a
    # re-sync (or switching accounts) can't leave stale posts to be clustered.
    for stale in output_dir.glob("ig_text_*.json"):
        stale.unlink()

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
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        records.append(record)

    print(f"Pipeline complete: {len(records)} posts cleaned, {skipped} skipped (no copy)")
    return records


# ── Offline self-check ──────────────────────────────────────────────────────

def _demo() -> None:
    """Fixtures are real captions from the corpus. Run: python -m src.data.pipeline --check"""

    # The 5.2M-reach reel. Its first line names the city inside real copy; the
    # old paragraph-cascade splitter turned the whole caption into logistics.
    viral = (
        "100% Fresh homemade Bomboloni available in Taloja. Perfect for dessert "
        "cravings or late night sweet treats.\n\n"
        "📍 Free home delivery in Taloja\n"
        "📩 DM for Ramzan offers\n"
        "📞 To order: 8108446425(what's app)\n"
        "📩 Order 1 day prior \n\n"
        "Follow @hot_cakesbakes For more delicious updates.\n\n"
        "Homemade dessert,Italian Bomboloni,soft fluffy Bomboloni ,Taloja homemade "
        "dessert,satisfying frying,bakery reel \n\n"
        "#bombolone #bomboloni"
    )
    hook, logistics = split_caption(clean_text(viral))
    assert hook.startswith("100% Fresh homemade Bomboloni available in Taloja."), hook
    assert "Perfect for dessert cravings" in hook, hook
    assert "8108446425" not in hook, hook
    assert "Free home delivery" not in hook, hook
    assert "satisfying frying" not in hook, hook          # SEO block stripped
    assert "#bombolone" not in hook, hook
    assert "Follow @hot_cakesbakes" not in hook, hook
    assert len(hook) >= _MIN_HOOK_CHARS, hook
    assert "8108446425" in logistics, logistics

    # An inline CTA sitting between two lines of real voice: drop the CTA line,
    # keep the voice either side of it.
    inline = (
        "Taloja's softest Bomboloni just dropped 🍩🔥\n"
        "Freshly fried. Fluffy. Irresistible.\n"
        "DM to book yours 🤍"
    )
    hook, _ = split_caption(clean_text(inline))
    assert "softest Bomboloni just dropped" in hook, hook
    assert "Freshly fried" in hook, hook
    assert "DM to book" not in hook, hook

    # Hashtags only → nothing to learn. The emoji-suffixed tag is the real case
    # that defeated the old `#\w+` regex.
    assert split_caption("#donuts #bomboloni #taloja")[0] == ""
    assert _is_hashtag_block("#taloja #explorepage✨ #softandfluffy") is True
    assert _is_hashtag_block("Tag someone who needs this #donuts") is False

    # "For Orders" is a section header, not voice.
    assert _is_logistics("For Orders") is True

    # A short bare address line is logistics; the same city inside a sentence is not.
    assert _is_logistics("Taloja, Navi Mumbai") is True
    assert _is_logistics(
        "Fresh homemade Bomboloni available in Taloja. Perfect for late night cravings."
    ) is False

    # Keyword-block detector must not eat ordinary comma-rich brand voice.
    assert _is_keyword_block(
        "Homemade dessert,Italian Bomboloni,soft fluffy Bomboloni ,Taloja home baker,bakery reel"
    ) is True
    assert _is_keyword_block("Soft, fluffy, fresh, and made with love") is False
    assert _is_keyword_block("Soft, sugary Bomboloni filled with rich chocolate 🤤🍫") is False

    # Trailing logistics after real copy still splits cleanly.
    hook, logistics = split_caption(clean_text(
        "Say it with brownies. 🤎\n\n📞 To order: 9876543210"
    ))
    assert hook == "Say it with brownies. 🤎", hook
    assert "9876543210" in logistics, logistics

    print("pipeline self-check passed.")


# ── CLI entrypoint ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        _demo()
        raise SystemExit(0)

    records = run_pipeline()

    if not records:
        raise SystemExit("No records produced — check scraped_dataset/ has content.")

    hooks = [r["marketing_hook"] for r in records]
    avg_len = sum(len(h) for h in hooks) / len(hooks)
    print(f"Average marketing_hook length: {avg_len:.0f} chars\n")

    df = pd.DataFrame(records)[["shortcode", "timestamp_utc", "marketing_hook"]]
    pd.set_option("display.max_colwidth", 90)
    print(df.head(8).to_string(index=False))
