# StyleSync — Data Catalog

A reference for every data file in the project: where it comes from, what it contains, and who reads it.

---

## Table of Contents

1. [Data Flow Overview](#1-data-flow-overview)
2. [Scraped Dataset](#2-scraped-dataset-scraped_dataset)
3. [Cleaned Records](#3-cleaned-records-datacleaned)
4. [Brand Profile](#4-brand-profile-databrand_profilejson)
5. [Clusters](#5-clusters-dataclustersjson)
6. [Demo Snapshots](#6-demo-snapshots)
7. [Field Reference Index](#7-field-reference-index)

---

## 1. Data Flow Overview

```
Instagram (public profile or export ZIP)
    │
    ▼
scraped_dataset/ig_text_{shortcode}.json   ← Stage 0: raw per-post files
    │
    ▼  src/data/pipeline.py
data/cleaned/{shortcode}.json              ← Stage 1: cleaned, normalized
    │
    ▼  src/embeddings/cluster.py
data/clusters.json                         ← Stage 2: cluster assignments + profiles
    │
    ▼  src/embeddings/profile_extractor.py
data/brand_profile.json                    ← Stage 3: brand voice profile (Granite)
```

The `api/` layer reads only from `data/brand_profile.json` and `data/clusters.json`. It never touches `scraped_dataset/` or `data/cleaned/` at runtime.

---

## 2. Scraped Dataset (`scraped_dataset/`)

**Written by:** `src/scrapers/instaloader_scraper.py` (Instaloader path) or `ig_scraper.py` (export path)  
**Read by:** `src/data/pipeline.py`  
**Gitignored:** Yes — contains raw user content

### Filename pattern

```
scraped_dataset/ig_text_{shortcode}.json
```

One file per Instagram post. `shortcode` is the post's unique identifier (the string after `/p/` in the Instagram URL).

### Schema

```json
{
  "source_url"     : "https://www.instagram.com/p/CxYZ1234567/",
  "shortcode"      : "CxYZ1234567",
  "owner_id"       : "123456789",
  "author"         : "hot_cakesbakes",
  "timestamp_utc"  : "2025-10-15T08:30:00",
  "content": {
    "caption_raw"         : "Full caption text including hashtags and emojis...",
    "hashtags"            : ["bomboloni", "homebakery", "navimumai"],
    "mentions"            : ["someaccount"],
    "accessibility_text"  : "Photo description from Instagram alt text (may be empty)"
  }
}
```

### Field notes

| Field | Type | Notes |
|-------|------|-------|
| `source_url` | string | Canonical Instagram post URL |
| `shortcode` | string | Instagram's internal post ID; used as filename key |
| `owner_id` | string | Numeric account ID as string |
| `author` | string | Username without `@`; used as brand handle fallback |
| `timestamp_utc` | string | ISO 8601 UTC datetime; used for Voice Timeline month bucketing |
| `caption_raw` | string | Full caption as posted, including `#hashtags` and `@mentions` |
| `hashtags` | string[] | Extracted from `caption_raw` via regex `#(\w+)` |
| `mentions` | string[] | Extracted from `caption_raw` via regex `@(\w+)` |
| `accessibility_text` | string | Instagram's auto-generated image description; usually empty |

---

## 3. Cleaned Records (`data/cleaned/`)

**Written by:** `src/data/pipeline.py`  
**Read by:** `src/embeddings/cluster.py`, `src/embeddings/profile_extractor.py`  
**Gitignored:** Yes — derived from scraped content

### Filename pattern

```
data/cleaned/{shortcode}.json
```

One file per post that passes cleaning (non-empty caption after ftfy normalization).

### Schema

```json
{
  "shortcode"     : "CxYZ1234567",
  "author"        : "hot_cakesbakes",
  "timestamp_utc" : "2025-10-15T08:30:00",
  "source_url"    : "https://www.instagram.com/p/CxYZ1234567/",
  "hook"          : "Made with love, baked with care.",
  "caption_clean" : "Made with love, baked with care. Available every Saturday. Order via DM. 🍰",
  "hashtags"      : ["homebakery", "bomboloni"],
  "word_count"    : 14
}
```

### Field notes

| Field | Type | Notes |
|-------|------|-------|
| `hook` | string | First sentence of the caption (split on `. ` or `\n`); used as the creative lead-in |
| `caption_clean` | string | Full caption after ftfy unicode normalization and whitespace cleanup |
| `word_count` | int | Word count of `caption_clean`; posts under 3 words are filtered out |

Posts with `word_count < 3` are excluded. Posts with an empty `caption_raw` in the scraped file are excluded. All other fields are carried through from the scraped file unchanged.

---

## 4. Brand Profile (`data/brand_profile.json`)

**Written by:** `src/embeddings/profile_extractor.py` (Granite 3.1 8B)  
**Read by:** `api/routers/brand.py`, all `src/generation/*.py` modules  
**Gitignored:** No (demo version committed; active version is regenerated per account)

### Schema

```json
{
  "brand_name"        : "HotCakes Bakes",
  "ig_handle"         : "@hot_cakesbakes",
  "post_count"        : 113,
  "date_range"        : "October 2025 – June 2026",
  "content_pillars"   : [
    "Homemade Classics",
    "Fusion Specials",
    "Behind the Scenes",
    "Nutella Series",
    "Bomboloni"
  ],
  "tone_descriptors"  : ["warm", "indulgent", "playful", "relatable", "passionate"],
  "signature_phrases" : ["made with love", "fresh every day", "order via DM"],
  "avoided_terms"     : ["cheap", "discount", "buy now"],
  "recurring_words"   : ["fresh", "homemade", "baked", "love", "order"],
  "visual_style_notes": "Warm natural lighting, close-up textures, rustic wooden surfaces",
  "target_audience"   : "Home bakers and dessert lovers in Navi Mumbai aged 18-35",
  "cluster_profiles"  : {
    "0": {
      "cluster_id"       : 0,
      "pillar"           : "Homemade Classics",
      "post_count"       : 34,
      "tone_descriptors" : ["loving", "passionate", "dedicated"],
      "signature_phrases": ["made with love", "eggless and delicious"],
      "avoided_terms"    : ["cheap", "mass-produced"],
      "recurring_words"  : ["eggless", "moist", "homemade", "love"],
      "visual_style_notes": "Warm overhead shots, wooden boards, powdered sugar details"
    }
  }
}
```

### Top-level field reference

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `brand_name` | string | Passed into `BrandProfileExtractor` constructor | Defaults to `"HotCakes Bakes"` |
| `ig_handle` | string | Passed into constructor | Stored with leading `@` |
| `post_count` | int | Counted from cleaned records | Total posts that passed pipeline Stage 1 |
| `date_range` | string | Computed from `timestamp_utc` min/max | Human-readable e.g. `"October 2025 – June 2026"` |
| `content_pillars` | string[] | From `_CLUSTER_ID_LABELS` constant | Order matches cluster IDs 0-4 |
| `tone_descriptors` | string[] | Granite extraction | 5-8 adjectives describing overall brand voice |
| `signature_phrases` | string[] | Granite extraction | Verbatim phrases that appear frequently |
| `avoided_terms` | string[] | Granite extraction | Words/phrases that feel off-brand |
| `recurring_words` | string[] | Granite extraction | Single words counted across all captions |
| `visual_style_notes` | string | Granite extraction | Free-text description of visual aesthetic |
| `target_audience` | string | Granite extraction | One-sentence audience description |
| `cluster_profiles` | object | Keyed by cluster ID string | Per-cluster voice profiles (see below) |

### `cluster_profiles[n]` field reference

| Field | Type | Notes |
|-------|------|-------|
| `cluster_id` | int | 0-4; matches K-Means label |
| `pillar` | string | Human-readable pillar name from `_CLUSTER_ID_LABELS` |
| `post_count` | int | Number of posts assigned to this cluster |
| `tone_descriptors` | string[] | Cluster-specific tone (distinct from top-level) |
| `signature_phrases` | string[] | Phrases characteristic of this pillar |
| `avoided_terms` | string[] | Terms that undercut this pillar's voice |
| `recurring_words` | string[] | Most frequent words in this cluster |
| `visual_style_notes` | string | Visual direction for this content type |

### Consumers

| Consumer | Fields used |
|----------|------------|
| `api/routers/brand.py` `GET /profile` | All top-level fields |
| `api/routers/brand.py` `GET /clusters` | `cluster_profiles` merged with raw clusters |
| `src/generation/caption_generator.py` | `tone_descriptors`, `signature_phrases`, `avoided_terms`, cluster-specific fields |
| `src/generation/image_prompt_generator.py` | `visual_style_notes`, `tone_descriptors` |
| `src/generation/why_engine.py` | Full profile for benchmarking post against brand standard |
| `src/generation/voice_timeline.py` | `date_range`, `content_pillars` |
| `src/generation/strategic_insights.py` | `cluster_profiles[n].post_count` for richness scoring |
| `src/generation/script_generator.py` | Cluster-specific `tone_descriptors`, `signature_phrases` |
| `src/generation/blank_page_solver.py` | Top-level `tone_descriptors`, `content_pillars` |
| `frontend/components/layout/Sidebar.tsx` | `brand_name`, `handle`, `content_pillars`, `tone_descriptors` |

---

## 5. Clusters (`data/clusters.json`)

**Written by:** `src/embeddings/cluster.py`  
**Read by:** `api/routers/brand.py`, `api/routers/discover.py`  
**Gitignored:** No (demo version committed)

### Schema

```json
{
  "0": {
    "cluster_id"   : 0,
    "post_count"   : 34,
    "posts"        : [
      {
        "shortcode"     : "CxYZ1234567",
        "timestamp_utc" : "2025-10-15T08:30:00",
        "caption_clean" : "Made with love, baked with care...",
        "hook"          : "Made with love, baked with care.",
        "hashtags"      : ["homebakery", "eggless"]
      }
    ]
  }
}
```

The top-level keys are cluster ID strings (`"0"` through `"4"`). Each cluster contains:

| Field | Type | Notes |
|-------|------|-------|
| `cluster_id` | int | 0-4; matches K-Means label |
| `post_count` | int | Number of posts in this cluster |
| `posts` | object[] | All posts assigned to this cluster |
| `posts[n].shortcode` | string | Links back to `scraped_dataset/ig_text_{shortcode}.json` |
| `posts[n].timestamp_utc` | string | Used by `discover.py` for monthly bucketing |
| `posts[n].caption_clean` | string | Full normalized caption |
| `posts[n].hook` | string | First sentence; shown in UI sample captions |
| `posts[n].hashtags` | string[] | Extracted hashtags |

### How `GET /api/brand/clusters` enriches this

The `brand.py` router merges `clusters.json` with `brand_profile.json` to produce the response served to the frontend. For each cluster it adds:
- `pillar` — human-readable label from `_CLUSTER_ID_LABELS`
- `tone_descriptors`, `signature_phrases`, `avoided_terms`, `recurring_words` — from `cluster_profiles[n]` in `brand_profile.json`
- `sample_captions` — the first 3 `hook` strings from `posts`

---

## 6. Demo Snapshots

| File | Contents | When used |
|------|----------|-----------|
| `data/demo_brand_profile.json` | Full @hot_cakesbakes brand profile | `POST /api/onboard/reset-demo` copies this to `brand_profile.json` |
| `data/demo_clusters.json` | Full @hot_cakesbakes cluster data | `POST /api/onboard/reset-demo` copies this to `clusters.json` |

These files are committed to the repository and serve as the always-available fallback for demos. They should not be modified manually — if the pipeline produces an improved @hot_cakesbakes profile, update them:

```bash
cp data/brand_profile.json data/demo_brand_profile.json
cp data/clusters.json data/demo_clusters.json
git add data/demo_brand_profile.json data/demo_clusters.json
git commit -m "chore: refresh demo snapshots from latest pipeline run"
```

---

## 7. Field Reference Index

Quick lookup for any field name you encounter across the codebase.

| Field | File(s) | Description |
|-------|---------|-------------|
| `author` | scraped, cleaned | Instagram username without `@` |
| `avoided_terms` | brand_profile, clusters | Words that undercut the brand voice |
| `brand_name` | brand_profile | Human-readable brand name |
| `caption_clean` | cleaned, clusters | Normalized full caption text |
| `caption_raw` | scraped | Raw caption as posted on Instagram |
| `cluster_id` | clusters, brand_profile | Integer 0-4; K-Means assignment |
| `cluster_profiles` | brand_profile | Nested per-cluster voice objects |
| `content_pillars` | brand_profile | Ordered list matching cluster IDs 0-4 |
| `date_range` | brand_profile | Human-readable posting date range |
| `hashtags` | scraped, cleaned, clusters | Extracted `#tag` strings (without `#`) |
| `hook` | cleaned, clusters | First sentence of `caption_clean` |
| `ig_handle` | brand_profile | Account handle with leading `@` |
| `mentions` | scraped | Extracted `@mention` strings (without `@`) |
| `owner_id` | scraped | Numeric Instagram account ID as string |
| `pillar` | clusters (merged) | Human-readable cluster name |
| `post_count` | clusters, brand_profile | Number of posts in a cluster |
| `posts` | clusters | Array of cleaned post objects for a cluster |
| `recurring_words` | brand_profile, clusters | High-frequency single words |
| `sample_captions` | clusters (merged) | First 3 hook strings (API-only, not on disk) |
| `shortcode` | scraped, cleaned, clusters | Instagram post ID (after `/p/` in URL) |
| `signature_phrases` | brand_profile, clusters | Verbatim brand phrases |
| `source_url` | scraped, cleaned | Canonical `instagram.com/p/...` URL |
| `target_audience` | brand_profile | One-sentence audience description |
| `timestamp_utc` | scraped, cleaned, clusters | ISO 8601 UTC string |
| `tone_descriptors` | brand_profile, clusters | Adjectives describing voice/tone |
| `visual_style_notes` | brand_profile, clusters | Free-text visual direction |
| `word_count` | cleaned | Word count of `caption_clean` |
