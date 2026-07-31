# StyleSync — Data Catalog

A reference for every data file in the project: where it comes from, what it contains, and who reads it.

---

## Table of Contents

1. [Data Flow Overview](#1-data-flow-overview)
2. [Scraped Dataset](#2-scraped-dataset-scraped_dataset)
3. [Cleaned Records](#3-cleaned-records-datacleaned)
4. [Brand Profile](#4-brand-profile-databrand_profilejson)
5. [Clusters](#5-clusters-dataclustersjson)
6. [Instagram Connection](#6-instagram-connection-dataig_connectionjson)
7. [Content Workbench](#7-content-workbench-dataworkbenchdb)
8. [Diagnoses Cache](#8-diagnoses-cache-datadiagnoses)
9. [Agent Memory (ChromaDB)](#9-agent-memory-chromadb-datachroma)
10. [Demo Snapshots](#10-demo-snapshots)
11. [Field Reference Index](#11-field-reference-index)

---

## 1. Data Flow Overview

```
Instagram (public profile, export ZIP, or live Graph API connection)
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
    │
    ▼  src/data/insights.py (aggregate_cluster_engagement, run from run_pipeline.py)
data/clusters.json["cluster_engagement"]   ← Stage 4: engagement stats merged back in
```

The `api/` layer reads mainly from `data/brand_profile.json` and `data/clusters.json` at request time; it never touches `scraped_dataset/` or `data/cleaned/` at runtime (those are pipeline-stage-only). Several features maintain their own separate stores alongside the pipeline output — `data/ig_connection.json` (OAuth state), `data/workbench.db` (saved assets), `data/diagnoses/` (per-post Why Engine cache), and `data/chroma/` (agent memory) — documented in their own sections below.

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

Note: `api/routers/diagnose.py` reads `content.visual_description` from this same file for the Why Engine — approximate field, written by the moondream vision preprocessor (not confirmed in this pass; see `src/scrapers/` for the writer).

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

**Written by:** `src/embeddings/profile_extractor.py` (Granite 3.1 8B), via `BrandProfileExtractor.build_brand_profile()`
**Read by:** `api/routers/brand.py`, `src/generation/recovery_brief.py`, `api/routers/diagnose.py`, and most `src/generation/*.py` / `src/agents/*.py` modules
**Gitignored:** No (demo version committed as `data/demo_brand_profile.json`; active version is regenerated per account)

> **Schema correction:** this file was previously documented with flat top-level `content_pillars` / `tone_descriptors` / `signature_phrases` / `avoided_terms` / `recurring_words` arrays, and `cluster_profiles` as an **object keyed by cluster-id string** (`"0"`–`"4"`) with flat per-cluster fields. That is no longer accurate. `cluster_profiles` is a **list**, each entry has its own `cluster_id` and `post_count`, and all Granite-extracted content lives inside a nested `profile` object per entry. There is no top-level `content_pillars`, `tone_descriptors`, `signature_phrases`, `avoided_terms`, `recurring_words`, `post_count`, `date_range`, `visual_style_notes`, or `target_audience` field on disk — those are computed **at request time** by `api/routers/brand.py`'s `GET /profile` (unioned across all clusters), not persisted.

### Schema (verified against the current file on disk)

```json
{
  "brand_name"        : "Hot Cakesbakes",
  "ig_handle"         : "@hot_cakesbakes",
  "brand_bio"         : "Hot Cakesbakes — Instagram creator analyzed by StyleSync.",
  "timezone"          : "Asia/Kolkata",
  "model_used"        : "granite3.1-dense:8b",
  "inference_backend" : "ollama-local",
  "n_clusters"        : 5,
  "cluster_profiles"  : [
    {
      "cluster_id": 0,
      "post_count": 2,
      "profile": {
        "content_pillar": "Golden Delights",
        "tone_descriptors": ["playful", "nostalgic", "indulgent"],
        "vocabulary_patterns": {
          "recurring_words"  : ["golden", "never", "old"],
          "signature_phrases": ["That golden turn never gets old"],
          "emoji_style"      : "Uses emojis to emphasize the color and appeal of the baked goods."
        },
        "avoided_terms": ["specific ingredients", "dietary information", "ordering details"],
        "structural_signature": "Posts highlight a specific aspect or color theme...",
        "representative_post": "That golden turn never gets old 🍩✨"
      }
    }
  ]
}
```

### Top-level field reference

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `brand_name` | string | `BrandProfileExtractor` constructor param | Defaults to `"HotCakes Bakes"` |
| `ig_handle` | string | Constructor param | Stored with leading `@` |
| `brand_bio` | string | Constructor param | Free-text one-liner passed into every Granite prompt for context |
| `timezone` | string | Set once at onboarding, preserved across re-runs by `_existing_timezone()` | IANA name (e.g. `"Asia/Kolkata"`); a re-sync never resets it. Approximate on the demo snapshot — `data/demo_brand_profile.json` does not currently have this key. |
| `model_used` | string | `self.model` | e.g. `"granite3.1-dense:8b"` |
| `inference_backend` | string | Hard-coded | Always `"ollama-local"` currently |
| `n_clusters` | int | `len(cluster_profiles)` | Number of clusters that actually got a voice profile (excludes the metrics-only/uncategorized bucket, so can be less than `clusters.json`'s `n_clusters`) |
| `cluster_profiles` | object[] | One entry per non-empty, non-uncategorized cluster | List, not a dict — see below |

### `cluster_profiles[n]` field reference

| Field | Type | Notes |
|-------|------|-------|
| `cluster_profiles[n].cluster_id` | int | Matches the K-Means label / `clusters.json` cluster key |
| `cluster_profiles[n].post_count` | int | Number of posts assigned to this cluster (from `clusters.json`) |
| `cluster_profiles[n].profile` | object | The Granite-extracted voice profile — see below. Nested; there is no `cluster_profiles[n].tone_descriptors` etc. directly — it's `cluster_profiles[n].profile.tone_descriptors` |
| `cluster_profiles[n].profile.content_pillar` | string | 2-4 word Title Case pillar name; deduplicated across clusters by a second Granite pass (`dedupe_pillar_names`) if two collide |
| `cluster_profiles[n].profile.tone_descriptors` | string[] | 3-5 adjectives, this cluster only |
| `cluster_profiles[n].profile.vocabulary_patterns.recurring_words` | string[] | Frequent words/phrases in this cluster |
| `cluster_profiles[n].profile.vocabulary_patterns.signature_phrases` | string[] | Verbatim phrases characteristic of this pillar |
| `cluster_profiles[n].profile.vocabulary_patterns.emoji_style` | string | One-sentence description of emoji usage in this cluster |
| `cluster_profiles[n].profile.avoided_terms` | string[] | Terms/styles conspicuously absent from this cluster |
| `cluster_profiles[n].profile.structural_signature` | string | One-sentence description of how posts in this cluster are built |
| `cluster_profiles[n].profile.representative_post` | string | Verbatim copy of the most on-brand post in the cluster |
| `cluster_profiles[n].profile.parse_error` | bool | Present only when Granite's JSON failed to parse; if so, `profile.raw_response` holds the unparsed text instead of the fields above |

### Consumers

| Consumer | Fields used |
|----------|------------|
| `api/routers/brand.py` `GET /profile` | Iterates `cluster_profiles` (list), unions `profile.tone_descriptors`, `profile.avoided_terms`, `profile.vocabulary_patterns.signature_phrases`, `profile.vocabulary_patterns.recurring_words` across all clusters into brand-wide arrays; adds `pillar_label(cluster_id)` for `content_pillars` |
| `api/routers/brand.py` `GET /clusters` | Builds a `cluster_id → cluster_profiles entry` lookup, merges each cluster's `profile.*` fields with `data/clusters.json` |
| `src/generation/recovery_brief.py` | `cluster_profiles[n].profile.content_pillar`, `.tone_descriptors`, `.vocabulary_patterns.recurring_words/signature_phrases`, `.structural_signature`; unions `profile.avoided_terms` **brand-wide across all clusters** (not just the matched one) — this brand-wide union was a bug fix, matching the same pattern `brand.py`'s `GET /profile` uses |
| `api/routers/diagnose.py` | Falls back to `cluster_profiles[0]` for brand-voice context when a post has no assigned cluster |
| `src/generation/why_engine.py` | Full profile for benchmarking a post against brand standard |
| `src/generation/voice_timeline.py`, `strategic_insights.py`, `script_generator.py`, `blank_page_solver.py`, `caption_generator.py`, `image_prompt_generator.py` | Various `cluster_profiles[n].profile.*` fields per-cluster |
| `frontend/components/layout/Sidebar.tsx` | `brand_name`, plus the computed fields returned by `GET /api/brand/profile` (`content_pillars`, `tone_descriptors`) — not read directly from disk |

---

## 5. Clusters (`data/clusters.json`)

**Written by:** `src/embeddings/cluster.py` (`run_clustering()` — writes `n_clusters`, `cluster_map`, `clusters`); enriched in-place by `run_pipeline.py` calling `src/data/insights.py`'s `aggregate_cluster_engagement()` (adds `cluster_engagement`)
**Read by:** `api/routers/brand.py`, `api/routers/discover.py`, `api/routers/create.py`, `api/routers/agent.py`, `api/routers/diagnose.py`, `src/generation/boost_advisor.py`, `src/generation/jarvis_agent.py`, `src/generation/resonance_simulator.py`
**Gitignored:** No (demo version committed as `data/demo_clusters.json`)

> **Schema correction:** this file was previously documented as a dict keyed directly by cluster-id string, each holding `cluster_id`, `post_count`, and a `posts` array with `caption_clean`/`hook`/`hashtags` fields. The current file has a different top-level shape (`n_clusters` / `cluster_map` / `clusters` / `cluster_engagement`), and the per-post fields inside `clusters` are `marketing_hook` and a structured `engagement` object, not `caption_clean`/`hook`/`hashtags`.

### Schema (verified against the current file on disk)

```json
{
  "n_clusters": 5,
  "cluster_map": {
    "Da1zjneDIo4": 3,
    "Da69N7LsmNN": 2
  },
  "clusters": {
    "0": [
      {
        "shortcode"      : "DT4UDyNivIA",
        "timestamp_utc"  : "2026-01-24T04:36:20+0000",
        "marketing_hook" : "We all know \"tomorrow\" never comes 🤍",
        "engagement": {
          "reach"    : 1571,
          "likes"    : 26,
          "comments" : 3,
          "shares"   : 4,
          "views"    : 2102,
          "saves"    : 2
        }
      }
    ]
  },
  "cluster_engagement": {
    "0": {
      "cluster_name"        : "Golden Delights",
      "post_count"          : 2,
      "avg_views"           : 9061,
      "avg_reach"           : 6163,
      "avg_likes"           : 42,
      "avg_comments"        : 3,
      "avg_saves"           : 2,
      "engagement_rate"     : 0.9,
      "best_post_shortcode" : "DTreC26jJwp",
      "best_post_hook"      : "That golden turn never gets old 🍩✨"
    }
  }
}
```

### Top-level field reference

| Field | Type | Notes |
|-------|------|-------|
| `n_clusters` | int | K-Means `k` used for this run |
| `cluster_map` | object | Flat `{shortcode: cluster_id}` lookup for every post, including the uncategorized bucket |
| `clusters` | object | Keyed by cluster-id string (`"0"`–`"4"`, plus an uncategorized-bucket id from `src/data/pillars.py`'s `UNCATEGORIZED_ID`); each value is an **array** of post objects (see below) |
| `cluster_engagement` | object | Keyed by cluster-id string; per-cluster engagement rollup. **Only present after `run_pipeline.py` has run** — a bare `run_clustering()` call produces a file without this key, and several API routes (`discover.py`, `create.py`, `agent.py`) fall back to a hard-coded `_DEMO_ENGAGEMENT` constant when it's missing |

### `clusters["<id>"][n]` (per-post) field reference

| Field | Type | Notes |
|-------|------|-------|
| `shortcode` | string | Links back to `scraped_dataset/ig_text_{shortcode}.json` and `data/diagnoses/{shortcode}.json` |
| `timestamp_utc` | string | ISO 8601, used for monthly bucketing |
| `marketing_hook` | string | The post's cleaned lead-in copy (was called `hook` in the old cleaned-record schema; renamed at this stage) |
| `engagement.reach` / `.likes` / `.comments` / `.shares` / `.views` / `.saves` | int | Per-post metrics; a post with no metrics (thin/metrics-only pipeline input) may have an empty or partial `engagement` object |

### `cluster_engagement["<id>"]` field reference

| Field | Type | Notes |
|-------|------|-------|
| `cluster_name` | string | Pillar label, pulled from `brand_profile.json`'s `cluster_profiles[n].profile.content_pillar` at computation time |
| `post_count` | int | Number of posts in this cluster that carry real metrics (may be less than the cluster's total post count) |
| `avg_views` / `avg_reach` / `avg_likes` / `avg_comments` / `avg_saves` | int | Rounded per-post averages across metric-bearing posts |
| `engagement_rate` | float | `(sum of interaction metrics / total reach) * 100`, rounded to 1 decimal |
| `best_post_shortcode` | string | Highest-reach (tie-broken by saves) post in the cluster |
| `best_post_hook` | string | That post's `marketing_hook`, truncated to 120 chars |

### How `GET /api/brand/clusters` enriches this

`api/routers/brand.py`'s `get_clusters()` reads `clusters.json["clusters"]`, skips the uncategorized bucket, and for each remaining cluster ID merges in `brand_profile.json`'s matching `cluster_profiles[n].profile` fields (`pillar` via `pillar_label()`, `tone_descriptors`, `signature_phrases`, `recurring_words`, `avoided_terms`) plus `sample_captions` — the first 3 non-empty `marketing_hook` strings from that cluster's posts.

---

## 6. Instagram Connection (`data/ig_connection.json`)

**Written by:** `src/scrapers/instagram_api.py` — `save_connection()`, called from `exchange_code()` (initial OAuth) and updated in-place after each sync (`conn["last_sync_utc"] = time.time()`)
**Read by:** `api/routers/connect.py`, `src/scrapers/instagram_api.py`'s `load_connection()` (used wherever a live sync needs the token)
**Gitignored:** Yes — contains a live access token; never commit this file

### Schema (verified against the current file on disk)

```json
{
  "access_token"        : "IGAAOmrVhvDSZABZ...",
  "ig_user_id"          : "37519158314364227",
  "username"            : "hot_cakesbakes",
  "token_expires_at"    : 1790626665.5592663,
  "last_sync_utc"       : 1785452575.8018541,
  "granted_permissions" : [
    "instagram_business_basic",
    "instagram_business_manage_insights",
    "instagram_business_manage_comments"
  ]
}
```

### Field notes

| Field | Type | Notes |
|-------|------|-------|
| `access_token` | string | Long-lived (60-day) Instagram Graph API token, from `exchange_code()`'s token exchange |
| `ig_user_id` | string | Numeric IG user ID, from the initial short-lived token response |
| `username` | string | Fetched via `_fetch_username(token)` right after the token exchange |
| `token_expires_at` | float | Unix timestamp; `time.time() + expires_in` from Meta's response |
| `last_sync_utc` | float or null | Unix timestamp of the last successful media sync; `null` immediately after connecting, before the first sync. Used to fetch only newer media on incremental syncs |
| `granted_permissions` | string[] | Scopes the user actually consented to in the OAuth screen (source is `short.get("permissions", "")` from Meta's token-exchange response — observed as an array in the current file; treat as approximate/version-dependent on Meta's API) |

There is no `connected` boolean field on disk — connection state is inferred from **file existence**: `load_connection()` returns `None` if `data/ig_connection.json` doesn't exist, and `disconnect()` deletes the file entirely rather than setting a flag.

---

## 7. Content Workbench (`data/workbench.db`)

**Written by / Read by:** `api/routers/workbench.py` (SQLite, created on first request via `_get_conn()`)
**Gitignored:** Yes (local runtime store)

Hybrid schema: typed columns only for fields actually queried/filtered on; everything else lives in a JSON blob in `content`.

### Table: `workbench_assets`

```sql
CREATE TABLE IF NOT EXISTS workbench_assets (
    id           TEXT PRIMARY KEY,
    asset_type   TEXT NOT NULL,
    cluster_label TEXT,
    cluster_id   INTEGER,
    content      TEXT NOT NULL,
    pinned       INTEGER NOT NULL DEFAULT 0,
    source_tab   TEXT,
    actual_outcome       TEXT,
    recovery_brief_generated INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Column notes

| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (UUID4) | Primary key, generated on insert |
| `asset_type` | TEXT | Caller-supplied label for what kind of generated asset this is (e.g. caption, script, image prompt) — not an enum in the DB |
| `cluster_label` | TEXT, nullable | Human-readable pillar name at time of save |
| `cluster_id` | INTEGER, nullable | Cluster ID at time of save |
| `content` | TEXT | JSON-serialized asset payload; API layer (`_row_to_dict`) parses it back to an object on read, falls back to raw string if not valid JSON |
| `pinned` | INTEGER (bool as 0/1) | Toggled via `PATCH /api/workbench/assets/{id}` |
| `source_tab` | TEXT, nullable | Which UI tab/flow created this asset; `"recovery_agent"` is a special value that prevents a recovery brief from recursively triggering its own recovery |
| `actual_outcome` | TEXT, nullable | Free-text outcome tag set after the fact, e.g. `"underperformed"` / `"failed"` — these two values trigger the Autonomous Recovery Agent |
| `recovery_brief_generated` | INTEGER (bool as 0/1) | Set to `1` once a recovery brief has been auto-generated for this asset, so it only fires once |
| `created_at` | TEXT | SQLite `datetime('now')` default |

### Consumers

| Consumer | Behavior |
|----------|----------|
| `POST /api/workbench/assets` | Insert a new row |
| `GET /api/workbench/assets` | List all, optional `?pinned=true|false` filter |
| `PATCH /api/workbench/assets/{id}` | Update `pinned` / `actual_outcome` / `recovery_brief_generated`; when `actual_outcome` is set to `underperformed`/`failed` for the first time on a non-recovery-agent row, calls `trigger_recovery()` in `api/routers/recovery.py`, which chains into `src/generation/recovery_brief.py` |
| `DELETE /api/workbench/assets/{id}` | Remove a row |

---

## 8. Diagnoses Cache (`data/diagnoses/`)

**Written by / Read by:** `api/routers/diagnose.py`
**Gitignored:** Yes — regenerable per-post cache

### Filename pattern

```
data/diagnoses/{shortcode}.json
```

Disk cache for the "My posts" instant-diagnosis feature (the Why Engine). Exists so a Granite call (~10s) only ever runs once per post; every later page view of that post is instant. Deliberately kept separate from `workbench.db` (whose `PATCH` triggers recovery jobs) and from `lru_cache` alone (which evaporates on `uvicorn --reload`).

### Schema (verified against an actual cached file)

```json
{
  "verdict"            : "failed",
  "diagnosis"          : "The post received zero engagement...",
  "what_worked"        : "N/A",
  "what_failed"        : "The caption is too brief...",
  "brand_voice_gap"    : "The caption does not align with the brand's established voice patterns...",
  "change_next_time"   : "Include more descriptive language...",
  "verdict_label"      : "✗  Failed",
  "shortcode"          : "DBfnyNJSTMR",
  "post_type"          : "Carousel",
  "generated_at"       : "2026-07-28T04:32:27.343214+00:00",
  "metrics_at_generation": {
    "reach": 0, "views": 0, "likes": 0, "comments": 0, "saves": 0, "shares": 0
  }
}
```

### Field notes

| Field | Type | Notes |
|-------|------|-------|
| `verdict` | string | e.g. `"failed"` — raw Why Engine verdict, source of `verdict_label` |
| `diagnosis`, `what_worked`, `what_failed`, `brand_voice_gap`, `change_next_time` | string | Why Engine's structured output fields (approximate set — exact prompt/field list lives in `src/generation/why_engine.py`, not re-verified in this pass) |
| `verdict_label` | string | Display-formatted verdict with icon, e.g. `"✗  Failed"` |
| `shortcode`, `post_type` | string | Echoed from the request for convenience |
| `generated_at` | string | ISO 8601 UTC timestamp of when this diagnosis was generated |
| `metrics_at_generation` | object | Snapshot of `reach`/`views`/`likes`/`comments`/`saves`/`shares` at generation time — lets the UI detect "metrics have moved since this was generated" |

### Invalidation rule

There is no automatic expiry. `GET /api/diagnose/posts/{shortcode}` returns the cached file if it exists and `force` is not set. Passing `?force=true` re-runs the Why Engine and **overwrites** the cache file — intended for use after a post's metrics have changed materially. A response is never cached if Granite's JSON was unparseable (`what_failed == "Could not parse structured response."` sentinel) or if `diagnosis` is empty, so a bad Granite call can be retried instead of getting stuck.

---

## 9. Agent Memory (ChromaDB) (`data/chroma/`)

**Written by / Read by:** `src/memory/store.py`'s `AgentMemoryStore` class (persisted via `chromadb.PersistentClient(path="data/chroma")`)
**Gitignored:** Yes — local vector DB, regenerable
**Collection prefix:** `stylesync` (so the three physical Chroma collections are `stylesync_semantic`, `stylesync_episodic`, `stylesync_procedural`)

Three collections, matching a subset of the MIRIX memory taxonomy. Deliberately never merged into one overwriting summary — mixing semantic (brand-invariant) and episodic (campaign-specific) data would let campaign-specific outcomes overwrite stable brand-voice rules.

### `semantic` collection

Brand-invariant voice rules, seeded from `brand_profile.json` via `upsert_brand_profile()`.

| Field (in `metadata`) | Type | Notes |
|------|------|-------|
| `memory_type` | string | Always `"semantic"` |
| `brand_id` | string | Defaults to `"default_brand"` — single-tenant today |
| `source` | string | `"brand_profile"` |
| `tone` | string | Stringified `profile.get("tone")` |
| `audience` | string | Stringified `profile.get("audience")` |
| `updated_from` | string | Defaults to `"brand_profile.json"` |

Document body is a multi-line text block built by `_brand_profile_to_text()` (brand voice, tone, audience, values, preferred/avoid vocabulary, style rules, CTA style, emoji policy — as free text, not structured JSON).

### `episodic` collection

Campaign/post outcomes **with signal metrics**, written via `upsert_episode()` — the schema was recently expanded so downstream agents can reason about *why* a post won or lost, not just that it did.

| Field (in `metadata`) | Type | Notes |
|------|------|-------|
| `memory_type` | string | Always `"episodic"` |
| `brand_id`, `cluster_id`, `outcome`, `post_id`, `post_type` | string | Basic identifiers; `cluster_id` and `post_id` stringified |
| `hook_pattern`, `primary_signal` | string | e.g. what kind of hook was used, and what metric drove the outcome |
| `watch_time_secs` | float, nullable | Resolved from `watch_time_secs` or `avg_watch_time_secs`, whichever is passed |
| `save_rate` | float, nullable | |
| `share_count` | int, nullable | Resolved from `share_count` or `shares` |
| `saves`, `views`, `reach`, `likes`, `comments` | int, nullable | Raw counts |
| `verdict_label` | string | e.g. `"✗  Failed"` — mirrors the diagnoses-cache field |
| `created_at` | string | |
| `source` | string | `"analytics_feedback_loop"` |

Document body is built by `_episode_to_text()`: caption, cluster, outcome, post type, hook pattern, primary signal, avg watch time, save rate, share count, and an optional `why_summary`.

### `procedural` collection

Platform formatting rules — hard-coded seed data, platform-invariant, written via `upsert_procedural_rule()`. Auto-seeded once (`_seed_procedural_rules()`) with 5 Instagram-specific rules (hook-first-line, scannability, single-CTA, save/share bias, voice consistency) the first time the store is created with an empty `procedural` collection.

| Field (in `metadata`) | Type | Notes |
|------|------|-------|
| `memory_type` | string | Always `"procedural"` |
| `platform` | string | Defaults to `"instagram"` |
| `rule_name` | string | Slugified rule identifier |
| `source` | string | `"seed"` for hard-coded rules |

### Consumers

`build_copywriting_context()` is the main read entry point — queries all three collections independently for a given query string and returns `{semantic_rules, performance_context, procedural_rules}` without merging them. `status()` returns per-collection counts, surfaced by `api/routers/orchestrate.py`.

---

## 10. Demo Snapshots

| File | Contents | When used |
|------|----------|-----------|
| `data/demo_brand_profile.json` | Full @hot_cakesbakes brand profile (same schema as section 4) | `POST /api/onboard/reset-demo` copies this to `brand_profile.json` |
| `data/demo_clusters.json` | Full @hot_cakesbakes cluster data (same schema as section 5) | `POST /api/onboard/reset-demo` copies this to `clusters.json` |

These files are committed to the repository and serve as the always-available fallback for demos. They should not be modified manually — if the pipeline produces an improved @hot_cakesbakes profile, update them:

```bash
cp data/brand_profile.json data/demo_brand_profile.json
cp data/clusters.json data/demo_clusters.json
git add data/demo_brand_profile.json data/demo_clusters.json
git commit -m "chore: refresh demo snapshots from latest pipeline run"
```

Note: as of this writing, `data/demo_brand_profile.json` does not have a `timezone` key (it predates that field being added) — a discrepancy worth fixing next time these snapshots are refreshed.

---

## 11. Field Reference Index

Quick lookup for any field name you encounter across the codebase.

| Field | File(s) | Description |
|-------|---------|-------------|
| `access_token` | ig_connection | Long-lived Instagram Graph API token |
| `actual_outcome` | workbench.db | Outcome tag (`underperformed`/`failed` trigger auto-recovery) |
| `asset_type` | workbench.db | Caller-supplied asset kind label |
| `author` | scraped, cleaned | Instagram username without `@` |
| `avoided_terms` | brand_profile (`cluster_profiles[n].profile.avoided_terms`) | Words that undercut the brand voice, per cluster; unioned brand-wide by `brand.py` and `recovery_brief.py` |
| `best_post_shortcode` / `best_post_hook` | clusters (`cluster_engagement`) | Highest-performing post per cluster |
| `brand_bio` | brand_profile | Free-text brand description passed into every Granite prompt |
| `brand_name` | brand_profile | Human-readable brand name |
| `caption_clean` | cleaned | Normalized full caption text |
| `caption_raw` | scraped | Raw caption as posted on Instagram |
| `cluster_engagement` | clusters | Per-cluster engagement rollup, added by `run_pipeline.py` post-Granite; absent until then |
| `cluster_id` | clusters (`cluster_map` values, and per-cluster keys), brand_profile (`cluster_profiles[n].cluster_id`), workbench.db | Integer cluster assignment |
| `cluster_map` | clusters | Flat `{shortcode: cluster_id}` lookup |
| `cluster_profiles` | brand_profile | **List** of `{cluster_id, post_count, profile}` objects — not a dict |
| `content` | workbench.db | JSON-serialized generated asset payload |
| `content_pillar` | brand_profile (`cluster_profiles[n].profile.content_pillar`) | Per-cluster pillar name; deduplicated across clusters |
| `engagement` | clusters (`clusters["<id>"][n].engagement`) | Per-post `{reach, likes, comments, shares, views, saves}` |
| `engagement_rate` | clusters (`cluster_engagement`) | `(interactions / reach) * 100`, rounded to 1 decimal |
| `generated_at` | diagnoses cache | ISO 8601 timestamp of Why Engine run |
| `granted_permissions` | ig_connection | OAuth scopes actually granted |
| `hashtags` | scraped, cleaned | Extracted `#tag` strings (without `#`) |
| `hook` | cleaned | First sentence of `caption_clean` (renamed to `marketing_hook` once it reaches clusters.json) |
| `ig_handle` | brand_profile | Account handle with leading `@` |
| `ig_user_id` | ig_connection | Numeric Instagram account ID |
| `inference_backend` | brand_profile | Always `"ollama-local"` currently |
| `last_sync_utc` | ig_connection | Unix timestamp of last media sync; `null` before first sync |
| `marketing_hook` | clusters | Cleaned lead-in copy per post (clusters.json's name for `hook`) |
| `mentions` | scraped | Extracted `@mention` strings (without `@`) |
| `metrics_at_generation` | diagnoses cache | Metric snapshot at diagnosis time, for staleness detection |
| `model_used` | brand_profile | e.g. `"granite3.1-dense:8b"` |
| `n_clusters` | brand_profile, clusters | Count of clusters; can differ between the two files (brand_profile excludes the uncategorized bucket) |
| `owner_id` | scraped | Numeric Instagram account ID as string |
| `pillar` | clusters (merged via `brand.py`) | Human-readable cluster name, not stored on disk under this key |
| `pinned` | workbench.db | Bool (stored as 0/1) |
| `post_count` | brand_profile (`cluster_profiles[n].post_count`), clusters (`cluster_engagement[n].post_count`) | Number of posts in a cluster |
| `recovery_brief_generated` | workbench.db | Bool (stored as 0/1); guards against recursive recovery |
| `recurring_words` | brand_profile (`cluster_profiles[n].profile.vocabulary_patterns.recurring_words`) | High-frequency words/phrases, per cluster |
| `representative_post` | brand_profile (`cluster_profiles[n].profile.representative_post`) | Verbatim most-on-brand post for the cluster |
| `sample_captions` | clusters (merged via `brand.py`) | First 3 `marketing_hook` strings (API-only, not on disk) |
| `shortcode` | scraped, cleaned, clusters, diagnoses cache | Instagram post ID (after `/p/` in URL) |
| `signature_phrases` | brand_profile (`cluster_profiles[n].profile.vocabulary_patterns.signature_phrases`) | Verbatim brand phrases, per cluster |
| `source_tab` | workbench.db | Which UI flow created the asset; `"recovery_agent"` is a sentinel value |
| `source_url` | scraped, cleaned | Canonical `instagram.com/p/...` URL |
| `structural_signature` | brand_profile (`cluster_profiles[n].profile.structural_signature`) | One-sentence post-structure description per cluster |
| `timestamp_utc` | scraped, cleaned, clusters | ISO 8601 UTC string |
| `timezone` | brand_profile | IANA timezone name, set once at onboarding and preserved across re-syncs |
| `token_expires_at` | ig_connection | Unix timestamp |
| `tone_descriptors` | brand_profile (`cluster_profiles[n].profile.tone_descriptors`) | Adjectives describing voice/tone, per cluster |
| `username` | ig_connection | Connected Instagram username |
| `vocabulary_patterns` | brand_profile (`cluster_profiles[n].profile.vocabulary_patterns`) | Nested object: `recurring_words`, `signature_phrases`, `emoji_style` |
| `word_count` | cleaned | Word count of `caption_clean` |
