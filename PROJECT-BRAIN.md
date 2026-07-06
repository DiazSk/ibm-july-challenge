# StyleSync — PROJECT BRAIN

> Complete context dump for resuming work on any machine.  
> Last updated: 2026-07-06. Covers the entire project from day 0 to current state.

---

## 1. The Contest

| Field | Value |
|-------|-------|
| Challenge | IBM "Reimagine Creative Industries with AI" — July 2026 |
| Deadline | **July 31 2026, 11:59 PM ET** |
| Team | Solo — Zaid Shaikh (Northeastern CS, shaikh.zaid@northeastern.edu) |
| Demo brand | `@hot_cakesbakes` — artisanal bakery, Navi Mumbai |
| Primary requirement | IBM Granite as a **core functional component**, not cosmetic |
| Required deliverables | Working product + README with "How IBM Bob was used" section + IBM SkillsBuild certificate |

---

## 2. The Product

**StyleSync** is a Creative Intelligence Platform for Instagram creators. It ingests a creator's own historical posts, clusters them into content pillars, extracts a brand voice profile with IBM Granite, and then uses that profile for generation, diagnosis, and strategy — entirely locally, no cloud AI calls at inference time.

### The core thesis

> Every other AI creative tool assumes you know what you want to make. StyleSync starts from the opposite question: **who are you already, and how do you make more of that?**

### The unique claims
- Brand voice is derived from observed behavior (100+ posts), not user self-description
- Post-failure diagnosis explains *why* — not just what the metrics say
- Strategy signal identifies underutilized vs over-invested content territory
- 14 coordinated Granite invocations, zero third-party AI at inference
- All audio, data, and inference stays local — the demo works in a room with no internet

---

## 3. Version History (commit-by-commit)

### Epoch 0 — Raw scraping prototype (fa8a19c, 2cceedc)
Initial project structure. Instaloader scraper, data pipeline stages, embedding modules. No UI. Just Python scripts producing JSON.

### Epoch 1 — Streamlit UI + Granite generations (43f3263)
First working Streamlit app. Added `CaptionGenerator` (Granite #2) and `ImagePromptGenerator` (Granite #3). Brand profile extraction (Granite #1) running against clusters. First demo-able version.

### Epoch 2 — Why Engine (15df796)
`WhyEngine` class (Granite #4). Diagnoses Instagram post performance: verdict (Succeeded/Underperformed/Failed) + diagnosis + brand voice gap. Standalone demo script. JSON output format.

### Epoch 3 — Why Engine hardening (bc7af80)
Added reach and average watch time metrics to the Why Engine template. Streamlit performance metrics form updated.

### Epoch 4 — Discover features: Voice Timeline + Strategic Insights (b1d647d, 8cf7410)
- `VoiceTimeline` class (Granite #5) — monthly cluster distribution → narrative of creative evolution
- `StrategicInsights` class (Granite #8) — richness rank vs volume rank → strategy brief
- `VoiceTimelineChart` and `CaptionVariants` components added to Discover tab

### Epoch 5 — Cluster label refactor + brand endpoint updates (73e8f0b, b781eec)
Refactored cluster label handling throughout brand endpoints. Profile data retrieval structure updated.

### Epoch 6 — Blank Page Solver (1ea1bdf)
`MomentAnalyzer` (Granite #6) + `DirectionGenerator` (Granite #7). User describes a real moment → emotional core extraction → 3 creative directions → auto-populate CaptionGenerator. This was the "wow" feature for the demo.

### Epoch 7 — Full Next.js migration + Workbench (264266a, f20e276)
**Major pivot:** Replaced Streamlit with Next.js 16 + FastAPI architecture. Quiet-luxury design system (`#F9F7F4` bg, Georgia serif headings, `#2D2D2D` buttons). Added:
- Full onboarding UI (handle scrape + ZIP export paths)
- `WorkbenchDrawer` component (SQLite-backed asset scratchpad)
- `useLocalStorage` hook for cross-tab state persistence
- React Query throughout

### Epoch 8 — Workbench polish (b96af3f, b20be4f)
WorkbenchDrawer asset content display refactored. `CopyButton` component introduced.

### Epoch 9 — Boost Advisor (5099c58)
`BoostAdvisor` class (Granite #11). Cross-references cluster engagement data with richness/volume ranks to produce a concrete recommendation: which cluster to boost, which post, which Instagram objective, which cluster NOT to boost and why.

### Epoch 10 — Demo engagement data (3268a90)
Added `_DEMO_ENGAGEMENT` / `_FALLBACK_ENGAGEMENT` to `discover.py` and `jarvis_agent.py`. Guards against `max({})` crash when `clusters.json` has no `cluster_engagement` key (standard Instagram export has no metrics — demo data fills this gap).

### Epoch 11 — JARVIS Agent (da79957, b52f993, 92d229d)
Full JARVIS floating widget. Two new Granite invocations:
- **Granite #13** — `JarvisAgent`: multi-turn conversational brain, intent routing + natural spoken response
- **Granite #14** — `InspirationSynthesizer`: DuckDuckGo web search snippets → 3 brand-adapted content ideas

Persistent bottom-right floating button on all pages. Holds multi-turn conversations. Dispatches to existing generators (captions, post-mortem, web research, workbench read/save). Original voice: `SpeechRecognition` + `speechSynthesis` (browser-native).

### Epoch 12 — Voice Upgrade: Whisper STT + Kokoro TTS (c902a18 — current HEAD)
Replaced browser speech APIs with a proper voice pipeline to fix three bugs:
1. Emojis spoken aloud by `speechSynthesis` ("🍩" → "donut emoji")
2. Browser VAD cutting the user off mid-sentence (`SpeechRecognition` + `continuous:false`)
3. Robotic browser TTS voice

**New backend:**
- `src/generation/voice_transcriber.py` — faster-whisper (Whisper small), CUDA auto-detect, RTX 4060 optimized
- `src/generation/voice_synthesizer.py` — Kokoro TTS (`am_echo` voice), emoji stripping regex, returns WAV bytes
- `api/routers/voice.py` — `POST /api/voice/transcribe` + `POST /api/voice/synthesize`
- `api/dependencies.py` — two new `@lru_cache(maxsize=1)` singletons
- `api/main.py` — voice router at `/api/voice`
- `api/routers/onboard.py` — voice singletons added to `_clear_caches()`

**Frontend JarvisWidget.tsx:**
- `srRef` → `mediaRecorderRef` + `audioChunksRef` + `currentAudioRef`
- `SpeechRecognition` → `MediaRecorder` push-to-talk (no VAD, user controls stop)
- `speechSynthesis` → `POST /api/voice/synthesize` → `new Audio().play()`
- `interim` state removed; replaced with "Recording…" indicator
- Replay button removed

---

## 4. Current Architecture

```
ibm-july-challenge/
├── api/                          FastAPI backend
│   ├── main.py                   App + CORS + router registration
│   ├── dependencies.py           @lru_cache singletons (14 generator instances)
│   └── routers/
│       ├── brand.py              GET /brand/profile, /brand/clusters
│       ├── create.py             POST analyze-moment, directions, captions, image-prompt, script
│       ├── analyze.py            POST why-engine (chains Recovery Brief automatically)
│       ├── discover.py           GET voice-timeline, strategic-insights, boost-advisor
│       ├── workbench.py          CRUD /workbench/assets (SQLite)
│       ├── onboard.py            POST start, upload; GET status, has-profile; POST reset-demo
│       ├── agent.py              POST /agent/chat, GET /agent/session/{id}
│       └── voice.py              POST /voice/transcribe, /voice/synthesize
│
├── src/
│   ├── data/pipeline.py          Caption cleaning + structuring from scraped JSONs
│   ├── embeddings/
│   │   ├── cluster.py            K-Means clustering (sentence-transformers)
│   │   └── profile_extractor.py  Brand Profile Extractor (Granite #1)
│   ├── generation/
│   │   ├── caption_generator.py  Granite #2
│   │   ├── image_prompt_generator.py  Granite #3
│   │   ├── why_engine.py         Granite #4
│   │   ├── voice_timeline.py     Granite #5
│   │   ├── blank_page_solver.py  Granite #6 (MomentAnalyzer) + #7 (DirectionGenerator)
│   │   ├── strategic_insights.py Granite #8
│   │   ├── script_generator.py   Granite #9
│   │   ├── recovery_brief.py     Granite #10
│   │   ├── boost_advisor.py      Granite #11
│   │   ├── voice_refiner.py      Granite #12 (legacy VoiceCapture, still present)
│   │   ├── jarvis_agent.py       Granite #13 (JarvisAgent) + #14 (InspirationSynthesizer)
│   │   ├── voice_transcriber.py  faster-whisper STT (NOT Granite — local model)
│   │   └── voice_synthesizer.py  Kokoro TTS (NOT Granite — local model)
│   └── tools/web_search.py       DuckDuckGo wrapper for JARVIS inspiration tool
│
├── frontend/                     Next.js 16 App Router
│   ├── app/
│   │   ├── layout.tsx            Root layout — Providers + JarvisWidget (global)
│   │   ├── page.tsx              Root redirect (has-profile check → onboard or /create)
│   │   ├── onboard/page.tsx      Onboarding flow UI
│   │   ├── create/page.tsx       Create tab
│   │   ├── analyze/page.tsx      Analyze tab
│   │   └── discover/page.tsx     Discover tab
│   ├── components/
│   │   ├── agent/JarvisWidget.tsx  JARVIS floating widget (MediaRecorder + Kokoro)
│   │   ├── create/               BlankPageSolver, CaptionBrief, CaptionVariants,
│   │   │                         ImageDirectionCard, ScriptStudio, VoiceCapture
│   │   ├── analyze/              WhyEngineForm, DiagnosisPanel, RecoveryBrief
│   │   ├── discover/             VoiceTimelineChart, StrategicInsightsChart,
│   │   │                         StrategyBrief, TimelineNarrative, BoostAdvisor
│   │   ├── workbench/            WorkbenchDrawer
│   │   └── layout/               NavTabs, Providers, Sidebar
│   └── lib/
│       ├── api.ts                All fetch wrappers (BASE = NEXT_PUBLIC_API_URL ?? localhost:8000)
│       ├── types.ts              All TypeScript interfaces
│       ├── useLocalStorage.ts    Cross-tab state persistence hook
│       ├── queryClient.ts        React Query setup
│       └── utils.ts              Helpers
│
├── data/
│   ├── brand_profile.json        Live profile (active account)
│   ├── clusters.json             Live clusters (active account)
│   ├── demo_brand_profile.json   @hot_cakesbakes reference data
│   └── demo_clusters.json        @hot_cakesbakes reference data (+ cluster_engagement)
│
├── scraped_dataset/              Raw scraped JSONs from Instaloader
├── docs/                         architecture.md, data-catalog.md, debugging.md,
│                                 onboarding.md, platform-guide.md, product-brief.md
├── requirements.txt
├── run_pipeline.py               One-shot pipeline runner (scrape → cluster → profile)
├── ig_scraper.py                 ZIP export parser
└── venv/                         Python virtualenv (DO NOT commit)
```

---

## 5. The 14 Granite Invocations

| # | Class | File | Trigger |
|---|-------|------|---------|
| 1 | `BrandProfileExtractor` | `src/embeddings/profile_extractor.py` | Onboarding pipeline |
| 2 | `CaptionGenerator` | `src/generation/caption_generator.py` | Create tab — Caption Brief |
| 3 | `ImagePromptGenerator` | `src/generation/image_prompt_generator.py` | Create tab — Image Direction |
| 4 | `WhyEngine` | `src/generation/why_engine.py` | Analyze tab |
| 5 | `VoiceTimeline` | `src/generation/voice_timeline.py` | Discover tab |
| 6 | `MomentAnalyzer` | `src/generation/blank_page_solver.py` | Create tab — Blank Page Solver step 1 |
| 7 | `DirectionGenerator` | `src/generation/blank_page_solver.py` | Create tab — Blank Page Solver step 2 |
| 8 | `StrategicInsights` | `src/generation/strategic_insights.py` | Discover tab |
| 9 | `ScriptGenerator` | `src/generation/script_generator.py` | Create tab — Script Studio |
| 10 | `RecoveryBriefGenerator` | `src/generation/recovery_brief.py` | Analyze tab — auto-chained on failure/underperform |
| 11 | `BoostAdvisor` | `src/generation/boost_advisor.py` | Discover tab |
| 12 | `VoiceRefiner` | `src/generation/voice_refiner.py` | Legacy VoiceCapture (still wired to `/api/create/voice-refine`) |
| 13 | `JarvisAgent` | `src/generation/jarvis_agent.py` | JARVIS widget — every conversation turn |
| 14 | `InspirationSynthesizer` | `src/generation/jarvis_agent.py` | JARVIS widget — when `search_inspiration` tool called |

All use `OllamaLLM(model="granite3.1-dense:8b")` via LangChain. Temperature varies by task (0.4–0.7).

---

## 6. Voice Pipeline (Epoch 12 — Current)

The JARVIS voice system uses a dedicated STT + TTS stack completely separate from Granite:

```
User clicks mic button
  → MediaRecorder.start() (browser, push-to-talk, no VAD)
User clicks stop
  → Blob(audioChunksRef.current, {type: "audio/webm"})
  → POST /api/voice/transcribe (multipart)
  → faster-whisper (small model, CUDA on RTX 4060)
  ← {transcript: "..."}
  → sendToJarvis(transcript)
  → POST /api/agent/chat (Granite #13 + optionally #14)
  ← {response, action_result}
  → POST /api/voice/synthesize {text: response}
  → Kokoro TTS (am_echo voice, emoji-stripped server-side)
  ← audio/wav bytes
  → new Audio(URL.createObjectURL(blob)).play()
```

**Why these choices:**
- `faster-whisper` over `openai-whisper`: 4× faster, CTranslate2 CUDA, handles audio/webm from MediaRecorder
- `kokoro am_echo`: natural American male voice — JARVIS-appropriate. Apache-2.0.
- `MediaRecorder` over `SpeechRecognition`: user controls stop, no browser VAD cutting mid-sentence
- Emoji stripping in `VoiceSynthesizer._clean()`: Granite sometimes outputs emoji — Kokoro would speak them literally

---

## 7. Demo Brand Data — @hot_cakesbakes

| Field | Value |
|-------|-------|
| Handle | @hot_cakesbakes |
| Niche | Artisanal bakery, Navi Mumbai |
| Posts | 113 |
| Timespan | Oct 2025 – Jun 2026 (8 months) |
| Clusters | 5 |

**Cluster breakdown:**

| ID | Name | Richness Rank | Volume Rank | Avg Engagement |
|----|------|--------------|-------------|----------------|
| C0 | Homemade Classics | #3 | #1 | 4.6% |
| C1 | Artisan Techniques | #1 | #3 | 7.8% |
| C2 | Seasonal Specials | #2 | #4 | 6.2% |
| C3 | Behind the Scenes | #4 | #2 | 5.1% |
| C4 | Bomboloni | #1 | #4 | **11.1%** |

**Key data insight:** March 2026 — Bomboloni spiked to 48% of all content. Oct 2025 — 57% basic product showcase (C0). Strategy gap: C1 is richness rank #1 but volume rank #3 (underutilized). C0 is volume rank #1 but richness rank #3 (over-invested).

**To restore demo data:**
```bash
cp data/demo_brand_profile.json data/brand_profile.json
cp data/demo_clusters.json data/clusters.json
```
Or hit: `POST /api/onboard/reset-demo`

---

## 8. Setup on the Acer Predator (Windows, RTX 4060)

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Ollama for Windows](https://ollama.com/download) — install and start
- Git

### First-time setup

```bash
# 1. Clone / pull latest
git clone <repo> ibm-july-challenge
cd ibm-july-challenge

# 2. Python venv
python -m venv venv
venv\Scripts\activate        # Windows

# 3. CUDA PyTorch FIRST — required for Kokoro and faster-whisper GPU
pip install torch --index-url https://download.pytorch.org/whl/cu121

# 4. All other Python deps
pip install -r requirements.txt

# IMPORTANT: langchain-ollama may need explicit install
pip install "langchain-ollama>=0.3.0"

# 5. Node deps
cd frontend
npm install
cd ..

# 6. Pull Granite model (one-time, ~5 GB)
ollama pull granite3.1-dense:8b

# 7. Load demo data
copy data\demo_brand_profile.json data\brand_profile.json
copy data\demo_clusters.json data\clusters.json
```

### Running the stack

**Terminal 1 — Backend:**
```bash
venv\Scripts\activate
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open: `http://localhost:3000`

### Voice models (auto-download on first use)

The first time you use JARVIS voice, both models download automatically:
- **Whisper small:** ~244MB → `%USERPROFILE%\.cache\huggingface\hub\`
- **Kokoro:** ~325MB → same location

First transcribe/synthesize takes ~60s (download + load). Subsequent requests: ~80ms transcription, ~100ms synthesis on RTX 4060.

### Verifying the voice endpoints

```bash
# Health check
curl http://localhost:8000/api/health

# TTS test (should produce a WAV file)
curl -X POST http://localhost:8000/api/voice/synthesize ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"Hello from JARVIS\"}" ^
  --output test_speech.wav

# JARVIS chat test
curl -X POST http://localhost:8000/api/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"What is my best performing cluster?\"}],\"session_id\":\"test\"}"
```

---

## 9. API Reference (All Endpoints)

```
GET  /api/health

# Onboarding
GET  /api/onboard/has-profile
POST /api/onboard/start           {handle, brand_name}
POST /api/onboard/upload          multipart: file=.zip, account=str, brand_name=str
GET  /api/onboard/status/{job_id}
POST /api/onboard/reset-demo

# Brand data
GET  /api/brand/profile
GET  /api/brand/clusters

# Create tab
POST /api/create/analyze-moment   {moment_description, cluster_id?}
POST /api/create/directions       {moment_analysis, cluster_id}
POST /api/create/captions         {product, occasion, desired_feel, cluster_id, previous_captions?}
POST /api/create/image-prompt     {caption, cluster_id}
POST /api/create/script           {caption, post_type, cluster_id}
POST /api/create/voice-refine     {transcript, cluster_id}  ← Granite #12 legacy

# Analyze tab
POST /api/analyze/why-engine      {caption, post_type, metrics, cluster_id}
                                  → response includes recovery_brief when verdict=Failed/Underperformed

# Discover tab
GET  /api/discover/voice-timeline
GET  /api/discover/strategic-insights
GET  /api/discover/boost-advisor

# Workbench
POST   /api/workbench/assets      {asset_type, content, pillar?, cluster_id?, source_tab?}
GET    /api/workbench/assets      ?pinned=true
PATCH  /api/workbench/assets/{id} {pinned?: bool, actual_outcome?: str}
DELETE /api/workbench/assets/{id}

# JARVIS agent
POST /api/agent/chat              {messages: [{role, content}], session_id}
GET  /api/agent/session/{id}
DELETE /api/agent/session/{id}

# Voice pipeline
POST /api/voice/transcribe        multipart: audio=<blob>  → {transcript}
POST /api/voice/synthesize        {text, voice?}           → audio/wav bytes
```

---

## 10. Data Files

### `data/brand_profile.json`
Granite-generated brand voice profile. Key fields:
- `brand_name`, `ig_handle`, `brand_bio`
- `content_clusters[]` — array of cluster objects:
  - `cluster_id`, `cluster_label`, `post_count`
  - `tone_descriptors[]`, `content_pillar`
  - `signature_vocabulary[]`, `structural_patterns[]`
  - `brand_guidelines`

### `data/clusters.json`
K-Means clustering output. Key fields:
- `clusters[]` — per-cluster post lists, monthly distributions
- `cluster_engagement` (optional key) — `{C0: {avg_views, avg_likes, engagement_rate}, ...}`
  - Present in `demo_clusters.json`, absent in standard Instagram exports
  - All routers that need it fall back to `_DEMO_ENGAGEMENT` / `_FALLBACK_ENGAGEMENT`

### `data/workbench.db`
SQLite. Single table `workbench_assets`:
```sql
id TEXT PK, asset_type TEXT, cluster_label TEXT, cluster_id INT,
content TEXT (JSON blob), pinned INT DEFAULT 0, source_tab TEXT,
actual_outcome TEXT, recovery_brief_generated INT DEFAULT 0,
created_at TEXT DEFAULT (datetime('now'))
```

---

## 11. Design System

**Quiet-luxury aesthetic** — Jony Ive, not TechCrunch.

| Variable | Value | Use |
|----------|-------|-----|
| `--color-ql-bg` | `#F9F7F4` | Page background |
| `--color-ql-card` | `#FFFFFF` | Card surfaces |
| `--color-ql-gap` | `#F3F1EE` | Inset/gap fills |
| `--color-ql-border` | `#E8E4DE` | All borders |
| `--color-ql-dark` | `#2D2D2D` | Primary text, buttons |
| `--color-ql-muted` | `#8B8178` | Secondary text |
| `--color-ql-accent` | `#8B7355` | Accent (warm brown) |
| `--color-verdict-succeeded` | `#4A7C59` | Green |
| `--color-verdict-failed` | `#8B3A3A` | Red |
| `--color-verdict-underperformed` | `#8B7355` | Amber |

Typography: Georgia serif for headings, JARVIS panel headers, caption display. System sans for UI chrome.

---

## 12. Current Status (as of 2026-07-06)

### Fully working
- [x] All 14 Granite invocations wired and returning structured output
- [x] Next.js frontend — Create, Analyze, Discover, Workbench tabs all functional
- [x] Onboarding — both handle-scrape and ZIP-export paths
- [x] JARVIS floating widget — text + voice (push-to-talk)
- [x] Voice pipeline — faster-whisper STT + Kokoro TTS (emoji-stripped, natural voice)
- [x] Content Workbench — SQLite CRUD, pin, outcome tracking
- [x] Demo data for @hot_cakesbakes (brand_profile + clusters + engagement fallback)
- [x] TypeScript build: clean (`npm run build` passes with zero errors)
- [x] `_clear_caches()` in onboard.py invalidates all 14 singletons incl. voice models

### Requires Ollama locally (not included in repo)
- Ollama binary — download from ollama.com
- `granite3.1-dense:8b` model — `ollama pull granite3.1-dense:8b` (~5 GB)

### Pending for submission
- [ ] Install new voice deps on Acer Predator (`torch` CUDA, `faster-whisper`, `kokoro`, `soundfile`)
- [ ] Test full voice loop on Windows (browser → MediaRecorder → Whisper → Granite → Kokoro → Audio)
- [ ] README section: "How IBM Bob was used"
- [ ] IBM SkillsBuild course + upload completion certificate
- [ ] 3-minute demo video recording

---

## 13. Known Issues & Gotchas

### `ModuleNotFoundError: No module named 'langchain_ollama'`
```bash
pip install "langchain-ollama>=0.3.0"
```
This is separate from `langchain-ollama` in requirements.txt — exact version matters.

### `max({})` crash in `/api/agent/chat`
Fixed in Epoch 10. `clusters.json` from standard Instagram export has no `cluster_engagement` key. Both `api/routers/agent.py` and `src/generation/jarvis_agent.py` now fall back to `_DEMO_ENGAGEMENT` / `_FALLBACK_ENGAGEMENT` hardcoded dicts.

### Voice models not loading
Both faster-whisper and Kokoro download on first request. If the first `/api/voice/synthesize` or `/api/voice/transcribe` call times out, it's just downloading. Wait ~60s and retry. Check `%USERPROFILE%\.cache\huggingface\hub\` for download progress.

### Kokoro on Windows requires CUDA PyTorch
Must run `pip install torch --index-url https://download.pytorch.org/whl/cu121` BEFORE `pip install kokoro`. If installed in the wrong order, Kokoro falls back to CPU (still works, just slower — ~1s synthesis vs ~100ms).

### MediaRecorder `audio/webm` on Safari
Safari records `audio/mp4`, not `audio/webm`. The `voice.py` router detects content-type and passes the correct suffix to Whisper. Should work but not tested on Safari — Chrome/Edge are the primary targets.

### Ollama not running
All Granite invocations fail with a connection error if Ollama isn't running. Start with: `ollama serve` (or just launch Ollama desktop app). Verify with: `curl http://localhost:11434/api/tags`.

### Demo reset
If you've been testing and want to restore the @hot_cakesbakes demo state:
```bash
copy data\demo_brand_profile.json data\brand_profile.json
copy data\demo_clusters.json data\clusters.json
```
Or: `POST /api/onboard/reset-demo`

---

## 14. Three-Minute Demo Script

**Setup:** Demo data loaded, Ollama running, both servers up, Chrome open on localhost:3000.

### Minute 1 — The Wow (Create tab)
1. Open Create tab. Show the empty state.
2. Click "Blank Page Solver." Describe: *"It's Friday evening and we just pulled the last batch of Pistachio Rose Bomboloni from the fryer."*
3. Granite maps it to Bomboloni cluster (C4). Shows emotional core + 3 creative directions.
4. Pick direction #2. Caption Brief auto-populates.
5. Generate captions. Show 3 variants with brand reasoning underneath each.
6. Save one to Workbench.

### Minute 2 — The Data (Discover tab)
1. Open Discover tab. Voice Timeline loads.
2. Point at March 2026 spike: *"Bomboloni dominated 48% of all content that month."*
3. Granite narrates the creative arc.
4. Scroll to Strategic Insights. Show the richness vs volume chart.
5. *"Cluster 0 is over-invested — volume rank #1, richness rank #3. Cluster 1 is underutilized — richest vocabulary, lowest post volume. That gap is the strategy recommendation."*

### Minute 3 — JARVIS + Diagnosis
1. Click the mic button (bottom-right, any page).
2. Say: *"Research trending bakery content and give me 3 ideas."*
3. JARVIS searches the web (DuckDuckGo), synthesizes 3 brand-adapted ideas via Granite #14, reads them aloud in Kokoro voice, shows idea cards.
4. Navigate to Analyze tab. Paste a low-performing post caption + metrics.
5. Why Engine: verdict (Underperformed), diagnosis, brand voice gap.
6. Recovery Brief auto-appears: new hook + format recommendation + 150-word script.
7. Save Recovery Brief to Workbench.

**Closing line:** *"StyleSync is not a content tool. It's a creative operating system built from your own history — the first AI that starts from who you already are."*

---

## 15. Competitive Positioning

| Dimension | Octupie | ChatGPT | Analytics Tools | StyleSync |
|-----------|---------|---------|-----------------|-----------|
| Data source | Competitor accounts | Your prompt | Platform metrics | Your own posts |
| Core question | What's winning in my niche? | Write this for me | What happened? | Who am I, and where am I drifting? |
| Post diagnosis | No | No | No | Yes (Why Engine) |
| Recovery strategy | No | Partial | No | Yes (Recovery Brief) |
| Creative evolution | No | No | Basic | Yes (Voice Timeline) |
| Content strategy | No | No | No | Yes (Strategic Insights) |
| Boost Advisor | No | No | No | Yes (Granite #11) |
| Voice agent | No | Partial | No | Yes (JARVIS — Granite #13 + #14) |
| Privacy | Requires scraping | Cloud API | Cloud API | Fully local |
| IBM Granite | No | No | No | 14 invocations |

---

## 16. File Quick-Reference for Common Tasks

| Task | Files to edit |
|------|--------------|
| Change Granite model | Every class in `src/generation/` — `OllamaLLM(model=...)` |
| Add a new Granite feature | 1. `src/generation/new_feature.py` 2. `api/dependencies.py` (singleton) 3. `api/routers/*.py` (endpoint) 4. `api/routers/onboard.py` (`_clear_caches`) 5. `frontend/lib/types.ts` + `api.ts` 6. New component |
| Change JARVIS voice | `src/generation/voice_synthesizer.py` → `__init__(voice="am_echo")` — change to any Kokoro voice |
| Add JARVIS tool | `src/generation/jarvis_agent.py` → update system prompt tools list + `api/routers/agent.py` → add dispatch branch |
| Change demo data | `data/demo_brand_profile.json` + `data/demo_clusters.json` |
| Debug Granite responses | `api/routers/*.py` — log the raw LLM output before JSON parsing |
| CSS variables | `frontend/app/globals.css` |
| React Query keys | Grep `queryKey` in `frontend/` — convention is `["feature-name"]` |
