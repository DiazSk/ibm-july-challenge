# StyleSync — Architecture

A technical reference for how the system is structured: module responsibilities, request flows, caching design, and the 22 Granite invocations.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Backend Layer](#2-backend-layer)
3. [AI Layer — 22 Granite Invocations](#3-ai-layer--22-granite-invocations)
4. [Multi-Agent Layer](#4-multi-agent-layer)
5. [Data Pipeline & Instagram Ingestion](#5-data-pipeline--instagram-ingestion)
6. [Frontend Layer](#6-frontend-layer)
7. [Caching Architecture](#7-caching-architecture)
8. [Request Flows](#8-request-flows)

---

## 1. System Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│  Browser — Next.js 16 (App Router, React 19, Tailwind 4)                 │
│  8 studio tabs: /app/today /dashboard /brand /create /analyze /discover  │
│                 /agents /triage  — plus /app/onboard (full-screen)       │
│  Cross-cutting: JarvisWidget (floating voice/text) · Workbench drawer    │
│  lib/api.ts — typed fetch wrapper                                        │
└────────────────────────────┬──────────────────────────────────────────────┘
                             │ HTTP / JSON
┌────────────────────────────▼──────────────────────────────────────────────┐
│  FastAPI 0.111+ — api/main.py                                            │
│  21 routers mounted at /api/*  (today, onboard, connect, insights,       │
│  strategy, diagnose, inbox, brand, create, analyze, discover, workbench, │
│  agent, voice, repurpose, weekly-brief, triage, orchestrate, agent-run,  │
│  recovery, playbook)                                                     │
│  api/dependencies.py — ~30 @lru_cache singleton factories                │
│  Background task: _instagram_poll_loop (polls connected IG account)      │
└────────────┬──────────────────────┬─────────────────────┬─────────────────┘
             │ reads/writes         │ invokes             │ coordinates
┌────────────▼───────────┐  ┌───────▼──────────────┐  ┌───▼───────────────────┐
│  data/                 │  │  src/generation/*.py  │  │  src/agents/*.py      │
│  brand_profile.json    │  │  22 Granite invocation│  │  7 specialized agents │
│  clusters.json         │  │  modules              │  │  + StyleSyncOrch-     │
│  workbench.db (SQLite) │  │  (LangChain → Ollama) │  │    estrator           │
│  ig_connection.json    │  └──────────┬────────────┘  │  + WeeklyAutopilot    │
│  diagnoses/*.json      │             │               │  + PlaybookAgent      │
└────────────────────────┘             │               └───┬───────────────────┘
                                       │ localhost:11434    │ 3 ChromaDB
                          ┌────────────▼─────────────┐      │ collections
                          │  Ollama — granite3.1-    │◄─────┘ (semantic /
                          │  dense:8b (local, CPU/   │        episodic /
                          │  GPU — Ollama runtime    │        procedural)
                          │  picks the backend)      │
                          └───────────────────────────┘
```

All inference is local. No content leaves the machine during normal operation; Instagram data enters via one of two paths (OAuth Graph API or Instaloader/data-export), never leaves for inference.

---

## 2. Backend Layer

### `api/main.py`

Initializes the FastAPI app (`title="StyleSync API"`, `version="2.0.0"`). Sets up CORS for `localhost:3000` / `127.0.0.1:3000`, plus an `allow_origin_regex` for VS Code Dev Tunnels (`https://*.devtunnels.ms`) since the browser preview during development is often served through a tunnel rather than localhost directly.

A `lifespan` context manager starts `_instagram_poll_loop()` as a background `asyncio` task on startup and cancels it on shutdown. The loop sleeps `IG_POLL_INTERVAL_SECS` (default 3 hours), then — if an Instagram account is connected (`load_connection()` in `src/scrapers/instagram_api.py` returns truthy) — calls `connect.py`'s `run_sync_and_refresh()` in a thread-pool executor to pull new posts and refresh the brand profile without user action. A failed poll is logged to stderr and never kills the loop.

Mounts 21 routers at `/api/*` prefixes:

| Router | Prefix |
|--------|--------|
| `today` | `/api/today` |
| `onboard` | `/api/onboard` |
| `connect` | `/api/connect` |
| `insights` | `/api/insights` |
| `strategy` | `/api/strategy` |
| `diagnose` | `/api/diagnose` |
| `inbox` | `/api/inbox` |
| `brand` | `/api/brand` |
| `create` | `/api/create` |
| `analyze` | `/api/analyze` |
| `discover` | `/api/discover` |
| `workbench` | `/api/workbench` |
| `agent` | `/api/agent` |
| `voice` | `/api/voice` |
| `repurpose` | `/api/repurpose` |
| `weekly_brief` | `/api/weekly-brief` |
| `triage` | `/api/triage` |
| `orchestrate` | `/api/orchestrate` |
| `agent_run` | `/api/agent-run` |
| `recovery` | `/api/recovery` |
| `playbook` | `/api/playbook` |

`GET /api/health` returns `{"status": "ok", "service": "StyleSync API"}`.

### `api/dependencies.py`

Holds ~30 `@lru_cache(maxsize=1)`-decorated factory functions — one per generator/agent singleton, e.g.:

```python
@lru_cache(maxsize=1)
def get_caption_generator():
    from src.generation.caption_generator import CaptionGenerator
    return CaptionGenerator()
```

Each generator loads `data/brand_profile.json` at construction. `maxsize=1` means the instance is built once per process and reused across requests. Two singletons are intentionally excluded from cache invalidation: `get_sentence_embedder()` (model weights only, never goes stale) and, functionally, `get_memory_store()` (ChromaDB collections persist across syncs by design). After onboarding/sync completes, `onboard.py`'s `_clear_caches()` calls `.cache_clear()` on the generator factories so the next request rebuilds with the new profile.

Agent-layer factories compose on top of the generator ones: `get_memory_store()` → `get_trend_agent()` / `get_orchestrator()` (both take `memory=get_memory_store()`) → `get_autopilot()` (takes `get_orchestrator()`) → `get_playbook_agent()` (reads `brand_name` off disk, takes the shared memory store).

### Router responsibilities

| Router | Prefix | Responsibility |
|--------|--------|---------------|
| `today.py` | `/api/today` | Daily briefing: instant algorithmic "today's move" + reference post (`GET /`), plus a slow/cached first-party trend read (`GET /trend`, Trend Agent). Reuses `strategy.py`'s cached diagnoses rather than re-running Why Engine. |
| `onboard.py` | `/api/onboard` | Self-serve account analysis via two paths — handle scrape (`POST /start`, Instaloader) or ZIP data-export upload (`POST /upload`) — both running the 3-stage pipeline as a background task; `GET /status/{job_id}` polling; `GET /has-profile` gate; `POST /reset-demo`. |
| `connect.py` | `/api/connect` | Instagram OAuth connect: `GET /login` (authorize URL), `GET /callback` (token exchange), `GET /status`, `POST /sync` (manual sync-now), `POST /disconnect`. Persists token + `granted_permissions` to `data/ig_connection.json`. |
| `insights.py` | `/api/insights` | Real content-analytics dashboard (`GET /overview`): KPIs, top posts, engagement-by-pillar, best-time-to-post — pure aggregation over `clusters.json`, no LLM, `lru_cache`d. |
| `strategy.py` | `/api/strategy` | Performance-first strategy view, split by cost: `/overview` (instant, pure Python scorecard/timeline/moves), `/diagnoses` (Why Engine ×2, cached), `/brief` (Granite strategic brief, cached). |
| `diagnose.py` | `/api/diagnose` | Per-post diagnosis for the whole account: `/posts` (instant, algorithm-tier badge for every synced post), `/posts/{shortcode}` (one Why Engine call, disk-cached to `data/diagnoses/{shortcode}.json` so it survives `--reload`), `/posts/{shortcode}/seed`. |
| `inbox.py` | `/api/inbox` | Real Instagram comment read/reply via the Graph API: `GET /comments`, `POST /reply` (requires the `instagram_business_manage_comments` scope). |
| `brand.py` | `/api/brand` | Read-only brand profile/cluster data (`GET /profile`, `GET /clusters`) plus the Brand Drift Watchdog (`POST /drift-check`). |
| `create.py` | `/api/create` | Generate tab: `/analyze-moment`, `/directions`, `/captions`, `/script`, `/voice-refine`, `/image-prompt`, `/resonance-check`, `/guardian-review`, `/drift-compare`. The most Granite-invocation-dense router. |
| `analyze.py` | `/api/analyze` | `/describe-image` (vision model → text description) and `/why-engine` (post-mortem diagnosis, chains into an auto Recovery Brief on a bad verdict and an auto Repurpose fan-out on a good one). |
| `discover.py` | `/api/discover` | `/voice-timeline`, `/strategic-insights`, `/boost-advisor` — each computed once and `lru_cache`d (60-120s first call, then instant). |
| `workbench.py` | `/api/workbench` | SQLite-backed save-drawer: `POST/GET/PATCH/DELETE /assets` — pin, star, and outcome-tag any generated asset from any tab. A PATCH tagging an outcome as "underperformed"/"failed" is what triggers `recovery.py`. |
| `agent.py` | `/api/agent` | JARVIS chat (`POST /chat`): two-call Granite flow (intent routing → optional tool dispatch → synthesis). `GET`/`DELETE /session/{id}` manage in-memory conversation history. |
| `voice.py` | `/api/voice` | `POST /transcribe` (faster-whisper STT), `POST /synthesize` (Kokoro TTS) — powers the JARVIS widget's voice mode. |
| `repurpose.py` | `/api/repurpose` | Closed-loop repurposing: fans one caption out to Reel/Carousel/Static/Story via `ScriptGenerator`, as a background job, landing drafts in the Workbench. Fires automatically from `analyze.py` on a "succeeded" verdict, or on demand. |
| `weekly_brief.py` | `/api/weekly-brief` | Background agent: finds the underutilized-but-rich pillar from cached Strategic Insights, researches trends, proposes scenarios (Granite #17), runs each through Blank Page Solver → Caption → Image Direction, lands drafts in the Workbench. |
| `triage.py` | `/api/triage` | `POST /run` — paste up to 20 comments/DMs, get classification + drafted replies (synchronous batch, capped for latency). |
| `orchestrate.py` | `/api/orchestrate` | Single entry point to the multi-agent system: `POST /` runs one of 5 task-type topologies via `StyleSyncOrchestrator`; `GET /memory-status` reports ChromaDB collection counts. |
| `agent_run.py` | `/api/agent-run` | Autopilot: `POST /start` kicks off `WeeklyAutopilot` in a background thread; `GET /{job_id}` polls status/trace/results; `POST /{job_id}/answer` resumes a run blocked on a clarifying question. |
| `recovery.py` | `/api/recovery` | Autonomous Recovery Agent — proactively diagnoses + regenerates a Workbench post tagged "underperformed"/"failed"; `GET /pending-notice` lets JARVIS announce it; `GET /status/{job_id}`. |
| `playbook.py` | `/api/playbook` | Self-Improving Playbook: `POST /reflect` runs the reflection agent over tagged real outcomes (background); `GET /reflect/{job_id}` polls; `GET /rules` returns the current procedural playbook the copywriter follows. |

---

## 3. AI Layer — 22 Granite Invocations

All modules live in `src/generation/` (with two in `src/agents/`) and follow the same base pattern:
1. Load `data/brand_profile.json` (and/or `data/clusters.json`) at `__init__`
2. Build a prompt with brand context embedded
3. Call Ollama via LangChain (`ChatOllama`/`OllamaLLM`), requesting JSON
4. Parse the response — layered: direct `json.loads` → missing-comma repair → truncation repair → regex field extraction, so one malformed character never discards a whole result

Numbering below is taken verbatim from the `Granite invocation #N` / `Granite Call #N` docstrings inline in each source file (confirmed by grep across `src/generation/*.py` and `src/agents/*.py`).

| # | Class / function | File | Called from |
|---|-------|------|-------------|
| 1 | `BrandProfileExtractor.extract_cluster_profile` | `src/embeddings/profile_extractor.py` | Pipeline stage 3 — one call per content cluster (plus an occasional extra call to de-duplicate colliding pillar names) |
| 2 | `CaptionGenerator` | `caption_generator.py` | `create.py` `/captions`, `/script` (caption swap), `/drift-compare` (StyleSync side) |
| 3 | `ImagePromptGenerator` | `image_prompt_generator.py` | `create.py` `/image-prompt` |
| 4 | `WhyEngine` | `why_engine.py` | `analyze.py` `/why-engine`; also `strategy.py` `/diagnoses` and `diagnose.py` `/posts/{shortcode}` |
| 5 | `VoiceTimeline` | `voice_timeline.py` | `discover.py` `/voice-timeline` |
| 6 | `MomentAnalyzer` | `blank_page_solver.py` | `create.py` `/analyze-moment` |
| 7 | `DirectionGenerator` | `blank_page_solver.py` | `create.py` `/directions` |
| 8 | `StrategicInsights` | `strategic_insights.py` | `discover.py` `/strategic-insights` |
| 9 | `ScriptGenerator` | `script_generator.py` | `create.py` `/script` |
| 10 | `RecoveryBriefGenerator` | `recovery_brief.py` | `analyze.py` `/why-engine` (chained on a bad verdict); `recovery.py`'s autonomous agent |
| 11 | `BoostAdvisor` | `boost_advisor.py` | `discover.py` `/boost-advisor` |
| 12 | `VoiceRefiner` | `voice_refiner.py` | `create.py` `/voice-refine` |
| 13 | `JarvisAgent.chat` | `jarvis_agent.py` | `agent.py` `/chat` — 2 calls per turn: intent routing, then synthesis after tool dispatch |
| 14 | `InspirationSynthesizer.synthesize` | `jarvis_agent.py` | `agent.py` `/chat` — synthesizes web-search snippets into 3 brand-adapted ideas (a JARVIS tool) |
| 15 | `ConfidenceScorer` | `confidence_scorer.py` | `analyze.py` `/why-engine`, `discover.py` `/boost-advisor` — directional confidence badge, paired with a deterministic signal gate |
| 16 | `PersonaSimulator` (×3) + `ResonanceSynthesizer` (×1) | `resonance_simulator.py` | `create.py` `/resonance-check` — 4 Granite calls per request |
| 17 | `WeeklyBriefPlanner` | `weekly_brief.py` | `weekly_brief.py` `/generate` |
| 18 | `BrandGuardian` (critique + refine) | `brand_guardian.py` | `create.py` `/guardian-review` (up to 4 calls, hard-capped at 2 rounds); shared by `CriticAgent`'s critique step inside the Orchestrator's `full_campaign` loop |
| 19 | `BrandDriftAnalyzer` | `brand_drift.py` | `brand.py` `/drift-check` (Brand Drift Watchdog) |
| 20 | `CommentTriager` | `comment_triage.py` | `triage.py` `/run` — one call per chunk of messages |
| 21 | `ErrorClassifier` | `src/agents/critic_agent.py` | Inside `CriticAgent` (Orchestrator's `full_campaign` convergence loop) — maps a flagged issue to one typed error category |
| 22 | `TrendAgent` | `src/agents/trend_agent.py` | `today.py` `/trend`; Orchestrator's `trend_briefing` topology; `WeeklyAutopilot`'s evidence-gathering phase |

**Not counted among the 22:** `BaselineCaptionGenerator` (`baseline_caption.py`) runs the same `granite3.1-dense:8b` model but with a deliberately generic, brand-blind prompt — it exists purely as the control side of the Drift Test (`/drift-compare`), so any difference in the head-to-head is attributable to brand grounding, not model quality, and it isn't part of "the shipped system's coordinated invocations."

### Why LangChain + Ollama

`ChatOllama`/`OllamaLLM` give a consistent local-inference interface; prompts request strict JSON and the layered parser above absorbs Granite 3.1's two common defects (a dropped comma between fields, and truncation at the token cap) without discarding a whole result.

---

## 4. Multi-Agent Layer

A second AI layer sits alongside the single-purpose generation modules above: seven specialized agents (`src/agents/`), each a `BaseAgent` subclass, coordinated by `StyleSyncOrchestrator` (`src/agents/orchestrator.py`).

| Agent | File | Role |
|---|---|---|
| `CopywritingAgent` | `copywriting_agent.py` | Generates and rewrites captions |
| `CriticAgent` | `critic_agent.py` | Critiques a draft (via `BrandGuardian`, #18) and classifies the issue into a typed error (`ErrorClassifier`, #21) so the orchestrator can route to the right fix |
| `BrandVoiceAgent` | `brand_voice_agent.py` | Drift detection, vocabulary enforcement |
| `AnalyticsAgent` | `analytics_agent.py` | Why Engine, strategic insights, pre-scoring |
| `CommunityAgent` | `community_agent.py` | Comment/DM triage |
| `VisualAgent` | `visual_agent.py` | Image prompt generation |
| `TrendAgent` | `trend_agent.py` | Live web-trend briefing (#22) |

### `StyleSyncOrchestrator`

Picks a coordination topology per `task_type` at runtime (`TOPOLOGY_MAP`):

| `task_type` | Topology |
|---|---|
| `single_caption` | parallel — `BrandVoiceAgent` (drift check) ∥ `CopywritingAgent` (generation) |
| `full_campaign` | hierarchical — Copy → Critic convergence loop → Visual + Analytics (parallel) |
| `post_mortem` | sequential — Analytics (Why Engine) → Community (if a triage payload is present) |
| `trend_briefing` | parallel — Trend ∥ Analytics |
| `community_triage` | flat — Community alone |

The `full_campaign` convergence loop (`produce_post()`) is goal-directed, not count-bounded: it exits on `goal_met` (critic approves AND confidence ≥ the creator's gate), `plateau` (confidence Δ ≤ 2 across 3 consecutive cycles → flagged for human review), or `factual_gap` (hard stop, human review required), with `max_cycles` (8) as a safety ceiling. The `convergence_reason` is returned to the caller rather than hidden. `POST /api/orchestrate` exposes this directly; `agent_run.py`'s Autopilot uses the same `produce_post()` method internally for each planned post.

### `WeeklyAutopilot` (`src/agents/autopilot.py`)

Not a `BaseAgent` — a standalone plan-then-act planner that composes `StyleSyncOrchestrator` as its toolbelt. Three phases, each streamed via a `trace` callback:

- **THINK** — gathers evidence with orchestrator tools (`assess_gaps()`, `get_trends()`, `recall_performance()`), then has Granite reason over that evidence to produce a weekly plan (which pillars, which angles, why). If it hits a genuine strategic fork, it asks the user one question via an `ask_user` callback and blocks (real pause/resume via `threading.Event`, not a polling flag) until `POST /api/agent-run/{job_id}/answer` supplies an answer.
- **ACT** — autonomously produces each planned post via `orchestrator.produce_post()` (draft → critic → refine → score-gate → image), one post at a time.
- **REVIEW** — returns the batch with per-post rationale, confidence, and convergence reason.

### `PlaybookAgent` (`src/agents/playbook_agent.py`)

Reads tagged real outcomes (`src/memory/outcomes.py`'s `gather_tagged_outcomes()` — Workbench assets the creator marked succeeded/underperformed/failed) and writes new procedural rules the copywriter follows going forward. Exposed via `playbook.py`.

### Agent memory — `AgentMemoryStore` (`src/memory/store.py`)

ChromaDB-backed, three collections matching a semantic/episodic/procedural split:

- **semantic** — brand-invariant voice rules (from `brand_profile.json`)
- **episodic** — campaign-specific outcomes with signal metrics (hook pattern, watch time, save rate — from `workbench.db`)
- **procedural** — platform formatting rules

The store deliberately never conflates semantic and episodic into one overwriting summary, to avoid campaign-specific data overwriting brand-invariant tone rules.

---

## 5. Data Pipeline & Instagram Ingestion

### Two ingestion paths, one downstream pipeline

Instagram data can enter the system two ways, both writing into the same `scraped_dataset/` schema so the 3-stage pipeline below is unchanged either way:

1. **OAuth Connect** (`api/routers/connect.py`, `src/scrapers/instagram_api.py`) — the creator authorizes their own Business/Creator account once via Instagram Login (`IG_APP_ID`/`IG_APP_SECRET`/`IG_REDIRECT_URI` env vars). The app then pulls media + insights via the Graph API on demand or via the background poll loop, and persists the token + `granted_permissions` to `data/ig_connection.json`.
2. **Instaloader / data-export onboarding** (`api/routers/onboard.py`, `src/scrapers/instaloader_scraper.py`) — the original self-serve path: either a public-profile scrape by handle, or an uploaded Instagram official data-export ZIP. Still fully supported alongside OAuth Connect.

### Stage 1 — `src/data/pipeline.py`

Input: `scraped_dataset/*.json` → Output: `data/cleaned/*.json`

Runs captions through `ftfy` (fixes Unicode garbling from Instagram exports), splits each post into a marketing `hook` versus logistics (contact/ordering lines detected per-line, not per-paragraph, since brands often mix both in one caption block), and writes one cleaned JSON record per surviving post.

### Stage 2 — `src/embeddings/cluster.py`

Input: `data/cleaned/*.json` → Output: `data/clusters.json`

Embeds marketing hooks with `sentence-transformers` (`all-MiniLM-L6-v2`, local), L2-normalizes, and runs scikit-learn `KMeans(n_clusters=5)` to segment posts into content pillars. Device selection is `"auto"` (`mps` / `cuda` / `cpu`) — platform-neutral, not hardcoded to any one accelerator.

### Stage 3 — `src/embeddings/profile_extractor.py`

Input: `data/clusters.json` → Output: `data/brand_profile.json`

For each non-empty cluster, calls Granite once (Invocation #1) with up to 12 sample posts to extract `content_pillar`, `tone_descriptors`, `vocabulary_patterns` (`recurring_words`, `signature_phrases`, `emoji_style`), `avoided_terms`, `structural_signature`, and `representative_post`. After all clusters are named, a de-duplication pass checks for colliding pillar names (same first word) and — only if needed — makes one extra Granite call showing all pillar names at once so the model can rename the colliding ones distinctly.

### `data/brand_profile.json` schema

```json
{
  "brand_name": "...",
  "ig_handle": "...",
  "brand_bio": "...",
  "timezone": "Asia/Kolkata",
  "model_used": "granite3.1-dense:8b",
  "inference_backend": "ollama-local",
  "n_clusters": 5,
  "cluster_profiles": [
    {
      "cluster_id": 0,
      "post_count": 2,
      "profile": {
        "content_pillar": "...",
        "tone_descriptors": ["..."],
        "vocabulary_patterns": {
          "recurring_words": ["..."],
          "signature_phrases": ["..."],
          "emoji_style": "..."
        },
        "avoided_terms": ["..."],
        "structural_signature": "...",
        "representative_post": "..."
      }
    }
  ]
}
```

`cluster_profiles` is a **list**, not a flat dict keyed by cluster id — every consumer (`caption_generator.cluster_profiles()`, `create.py`'s `_cluster_vocab()`, etc.) looks up the matching entry with `next((c for c in profiles if c["cluster_id"] == cluster_id), profiles[0])`.

This is the longest stage of a fresh sync (several minutes): one Granite call per cluster, each roughly a minute on this hardware.

---

## 6. Frontend Layer

### App Router structure

```
frontend/app/
├── (marketing)/            Public marketing site: /, /how-it-works, /manifesto, /pricing
└── app/
    ├── layout.tsx          StudioLayout: StudioSidebar + StudioHeader + JarvisWidget,
    │                       wrapped in WorkbenchDrawerProvider
    ├── today/page.tsx      Today — daily briefing
    ├── dashboard/page.tsx  Dashboard — KPIs, top posts, charts, Ask-JARVIS
    ├── brand/page.tsx      Brand Voice — extracted profile + Drift Watchdog
    ├── create/page.tsx     Generate — Blank Page Solver → captions → Drift Test →
    │                       Resonance Simulator → Brand Guardian → Script Studio
    ├── analyze/page.tsx    Diagnose — Why Engine + Recovery Brief
    ├── discover/page.tsx   Strategy — Voice Timeline, Strategic Insights, Boost Advisor
    ├── agents/page.tsx     Agents — Autopilot + Self-Improving Playbook
    ├── triage/page.tsx     Inbox Triage — comment/DM classification + drafted replies
    └── onboard/page.tsx    Self-serve onboarding (full-screen overlay, bypasses the sidebar)
```

Eight studio tabs are registered in `frontend/components/layout/StudioSidebar.tsx`'s `NAV` array: Today, Dashboard, Brand voice, Generate, Diagnose, Strategy, Agents, Inbox Triage — each mapped to its route above.

### Cross-cutting UI (not nav tabs)

- **`JarvisWidget`** (`frontend/components/agent/JarvisWidget.tsx`) — a floating voice/text assistant mounted once in `StudioLayout`, present on every studio page. Talks to `agent.py` (`/api/agent/chat`) and `voice.py` (STT/TTS).
- **Workbench drawer** (`frontend/components/workbench/WorkbenchDrawer.tsx`, `WorkbenchDrawerProvider`) — a save-drawer any tab can open to persist a generated asset (caption, script, recovery brief, agent output) to `workbench.db`, star it, and tag its real-world outcome. Tagging an outcome as "underperformed"/"failed" triggers the autonomous Recovery Agent server-side.

### State management

React Query (`@tanstack/react-query`) handles server state; each API call has a dedicated query key, `staleTime` defaults keep tab-switches from unnecessary re-fetching. No global store (no Redux/Zustand) — component-local `useState` for forms and UI transitions, plus the one small `WorkbenchDrawerContext` for the drawer's open/closed state.

### API client — `lib/api.ts`

`apiFetch<T>(path, init?)` prepends `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`), sets JSON headers, and throws on non-2xx responses with status + body text. Upload-style calls (ZIP export, image describe) bypass this wrapper for raw multipart `fetch`.

---

## 7. Caching Architecture

### Generator/agent singleton cache (`api/dependencies.py`)

Every factory is `@lru_cache(maxsize=1)` — built once per process, reused across requests. `onboard.py`'s `_clear_caches()` calls `.cache_clear()` on the generator factories after a fresh sync writes new `brand_profile.json`/`clusters.json`, so the next request rebuilds with current data. `get_sentence_embedder()` is deliberately excluded (model weights only, never goes stale).

### Compute caches per router

Several routers memoize expensive (Granite-calling) compute functions the same way `discover.py` always has:

```python
@lru_cache(maxsize=1)
def _compute_voice_timeline() -> dict: ...
@lru_cache(maxsize=1)
def _compute_strategic_insights() -> dict: ...
@lru_cache(maxsize=1)
def _compute_boost_advisor() -> dict: ...
```

`strategy.py` and `insights.py` follow the same pattern for their own expensive aggregations. First load is slow (Granite calls, tens of seconds); every later load is a cache hit.

`diagnose.py` uses **disk** caching instead — one JSON file per post at `data/diagnoses/{shortcode}.json` — specifically because `lru_cache` evaporates on `uvicorn --reload`, and per-post diagnoses are expensive enough (one Why Engine call each) that losing them on every code change during development would be painful. `today.py` reuses `strategy.py`'s already-cached diagnoses rather than re-running Why Engine a third time.

### Invalidation

`_clear_caches()` (called from `onboard.py` after a fresh sync, and from `connect.py`'s sync path) clears the generator singletons and the `discover.py` compute caches so a re-sync's new data is reflected everywhere. Disk-cached diagnoses in `data/diagnoses/` are not automatically invalidated by a re-sync — they persist per-shortcode.

### No request-level caching

There is deliberately no HTTP-level caching (`Cache-Control`, ETags). All caching is in-process (`@lru_cache`) or on-disk (diagnoses, `workbench.db`), keeping invalidation logic centralized rather than spread across HTTP semantics.

---

## 8. Request Flows

### The Drift Test — `POST /api/create/drift-compare`

The hero feature: the same creative brief run through a brand-blind baseline and StyleSync, both scored against the real brand profile.

```
User fills a brief in Generate → "Run the Drift Test"
    │
    ▼
POST /api/create/drift-compare  {product, occasion, desired_feel, cluster_id}
    │
    ├─ get_baseline_caption_generator().generate(product, occasion)
    │       └─ generic prompt, NO brand profile, NO cluster grounding
    │          (same granite3.1-dense:8b model — isolates grounding, not model quality)
    │
    ├─ get_caption_generator().generate(product, occasion, desired_feel, cluster_id)
    │       └─ Granite Call #2 — full brand voice + cluster tone + avoided terms
    │
    ├─ _cluster_vocab(cluster_id) → vocabulary_patterns + avoided_terms from brand_profile.json
    │
    └─ for each side: _score_side(caption, vocab, avoided, clusters_data, embedder)
            ├─ PRIMARY:   score_voice_fidelity() — deterministic match against the
            │             creator's own signature phrases / recurring words / avoided terms
            └─ SECONDARY: detect_nearest_cluster_and_signal() — embedding topical band
                           (shows both captions are on-topic; the point is on-topic ≠ on-voice)
    │
    ▼
return {baseline: {caption, score, matched_words, ...}, stylesync: {...}}
```

No extra Granite call is spent on scoring — fidelity is deterministic Python, so the comparison is reproducible and free to re-run.

### Autopilot — `POST /api/agent-run/start`

```
User picks post count, platform, confidence gate → "Run Autopilot"
    │
    ▼
POST /api/agent-run/start {steer, target_count, platform, confidence_threshold}
    │
    ▼
start_autopilot_job() → job_id, spawns a daemon thread running WeeklyAutopilot.run()
    │
    ├─ THINK  (pilot.think)
    │     ├─ orchestrator.assess_gaps()         — over/under-used pillars (Analytics)
    │     ├─ orchestrator.get_trends()          — live trend briefing (Trend Agent, #22)
    │     ├─ orchestrator.recall_performance()  — episodic memory, past real outcomes
    │     ├─ Granite reasons over the evidence → weekly plan {posts: [{cluster_id, angle, rationale}]}
    │     └─ if plan.needs_user_input: job.status = "awaiting_input"; blocks on
    │        threading.Event until POST /api/agent-run/{job_id}/answer sets it
    │
    ├─ ACT  (pilot.act) — for each planned post:
    │     └─ orchestrator.produce_post(payload)
    │           ├─ CopywritingAgent drafts a caption
    │           ├─ convergence loop: CriticAgent critiques → typed routing
    │           │     (ai_slop → rewrite, off_brand_vocab → BrandVoiceAgent enforce,
    │           │      wrong_platform → reformat, factual_gap → stop + flag human review)
    │           │     until goal_met | plateau | factual_gap | max_cycles (8)
    │           └─ AnalyticsAgent (final score) ∥ VisualAgent (image prompt), parallel
    │
    └─ REVIEW — job.status = "done"; posts[] with per-post caption, confidence,
                convergence_reason, image_prompt

Frontend polls GET /api/agent-run/{job_id} — trace[] streams live so the UI
can show the agent's reasoning as it happens, not just a spinner.
```

### Why Engine post-mortem cascade — `POST /api/analyze/why-engine`

Shows how one endpoint chains into two other subsystems depending on the verdict.

```
User pastes a real post + its metrics → "Diagnose"
    │
    ▼
POST /api/analyze/why-engine {caption, post_type, views, reach, likes, comments, shares, saves, ...}
    │
    ▼
WhyEngine.analyze(...)   — Granite Call #4
    │  returns {verdict, diagnosis, what_worked, what_failed, brand_voice_gap, change_next_time}
    │
    ├─ if verdict in (underperformed, failed):
    │     RecoveryBriefGenerator.generate(diagnosis, what_failed, brand_voice_gap, cluster_id)
    │     → Granite Call #10 → result["recovery_brief"]  (non-fatal if this fails)
    │
    ├─ ConfidenceScorer.score(context_summary, output_summary)
    │     → Granite Call #15 → result["confidence"]  (non-fatal if this fails)
    │
    └─ if verdict == succeeded:
          background_tasks.add_task(run_repurpose_pipeline, ...)
          → fans the winning caption out to Reel/Carousel/Static/Story via
            ScriptGenerator (#9), landing every format directly in the Workbench
          → result["repurpose_job_id"]  (poll via GET /api/repurpose/status/{id})
```

### Onboarding — two paths into the same pipeline

```
Path A: handle scrape                      Path B: data-export upload
POST /api/onboard/start                    POST /api/onboard/upload
  {handle, brand_name}                       (ZIP file)
    │                                           │
    ▼                                           ▼
job_id created → BackgroundTask: _run_handle_pipeline / _run_export_pipeline
    │
    ├─ Instaloader scrape (Path A only) or ZIP extraction (Path B only)
    ├─ pipeline.py     — clean + normalize captions      → data/cleaned/
    ├─ cluster.py      — embed + K-Means                 → data/clusters.json
    ├─ profile_extractor.py — Granite per cluster (#1)    → data/brand_profile.json
    ├─ _clear_caches()
    └─ job status → "done"

GET /api/onboard/status/{job_id}   ← polled by the frontend
    on error: {status: "error", message: "..."} — e.g. a private account for Path A —
    and the UI offers the data-export upload as a fallback.

Path C (not a job): OAuth Connect (api/routers/connect.py) — one-time authorization,
then the background _instagram_poll_loop keeps the profile fresh without any job UI.
```
