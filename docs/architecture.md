# StyleSync — Architecture

A technical reference for how the system is structured: module responsibilities, request flows, caching design, and the nine Granite invocations.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Backend Layer](#2-backend-layer)
3. [AI Layer — Nine Granite Invocations](#3-ai-layer--nine-granite-invocations)
4. [Data Pipeline](#4-data-pipeline)
5. [Frontend Layer](#5-frontend-layer)
6. [Caching Architecture](#6-caching-architecture)
7. [Onboarding Pipeline](#7-onboarding-pipeline)
8. [Request Flows](#8-request-flows)

---

## 1. System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Browser — Next.js 16 (App Router, React 19, Tailwind 4)        │
│  /onboard   /create   /analyze   /discover                       │
│  lib/api.ts — typed fetch wrapper                                │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP / JSON
┌────────────────────────────▼─────────────────────────────────────┐
│  FastAPI 0.111 — api/main.py                                     │
│  5 routers: onboard / brand / create / analyze / discover        │
│  api/dependencies.py — @lru_cache generator singletons           │
└────────────┬─────────────────────────┬───────────────────────────┘
             │ reads                   │ invokes
┌────────────▼────────────┐  ┌─────────▼────────────────────────────┐
│  data/                  │  │  src/generation/*.py                 │
│  brand_profile.json     │  │  9 Granite invocation modules        │
│  clusters.json          │  │  (LangChain → Ollama HTTP)           │
└─────────────────────────┘  └─────────────┬────────────────────────┘
                                           │ localhost:11434
                             ┌─────────────▼────────────────────────┐
                             │  Ollama — granite3.1-dense:8b        │
                             │  Apple Silicon / Neural Engine       │
                             └──────────────────────────────────────┘
```

All inference is local. No data leaves the machine during normal operation.

---

## 2. Backend Layer

### `api/main.py`

Initializes the FastAPI application. Sets up CORS (allows `localhost:3000` and `127.0.0.1:3000`). Mounts five routers at `/api/*` prefixes. Provides a `/api/health` endpoint.

Router mounting order matters for OpenAPI docs display; `onboard` is mounted first so it appears at the top of `/docs`.

### `api/dependencies.py`

Holds `@lru_cache`-decorated factory functions for all nine generator singletons:

```python
@lru_cache(maxsize=1)
def get_caption_generator() -> CaptionGenerator:
    return CaptionGenerator()
```

Each generator loads `data/brand_profile.json` at construction time. The `maxsize=1` cache means the instance is built once and reused across all requests. After onboarding completes, `_clear_caches()` in `onboard.py` calls `.cache_clear()` on all eight factory functions so the next request rebuilds with the new profile.

### Router responsibilities

| Router | Prefix | Responsibility |
|--------|--------|---------------|
| `onboard.py` | `/api/onboard` | Self-serve account analysis; background task management; profile gate check |
| `brand.py` | `/api/brand` | Read-only brand profile and cluster data; merges disk JSON into typed API response |
| `create.py` | `/api/create` | All content generation: moment analysis → directions → captions → image prompt → script |
| `analyze.py` | `/api/analyze` | Why Engine: takes post metrics + caption → performance diagnosis |
| `discover.py` | `/api/discover` | Voice Timeline and Strategic Insights; double-cached (`@lru_cache` on both compute functions) |

---

## 3. AI Layer — Nine Granite Invocations

All nine modules live in `src/generation/` and follow the same pattern:
1. Load `data/brand_profile.json` at `__init__`
2. Build a prompt string with brand context embedded
3. Call Ollama via LangChain's `ChatOllama` → parse the response as JSON
4. Return a typed Python dict

### Invocation map

| # | Class | File | Called from | Input → Output |
|---|-------|------|-------------|----------------|
| 1 | `BrandProfileExtractor` | `profile_extractor.py` | `run_pipeline.py`, `onboard.py` | Corpus of captions → `brand_profile.json` |
| 2 | `CaptionGenerator` | `caption_generator.py` | `create.py` `/captions` | Brief (product, occasion, feel, cluster) → 3 caption variants |
| 3 | `ImagePromptGenerator` | `image_prompt_generator.py` | `create.py` `/image-prompt` | Caption + product → Midjourney/DALL-E prompt |
| 4 | `WhyEngine` | `why_engine.py` | `analyze.py` `/why-engine` | Post metrics + caption + cluster → 6-section diagnosis |
| 5 | `VoiceTimeline` | `voice_timeline.py` | `discover.py` `/voice-timeline` | Monthly cluster distribution → narrative + key shift |
| 6 | `MomentAnalyzer` | `blank_page_solver.py` | `create.py` `/analyze-moment` | Free-text moment description → emotional core + cluster pick |
| 7 | `DirectionGenerator` | `blank_page_solver.py` | `create.py` `/directions` | Moment analysis → 3 creative direction cards |
| 8 | `StrategicInsights` | `strategic_insights.py` | `discover.py` `/strategic-insights` | Richness scores per cluster → strategy brief + experiment |
| 9 | `ScriptGenerator` | `script_generator.py` | `create.py` `/script` | Reference post + metrics + format → full Reel/Carousel/Static script |

### Pattern: why LangChain + Ollama?

LangChain's `ChatOllama` is used for its `format="json"` mode, which forces Granite to emit valid JSON. All prompts include an explicit JSON schema in the system message. The generation modules parse the response with `json.loads()` and return structured Python dicts — no string post-processing.

### Caption quality note — Script Studio

`create.py`'s `/script` endpoint runs two Granite calls sequentially:
1. `ScriptGenerator.generate()` produces the script structure (hook, slides, shots, etc.)
2. `CaptionGenerator.generate()` overwrites `script["caption"]` with a higher-quality caption

This ensures caption quality parity between Caption Brief and Script Studio.

---

## 4. Data Pipeline

Three sequential stages, each producing a file set consumed by the next.

### Stage 1 — `src/data/pipeline.py`

Input: `scraped_dataset/ig_text_*.json`  
Output: `data/cleaned/*.json`

- Reads every `ig_text_*.json` file
- Runs caption text through `ftfy` (fixes Unicode garbling from Instagram exports)
- Strips excessive whitespace and emoji clusters
- Splits caption into `hook` (first sentence) and full `caption_clean`
- Filters posts with `word_count < 3`
- Writes one `data/cleaned/{shortcode}.json` per surviving post

### Stage 2 — `src/embeddings/cluster.py`

Input: `data/cleaned/*.json`  
Output: `data/clusters.json`

- Loads all cleaned captions into a list
- Embeds them using `sentence-transformers` `all-MiniLM-L6-v2` (runs locally, ~80 MB model)
- Runs scikit-learn `KMeans(n_clusters=5)` on the embeddings
- Assigns each post to a cluster
- Writes `data/clusters.json` with posts grouped by cluster ID

### Stage 3 — `src/embeddings/profile_extractor.py`

Input: `data/clusters.json`, `data/cleaned/*.json`  
Output: `data/brand_profile.json`

- Constructs a corpus summary per cluster (top phrases, sample captions)
- Calls Granite (Invocation #1) with the full corpus to extract brand-level attributes
- Calls Granite once per cluster (5 calls total) to extract cluster-specific voice profiles
- Writes the complete `data/brand_profile.json`

This is the longest stage (~8-12 minutes): 6 Granite calls, each ~90 seconds.

---

## 5. Frontend Layer

### App Router structure

```
frontend/app/
├── layout.tsx          Root layout: NavTabs + Sidebar + Providers wrapper
├── page.tsx            Home: checks has-profile → routes to /create or /onboard
├── onboard/page.tsx    Self-serve onboarding (overlay, covers layout)
├── create/page.tsx     Content creation hub
├── analyze/page.tsx    Why Engine post-mortem
└── discover/page.tsx   Voice Timeline + Strategic Insights
```

### Root layout behavior

`layout.tsx` wraps every page except `/onboard`. The onboard page uses `position: fixed; inset: 0; z-index: 50` to render as a full-screen overlay on top of the layout — this means the Sidebar and NavTabs exist in the DOM but are hidden behind the overlay.

### State management

React Query (`@tanstack/query`) handles all server state. Each API call has a dedicated query key. Queries run on mount; `staleTime` defaults to 5 minutes so switching tabs doesn't re-fetch.

There is no global state store (no Redux, no Zustand). Component-local `useState` handles form inputs and UI transitions.

### API client — `lib/api.ts`

All fetch calls go through `apiFetch<T>(path, init?)` which:
- Prepends `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`)
- Sets `Content-Type: application/json` for JSON requests
- Throws on non-2xx responses with the status code + body text

`uploadExport()` bypasses `apiFetch` and uses raw `fetch` to send `FormData` (multipart, no JSON header).

---

## 6. Caching Architecture

### Generator singleton cache (`api/dependencies.py`)

```
Request → get_caption_generator() → @lru_cache(maxsize=1)
                                        │
                               ┌────── hit ──────┐
                               │                 │
                    return existing          build new CaptionGenerator
                    instance                (loads brand_profile.json)
```

All 8 generator factories follow this pattern. The cache is process-scoped: restarting uvicorn clears it automatically.

**Invalidation trigger:** `onboard.py:_clear_caches()` calls `.cache_clear()` on all 8 factories immediately after the pipeline writes new JSON files. The next request to any generation endpoint rebuilds its singleton with the new profile.

### Discover compute cache (`api/routers/discover.py`)

```python
@lru_cache(maxsize=1)
def _compute_voice_timeline() -> VoiceTimelineResult:
    ...  # expensive: reads all clusters, calls Granite

@lru_cache(maxsize=1)
def _compute_strategic_insights() -> StrategicInsightsResult:
    ...  # expensive: calls Granite
```

First load: 60-120 seconds (Granite calls). Every subsequent load: instant (cache hit).

`_clear_caches()` calls `.cache_clear()` on both functions after onboarding.

### No request-level caching

There is deliberately no HTTP-level caching (`Cache-Control`, ETags) on the API responses. All caching is in-process `@lru_cache`. This keeps the cache invalidation logic simple: one function call clears everything.

---

## 7. Onboarding Pipeline

The onboarding flow runs the full 3-stage pipeline in a FastAPI `BackgroundTask` thread, reporting progress to an in-memory `_jobs` dict polled by the frontend.

```
POST /api/onboard/start
    │
    ├─ validate handle
    ├─ create job_id → _jobs[job_id] = {status: "queued", progress: 0}
    └─ background_tasks.add_task(_run_handle_pipeline, job_id, handle, brand_name)
        │
        │  (runs in thread pool, non-blocking)
        │
        ├─ 5%  Instaloader: scrape public profile → scraped_dataset/
        ├─ 10% Instaloader: fetch all posts (up to 200)
        ├─ 30% pipeline.py: clean + normalize captions → data/cleaned/
        ├─ 50% cluster.py: embed + K-Means → data/clusters.json
        ├─ 65% profile_extractor.py: Granite brand voice → data/brand_profile.json
        ├─ _clear_caches()
        └─ 100% _jobs[job_id] = {status: "done"}

GET /api/onboard/status/{job_id}
    └─ returns _jobs[job_id]   ← polled every 3s by frontend
```

**Error handling:** Any exception in `_run_handle_pipeline` is caught, the job status is set to `"error"`, and the error message is stored in `_jobs[job_id]["message"]`. The frontend shows the error message and offers the data export fallback.

**Single active profile:** The pipeline always writes to `data/brand_profile.json` and `data/clusters.json`, overwriting any previous data. There is no multi-user isolation.

---

## 8. Request Flows

### Caption generation (Create tab)

```
User fills Caption Brief → clicks "Generate Captions"
    │
    ▼
POST /api/create/captions
    {product, occasion, desired_feel, cluster_id, previous_captions?}
    │
    ▼
create.py → get_caption_generator()
    │           └─ @lru_cache → CaptionGenerator (brand_profile loaded at init)
    │
    ▼
CaptionGenerator.generate(product, occasion, desired_feel, cluster_id)
    │
    ├─ fetch cluster profile from self._cluster_profiles
    ├─ build prompt: brand voice + cluster tone + brief + "avoid" list
    ├─ append previous_captions as negative examples (if provided)
    │
    ▼
Granite 3.1 via Ollama (Invocation #2, ~10-20s)
    │
    ▼
parse JSON → [{caption, reasoning}, {caption, reasoning}, {caption, reasoning}]
    │
    ▼
return 3 Caption objects to frontend
```

### Discover tab — first load

```
User opens /discover
    │
    ▼
frontend mounts VoiceTimelineChart + StrategicInsightsChart
    │
    ├─ useQuery("voice-timeline") → GET /api/discover/voice-timeline
    │       │
    │       ▼
    │   discover.py → _compute_voice_timeline()  [first call: ~60s]
    │       ├─ read data/clusters.json
    │       ├─ bucket posts by month
    │       ├─ compute monthly pillar percentages
    │       ├─ call Granite (Invocation #5) to write narrative
    │       └─ return VoiceTimelineResult  ← cached by @lru_cache
    │
    └─ useQuery("strategic-insights") → GET /api/discover/strategic-insights
            │
            ▼
        discover.py → _compute_strategic_insights()  [first call: ~60s]
            ├─ read brand_profile.json + clusters.json
            ├─ compute richness scores (phrase diversity × post count)
            ├─ call Granite (Invocation #8) to write strategy brief
            └─ return StrategicInsightsResult  ← cached by @lru_cache
```

Both queries run concurrently. On second visit, both return from cache in <10ms.

### Onboarding — error and fallback flow

```
User enters @someprivateaccount → clicks "Analyze My Brand"
    │
    ▼
POST /api/onboard/start → job_id returned
    │
    ▼
_run_handle_pipeline:
    scrape_profile("someprivateaccount")
        └─ raises RuntimeError("@someprivateaccount is a private account...")
            │
            ▼
        _update_job(job_id, current_pct, str(exc), status="error")
    │
    ▼
Frontend polls GET /api/onboard/status/{job_id}
    └─ {status: "error", message: "@someprivateaccount is a private account..."}
        │
        ▼
    Progress screen switches to error state
        └─ Shows error message
        └─ "Use data export instead" button
            └─ onClick: setScreen("choice"); setShowUpload(true)
                └─ Returns to choice screen with ZIP uploader pre-expanded
```
