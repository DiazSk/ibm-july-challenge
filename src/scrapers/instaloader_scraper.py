"""
Instaloader-based Instagram profile scraper.

Fetches all posts from a public Instagram account and writes them to
scraped_dataset/ in the exact schema consumed by src/data/pipeline.py.

No API keys required — uses Instaloader for anonymous public scraping.
"""

import json
import re
import sys
from datetime import timezone
from pathlib import Path

import instaloader

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRAPED_DIR  = _PROJECT_ROOT / "scraped_dataset"


def scrape_profile(username: str, max_posts: int = 200) -> int:
    """
    Scrape a public Instagram profile and write posts to scraped_dataset/.

    Clears any existing scraped_dataset/ files first so the pipeline always
    runs on clean data for the current account.

    Returns the number of posts saved.

    Raises RuntimeError with a user-friendly message if:
    - The profile is private or doesn't exist
    - Instagram rate-limits the request
    """
    handle = username.lstrip("@").strip()
    if not handle:
        raise RuntimeError("Please enter a valid Instagram username.")

    # Clear previous account's data
    _SCRAPED_DIR.mkdir(exist_ok=True)
    for f in _SCRAPED_DIR.glob("ig_text_*.json"):
        f.unlink()

    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    try:
        profile = instaloader.Profile.from_username(L.context, handle)
    except instaloader.exceptions.ProfileNotExistsException:
        # instaloader reports this even when the account is real: an anonymous
        # scrape getting rate-limited/blocked by Instagram (403 on their end)
        # surfaces through instaloader as "profile does not exist," not as a
        # distinct blocked/rate-limited error. So this message can't promise
        # the account is actually missing.
        raise RuntimeError(
            f"Couldn't find @{handle} — or Instagram blocked this anonymous scrape "
            "(it does that a lot). If the account is real, use \"Connect Instagram "
            "(real-time)\" instead — it authenticates properly and isn't affected."
        )
    except instaloader.exceptions.LoginRequiredException:
        raise RuntimeError(
            f"@{handle} is a private account. Use the data export option instead."
        )
    except instaloader.exceptions.ConnectionException as e:
        raise RuntimeError(
            f"Could not connect to Instagram: {e}. "
            "Try again in a few minutes or use the data export option."
        )

    if profile.is_private:
        raise RuntimeError(
            f"@{handle} is a private account. Use the data export option instead."
        )

    saved = 0
    for post in profile.get_posts():
        if saved >= max_posts:
            break
        try:
            caption = post.caption or ""
            shortcode = post.shortcode

            data = {
                "source_url"   : f"https://www.instagram.com/p/{shortcode}/",
                "shortcode"    : shortcode,
                "owner_id"     : str(post.owner_id),
                "author"       : post.owner_username,
                "timestamp_utc": post.date_utc.replace(tzinfo=timezone.utc).isoformat(),
                "content": {
                    "caption_raw"       : caption,
                    "hashtags"          : re.findall(r"#(\w+)", caption),
                    "mentions"          : re.findall(r"@(\w+)", caption),
                    "accessibility_text": post.accessibility_caption or "",
                },
            }

            out = _SCRAPED_DIR / f"ig_text_{shortcode}.json"
            out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            saved += 1

        except instaloader.exceptions.TooManyRequestsException:
            # Instagram rate-limited us — return what we have
            print(
                f"Instagram rate limit hit after {saved} posts. "
                "Proceeding with partial data.",
                file=sys.stderr,
            )
            break
        except Exception:
            # Skip individual post errors silently
            continue

    if saved == 0:
        raise RuntimeError(
            f"No posts found for @{handle}. "
            "The account may be empty or Instagram blocked the request. "
            "Try the data export option instead."
        )

    return saved
