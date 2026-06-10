#!/usr/bin/env python3
"""CLI scraper: extract text data from a public Instagram post or an Instagram data export."""

import argparse
import json
import lzma
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import instaloader


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Instagram shortcodes are base-64 encodings of the numeric media ID.
_SC_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def extract_shortcode(url: str) -> str:
    match = re.search(r'/(?:p|reel)/([A-Za-z0-9_-]+)', url)
    if not match:
        raise ValueError(f"Could not extract shortcode from URL: {url}")
    return match.group(1)


def build_loader(username: str | None = None) -> instaloader.Instaloader:
    """Create an Instaloader instance, loading a saved session if username is given."""
    L = instaloader.Instaloader()
    if username:
        try:
            L.load_session_from_file(username)
        except FileNotFoundError:
            print(
                f"Warning: no saved session for '{username}', continuing anonymously.",
                file=sys.stderr,
            )
    return L


def post_to_dict(post: instaloader.Post) -> dict:
    """Serialize an instaloader Post object to the structured output schema."""
    caption = post.caption or ""
    return {
        "source_url": f"https://www.instagram.com/p/{post.shortcode}/",
        "shortcode": post.shortcode,
        "owner_id": post.owner_id,
        "author": post.owner_username,
        "timestamp_utc": post.date_utc.replace(tzinfo=timezone.utc).isoformat(),
        "content": {
            "caption_raw": caption,
            "hashtags": re.findall(r"#(\w+)", caption),
            "mentions": re.findall(r"@(\w+)", caption),
            "accessibility_text": post.accessibility_caption or "",
        },
    }


def media_id_to_shortcode(media_id: int) -> str:
    """Convert Instagram's numeric media ID to its base-64 shortcode."""
    if media_id == 0:
        return "A"
    sc = ""
    while media_id > 0:
        sc = _SC_ALPHABET[media_id % 64] + sc
        media_id //= 64
    return sc


def _shortcode_from_uri(uri: str) -> str | None:
    """
    Derive a shortcode from an Instagram export media URI.

    Handles two known URI formats:
      New: media/posts/MEDIA_ID.jpg  or  media/reels/YYYYMM/MEDIA_ID.mp4
      Old: media/posts/YYYYMM/MEDIA_ID_OWNER_ID_n.jpg
    """
    # New format — bare numeric ID before extension
    match = re.search(r'/(\d{10,})\.\w+$', uri)
    if match:
        return media_id_to_shortcode(int(match.group(1)))
    # Old format — MEDIA_ID_OWNER_ID_suffix.jpg
    match = re.search(r'/(\d{10,})_\d+_\w+\.\w+$', uri)
    if match:
        return media_id_to_shortcode(int(match.group(1)))
    return None


# ---------------------------------------------------------------------------
# Scrape modes
# ---------------------------------------------------------------------------

def scrape_single(url: str, username: str | None = None) -> None:
    """Fetch and save a single post or Reel by URL."""
    shortcode = extract_shortcode(url)
    print(f"Fetching shortcode: {shortcode}")

    L = build_loader(username)
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    data = post_to_dict(post)

    output_dir = Path("scraped_dataset")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"ig_text_{shortcode}.json"
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Saved → {output_path}")


def parse_downloaded_dir(directory: str) -> None:
    """
    Parse .json.xz metadata files produced by the instaloader CLI:

        python -m instaloader --login USERNAME \\
            --no-pictures --no-videos --no-video-thumbnails PROFILE

    Converts every post into scraped_dataset/.
    """
    source_dir = Path(directory)
    if not source_dir.is_dir():
        print(f"Error: '{directory}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    meta_files = sorted(
        list(source_dir.glob("*.json.xz")) +
        [f for f in source_dir.glob("*.json") if not f.name.startswith("id_")]
    )

    if not meta_files:
        print(f"No .json.xz/.json metadata files found in '{directory}'.", file=sys.stderr)
        sys.exit(1)

    output_dir = Path("scraped_dataset")
    output_dir.mkdir(exist_ok=True)

    total = len(meta_files)
    saved = skipped = errors = 0

    for i, meta_file in enumerate(meta_files, 1):
        try:
            if meta_file.suffix == ".xz":
                blob = json.loads(lzma.decompress(meta_file.read_bytes()))
            else:
                blob = json.loads(meta_file.read_text(encoding="utf-8"))

            node = blob.get("node", blob)
            shortcode = node.get("shortcode", "")
            if not shortcode:
                print(f"[{i:>3}/{total}] SKIP  {meta_file.name} (no shortcode)")
                skipped += 1
                continue

            output_path = output_dir / f"ig_text_{shortcode}.json"
            if output_path.exists():
                print(f"[{i:>3}/{total}] SKIP  {shortcode} (already converted)")
                skipped += 1
                continue

            caption = ""
            for edge in node.get("edge_media_to_caption", {}).get("edges", []):
                caption = edge.get("node", {}).get("text", "") or ""
                if caption:
                    break

            owner = node.get("owner", {})
            ts = node.get("taken_at_timestamp", 0)

            data = {
                "source_url": f"https://www.instagram.com/p/{shortcode}/",
                "shortcode": shortcode,
                "owner_id": owner.get("id", ""),
                "author": owner.get("username", ""),
                "timestamp_utc": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "content": {
                    "caption_raw": caption,
                    "hashtags": re.findall(r"#(\w+)", caption),
                    "mentions": re.findall(r"@(\w+)", caption),
                    "accessibility_text": node.get("accessibility_caption") or "",
                },
            }

            output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"[{i:>3}/{total}] SAVED → {output_path}")
            saved += 1

        except Exception as e:
            print(f"[{i:>3}/{total}] ERROR {meta_file.name}: {e}", file=sys.stderr)
            errors += 1

    print(f"\nDone — {saved} saved, {skipped} skipped, {errors} errors  →  scraped_dataset/")


def parse_instagram_export(path: str, account: str = "hot_cakesbakes") -> None:
    """
    Parse Instagram's official data export into our schema.

    How to get the export:
      Instagram → Settings → Your Activity → Download your information
      → Some of your information → Posts → JSON format → Request download

    path: the downloaded .zip file  OR  the extracted directory.
    """
    source = Path(path)
    post_entries: list[dict] = []

    # ── Load all posts_*.json files from ZIP or directory ──────────────────
    if source.is_file() and source.suffix == ".zip":
        with zipfile.ZipFile(source) as zf:
            names = zf.namelist()
            post_targets  = [n for n in names if re.search(r'posts_\d+\.json$', n, re.I)]
            reels_targets = [n for n in names if re.search(r'reels\.json$',     n, re.I)]
            if not post_targets and not reels_targets:
                print(
                    "No posts_*.json or reels.json found in the ZIP. "
                    "Make sure you exported 'Posts' and 'Reels' in JSON format.",
                    file=sys.stderr,
                )
                sys.exit(1)
            for name in sorted(post_targets):
                chunk = json.loads(zf.read(name).decode("utf-8"))
                post_entries.extend(chunk if isinstance(chunk, list) else [chunk])
            for name in sorted(reels_targets):
                chunk = json.loads(zf.read(name).decode("utf-8"))
                reels = chunk.get("ig_reels_media", chunk if isinstance(chunk, list) else [])
                post_entries.extend(reels)

    elif source.is_dir():
        for f in sorted(source.rglob("posts_*.json")):
            chunk = json.loads(f.read_text(encoding="utf-8"))
            post_entries.extend(chunk if isinstance(chunk, list) else [chunk])
        for f in sorted(source.rglob("reels.json")):
            chunk = json.loads(f.read_text(encoding="utf-8"))
            reels = chunk.get("ig_reels_media", chunk if isinstance(chunk, list) else [])
            post_entries.extend(reels)
        if not post_entries:
            print(
                f"No posts or reels data found under '{path}'. "
                "Make sure you exported 'Posts' and 'Reels' in JSON format.",
                file=sys.stderr,
            )

    else:
        print(f"Error: '{path}' must be a .zip file or directory.", file=sys.stderr)
        sys.exit(1)

    if not post_entries:
        print("Export loaded but no post entries found.", file=sys.stderr)
        sys.exit(1)

    output_dir = Path("scraped_dataset")
    output_dir.mkdir(exist_ok=True)

    total = len(post_entries)
    saved = skipped = errors = 0

    print(f"Found {total} posts in export. Converting…\n")

    for i, entry in enumerate(post_entries, 1):
        try:
            # Instagram wraps each post: {"media": [{...}, ...]}
            media_list = entry.get("media", [entry])
            if not media_list:
                skipped += 1
                continue

            primary = media_list[0]           # use first item for shared metadata
            caption  = primary.get("title", "") or ""
            ts       = primary.get("creation_timestamp", 0)
            uri      = primary.get("uri", "")

            # Derive shortcode from media URI (base-64 of numeric media ID)
            shortcode = _shortcode_from_uri(uri)
            file_id   = shortcode or f"ts_{ts}"

            output_path = output_dir / f"ig_text_{file_id}.json"
            if output_path.exists():
                print(f"[{i:>3}/{total}] SKIP  {file_id} (already converted)")
                skipped += 1
                continue

            data = {
                "source_url": (
                    f"https://www.instagram.com/p/{shortcode}/" if shortcode else ""
                ),
                "shortcode": shortcode or "",
                "owner_id":  "",
                "author":    account,
                "timestamp_utc": (
                    datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else ""
                ),
                "content": {
                    "caption_raw": caption,
                    "hashtags":  re.findall(r"#(\w+)", caption),
                    "mentions":  re.findall(r"@(\w+)", caption),
                    "accessibility_text": "",
                },
            }

            output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"[{i:>3}/{total}] SAVED → {output_path}")
            saved += 1

        except Exception as e:
            print(f"[{i:>3}/{total}] ERROR entry {i}: {e}", file=sys.stderr)
            errors += 1

    print(f"\nDone — {saved} saved, {skipped} skipped, {errors} errors  →  scraped_dataset/")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Instagram text data from a single post or an official data export.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # single post / reel (still works fine)
  python ig_scraper.py -u hot_cakesbakes "https://www.instagram.com/reel/DVsNBMGjCOs/"

  # bulk: parse Instagram's official data export (ZIP or extracted directory)
  python ig_scraper.py --parse-export ~/Downloads/instagram-hot_cakesbakes.zip
  python ig_scraper.py --parse-export ~/Downloads/instagram-export-dir/

  # bulk: parse instaloader CLI download (if CLI worked)
  python ig_scraper.py --parse-dir hot_cakesbakes/
""",
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Single post or Reel URL",
    )
    parser.add_argument(
        "-u", "--username",
        default=None,
        help="Instagram username whose saved instaloader session to load",
    )
    parser.add_argument(
        "--parse-export",
        default=None,
        metavar="PATH",
        help="Parse Instagram's official data export (.zip or extracted directory)",
    )
    parser.add_argument(
        "--account",
        default="hot_cakesbakes",
        metavar="USERNAME",
        help="Account name to embed in export-parsed records (default: hot_cakesbakes)",
    )
    parser.add_argument(
        "--parse-dir",
        default=None,
        metavar="DIRECTORY",
        help="Parse instaloader CLI-downloaded .json.xz files from this directory",
    )
    args = parser.parse_args()

    if not args.url and not args.parse_export and not args.parse_dir:
        parser.error("Provide a post URL, --parse-export PATH, or --parse-dir DIRECTORY")

    if args.parse_export:
        parse_instagram_export(args.parse_export, account=args.account)
    elif args.parse_dir:
        parse_downloaded_dir(args.parse_dir)
    else:
        try:
            scrape_single(args.url, username=args.username)
        except instaloader.exceptions.InstaloaderException as e:
            print(f"Instaloader error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
