# StyleSync — PROJECT BRAIN

> Complete context dump for resuming work on any machine.  
> Last updated: 2026-07-11. Covers the entire project from day 0 to current state.

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

### Epoch 12 — Voice Upgrade: Whisper STT + Kokoro TTS (c902a18)
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

### Epoch 13 — JARVIS Voice Hardening + Audio Sync (68a46e5, 7b1d225)
Post-Epoch 12 hardening pass that fixed four production bugs discovered during full end-to-end voice testing on Windows/RTX 4060.

**Bug 1 — `NotSupportedError: Failed to load because no supported source was found`**  
`soundfile` was writing float32 WAV by default. Browsers only support 16-bit PCM WAV. Fixed:  
`sf.write(buf, samples, _SAMPLE_RATE, format="WAV", subtype="PCM_16")` in `voice_synthesizer.py`.

**Bug 2 — Voice synthesize 500 on calls 2+ (misaki `None` phonemes)**  
Kokoro's English G2P (`misaki`) returns `None` phonemes without `espeak-ng` installed (system binary, not pip). Line 693 of `misaki/en.py` did `None + str`. Patched directly:
```python
# Before: result = ''.join(t.phonemes + t.whitespace for t in tokens)
# After:
result = ''.join((t.phonemes or '') + t.whitespace for t in tokens)
```
This is a permanent fix for Windows without espeak-ng. Also required: `pip install num2words phonemizer`.

**Bug 3 — JARVIS caption tool routing (`action_result: null` on caption requests)**  
Granite 3.1 8B inconsistently returns captions inline rather than as a JSON tool call, causing `action_result` to be null and the CaptionCard UI never renders. Fixed by adding a regex pre-filter in `api/routers/agent.py` that detects unambiguous caption intent and synthesises the tool call before consulting Granite:
```python
_CAPTION_INTENT_RE = re.compile(
    r"\b(write|create|generate|make|craft|give\s+me|draft|compose)\b.{0,60}\b(caption|post|copy)\b"
    r"|\bcaption\s+(for|about|on)\b", re.IGNORECASE,
)
```
Includes a `_CLUSTER_HINT` keyword→cluster_id map (bomboloni→C4, nutella→C3, rasmalai/kunafa/biscuit pudding→C1, behind the scenes→C2).

**Bug 4 — Text and audio out of sync (text visible seconds before audio starts)**  
`sendToJarvis()` in `JarvisWidget.tsx` was calling `addMessage()` (text visible) before the TTS fetch, so text appeared ~100–500ms before audio. Fixed by reordering: TTS fetch completes first, then `addMessage()` and `audio.play()` fire together. Text bubble and voice now start at the exact same moment.

### Epoch 14 — Brand Muse AI UI port (2026-07-11)

**Major pivot:** Replaced the "quiet-luxury" design system with a full port of a separate reference project's UI ("Brand Muse AI" — a TanStack Start app with 100% mock data, no real backend), while keeping Next.js as the framework and the FastAPI backend **completely untouched**. Zero backend files changed in this epoch.

- **New "Dreamy Cloud" design system** — sky-blue primary, warm-orange accent, cream cards, soft cloudy-white background with three fixed radial gradients (blue top-left, peach top-right, cream bottom). Instrument Serif (display) + Work Sans (body) via `next/font/google`. Old `--color-ql-*`/`--color-verdict-*`/`--color-cluster-*` token *names* kept and remapped to new values (not renamed) so ~20 existing components re-skinned with zero logic edits.
- **Route restructuring** — `/` is now a real public marketing site; the studio moved to `/app/*`, mirroring Brand Muse AI's own `/` vs `/app` split:
  - `/` (marketing) — Landing, `/how-it-works`, `/manifesto`, `/pricing`
  - `/app` — smart redirect (has-profile check → `/app/onboard` or `/app/dashboard`)
  - `/app/onboard`, `/app/create`, `/app/analyze`, `/app/discover` — moved from the old flat `/onboard`, `/create`, `/analyze`, `/discover`
  - `/app/dashboard`, `/app/brand` — **new pages**, wired to real data only (KPIs derived from `/api/brand/clusters`, recent generations from Workbench, tone/vocabulary from `/api/brand/profile`) — no fabricated numbers (Brand Muse's mock `brandHealth`/`updatedAt`/tone-axis-slider fields were dropped since there's no real Granite output backing them)
- **New layout shell** — `StudioSidebar.tsx` (5-icon nav + brand chip) + `StudioHeader.tsx` (active brand + Workbench "Saved (N)" trigger) replace the old `Sidebar.tsx`/`NavTabs.tsx` (deleted)
- **New shared components** — `site-chrome.tsx` (BrandMark/SiteNav/SiteFooter), `pillar-ring.tsx` (hero animation, driven by real @hot_cakesbakes engagement data via `lib/marketing-data.ts`, not fabricated)
- **JarvisWidget, Create/Analyze/Discover components, Workbench, Onboarding** — logic-frozen, only reskinned (colors/fonts swapped via the token remap; a handful of hardcoded hex/`"Georgia, serif"` literals fixed individually)
- Added `framer-motion` dependency (only new package — Brand Muse AI's shadcn/ui/Radix scaffold was confirmed unused by its actual pages and deliberately not ported, avoiding ~25 unneeded packages and version conflicts)

### Epoch 15 — Full QA pass + backend bug fixes (2026-07-11)

Full end-to-end QA (frontend UI → backend API → Granite generation) against the live stack (`uvicorn` + Ollama), documented in `QA-REPORT.md`. Found and fixed 5 real bugs — 2 frontend (introduced by/exposed during the Epoch 14 port), 3 pre-existing backend bugs the user asked to have fixed too:

- **Frontend fix 1** — `DiagnosisPanel.tsx` verdict-color matching was completely broken: `why_engine.py` always decorates `verdict_label` with symbols (`"✓  Succeeded"`, `"~  Underperformed"`, `"✗  Failed"`), so the exact-match `VERDICT_CONFIG` lookup never hit and **every** diagnosis silently rendered with the amber "Underperformed" color regardless of actual verdict — 100% reproducible. Fixed by deriving the color key from the raw `verdict` field (substring match) instead.
- **Frontend fix 2** — Brand Voice page (`app/app/brand/page.tsx`) mixed full sentences (`signature_phrases`) into a small-pill "vocabulary" tag cloud alongside single words (`recurring_words`), and had a "Lean Into" section that exactly duplicated "Tone". Split into a proper "Signature Vocabulary" (words) + "Signature Phrases" (quoted list) + removed the duplicate section.
- **Frontend fix 3** — Tailwind v4 `@layer` cascade bug in `globals.css`: the `h1, h2, h3, h4 { color: ... }` base rule (and other base styles) were written as plain unlayered CSS. In Tailwind v4, unlayered CSS always wins over `@layer utilities` classes regardless of specificity — so **no** Tailwind text-color utility could ever override a heading's color anywhere on the site (caused the marketing landing page's "Granite is not" heading to be invisible — dark text on the `GraniteBand` section's black background). Fixed by wrapping all base styles in `@layer base`, matching Tailwind's intended cascade.
- **Backend fix B1 (High)** — JARVIS's `search_inspiration` tool intermittently (~50% in testing) leaked raw tool-call JSON into the visible chat response instead of dispatching cleanly (same bug class already patched for the caption intent, but with no equivalent safety net) — directly affected the documented 3-minute demo script's minute-3 moment. Fixed by adding `_detect_inspiration_intent()` in `api/routers/agent.py`, mirroring the existing `_detect_caption_intent()` pre-filter pattern — bypasses Granite's flaky routing entirely for research/inspiration phrasing. Verified 8/8 clean trials after the fix (exact demo phrasing + varied natural phrasings), zero regressions to caption intent or plain brand Q&A.
- **Backend fix B2 (Medium)** — `image_prompt_generator.py` occasionally received malformed JSON from Granite (missing comma) and fell back to dumping the raw garbled LLM output into the UI. Added a 3-layer parse strategy: direct `json.loads` → comma-repair regex retry → last-resort regex field extraction. Verified against the exact malformed text captured during QA.
- **Backend fix B3 (Medium)** — `boost_advisor.py`'s `boost_cluster_id`/`boost_cluster_name` (and `dont_boost_*`) could disagree, since Granite free-generates the name independently of the ID it also produces. The code already overrode `boost_post_hook` from the authoritative `cluster_engagement` dict by ID but wasn't doing the same for the name fields — extended that existing pattern to also correct both name fields. Deterministic fix (not probabilistic like B1) — verified correct across a cache-cleared fresh Granite generation.

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
│   │   ├── layout.tsx             Root shell — html/body, next/font/google fonts, Providers only
│   │   ├── globals.css            Design tokens ("Dreamy Cloud") — @theme inline + @layer base
│   │   ├── (marketing)/           Public marketing site — route group, SiteNav+SiteFooter chrome
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            "/" — Landing (Hero w/ PillarRing, Inversion, HowItWorks teaser,
│   │   │   │                       WhatWeSee, GraniteBand, LocalFirst, DemoCallout, FinalCta)
│   │   │   ├── how-it-works/page.tsx
│   │   │   ├── manifesto/page.tsx
│   │   │   └── pricing/page.tsx
│   │   └── app/                   Studio — mirrors Brand Muse AI's own "/app/*" split
│   │       ├── layout.tsx          StudioSidebar + StudioHeader + JarvisWidget shell
│   │       ├── page.tsx             "/app" — smart redirect (has-profile → onboard or dashboard)
│   │       ├── onboard/page.tsx       "/app/onboard" — onboarding flow UI
│   │       ├── dashboard/page.tsx      "/app/dashboard" — real KPIs, pillar shares, recent
│   │       │                          generations (from Workbench), strategic brief
│   │       ├── brand/page.tsx           "/app/brand" — tone tags, signature vocabulary,
│   │       │                          signature phrases, avoid list, pillar signature cards
│   │       ├── create/page.tsx           "/app/create" — Create tab
│   │       ├── analyze/page.tsx           "/app/analyze" — Analyze tab
│   │       └── discover/page.tsx           "/app/discover" — Discover tab
│   ├── components/
│   │   ├── site-chrome.tsx        BrandMark, SiteNav, SiteFooter (marketing chrome)
│   │   ├── pillar-ring.tsx        Hero animated ring — driven by real @hot_cakesbakes data
│   │   ├── agent/JarvisWidget.tsx  JARVIS floating widget (MediaRecorder + Kokoro)
│   │   ├── create/               BlankPageSolver, CaptionBrief, CaptionVariants,
│   │   │                         ImageDirectionCard, ScriptStudio, VoiceCapture
│   │   ├── analyze/              WhyEngineForm, DiagnosisPanel, RecoveryBrief
│   │   ├── discover/             VoiceTimelineChart, StrategicInsightsChart,
│   │   │                         StrategyBrief, TimelineNarrative, BoostAdvisor
│   │   ├── workbench/            WorkbenchDrawer
│   │   └── layout/               StudioSidebar, StudioHeader, Providers
│   └── lib/
│       ├── api.ts                All fetch wrappers (BASE = NEXT_PUBLIC_API_URL ?? localhost:8000)
│       ├── types.ts              All TypeScript interfaces
│       ├── marketing-data.ts     Real @hot_cakesbakes numbers for illustrative marketing content
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

## 6. Voice Pipeline (built in Epoch 12, unchanged since)

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

Open: `http://localhost:3000` (public marketing site) — click "Open studio" or go to `http://localhost:3000/app` directly for the studio (smart-redirects to onboarding or the dashboard).

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

**"Dreamy Cloud" aesthetic** (Epoch 14, ported from Brand Muse AI) — sky blue, warm orange, cream, soft cloudy white. Replaced the original "quiet-luxury" theme; old `--color-ql-*`/`--color-verdict-*`/`--color-cluster-*` token *names* were kept and remapped to new values so ~20 existing components didn't need any code changes.

| Variable | Value | Use |
|----------|-------|-----|
| `--background` | `oklch(0.985 0.012 235)` | Page background (soft cloudy white) |
| `--card` / `--popover` | `oklch(0.995 0.006 80)` | Card surfaces (cream) |
| `--primary` / `--sky` | `oklch(0.68 0.13 235)` | Sky blue |
| `--accent` / `--gold` | `oklch(0.72 0.17 55)` | Warm orange (brand accent) |
| `--secondary` / `--muted` | pale sky-blue tints | Inset/gap fills |
| `--border` | `oklch(0.18 0.02 250 / 10%)` | All borders |
| `--foreground` / `--ink` | `oklch(0.18 0.02 250)` | Primary text |
| `--destructive` | `oklch(0.62 0.2 25)` | Red |
| `--success` (hand-picked, no native Dreamy Cloud green) | `oklch(0.62 0.13 155)` | Verdict succeeded |
| `--chart-1..5` | sky/gold/soft-sky/parchment/muted | Cluster colors (`--color-cluster-0..4`) |
| Legacy `--color-ql-*` / `--color-verdict-*` / `--color-cluster-*` | remapped via `@theme inline` in `globals.css` | Backward-compat token names used throughout components |

Body background: three fixed radial gradients (sky-blue top-left, peach top-right, cream bottom), `background-attachment: fixed`.

Typography: **Instrument Serif** (display/headings, JARVIS panel headers, caption display) + **Work Sans** (body/UI chrome), both via `next/font/google` in `frontend/app/layout.tsx`.

**Gotcha:** base styles (`body`, `h1-h4`, selection, scrollbar) in `globals.css` **must** live inside `@layer base { ... }`. Tailwind v4 gives unlayered CSS higher cascade priority than *any* `@layer utilities` class regardless of specificity — a plain `h1,h2,h3,h4 { color: ... }` rule outside a layer will silently defeat every `text-*` color utility applied to a heading, sitewide (this caused the GraniteBand marketing-page heading to render invisible until fixed in Epoch 15).

---

## 12. Current Status (as of 2026-07-11)

### Fully working
- [x] All 14 Granite invocations wired and returning structured output
- [x] Full UI port to "Dreamy Cloud" design system (Epoch 14) — marketing site (`/`) + studio (`/app/*`), zero backend changes
- [x] Next.js frontend — Dashboard, Brand Voice, Create, Analyze, Discover, Workbench all functional, all on real data
- [x] Onboarding — both handle-scrape and ZIP-export paths
- [x] JARVIS floating widget — text + voice (push-to-talk)
- [x] Voice pipeline — faster-whisper STT + Kokoro TTS — all bugs resolved (PCM_16 WAV, misaki patch, audio sync)
- [x] JARVIS caption tool routing — `_detect_caption_intent` pre-filter ensures CaptionCard always renders
- [x] JARVIS inspiration tool routing — `_detect_inspiration_intent` pre-filter (Epoch 15) ensures InspirationCards always renders, no raw JSON leak
- [x] JARVIS text + audio synchronized — text bubble and voice start at the same moment
- [x] Content Workbench — SQLite CRUD, pin, outcome tracking
- [x] Demo data for @hot_cakesbakes (brand_profile + clusters + engagement fallback)
- [x] TypeScript build: clean (`npm run build` passes with zero errors)
- [x] `_clear_caches()` in onboard.py invalidates all 14 singletons incl. voice models
- [x] Full voice loop tested end-to-end on Windows (browser → MediaRecorder → Whisper → Granite → Kokoro → Audio)
- [x] Full end-to-end QA pass (Epoch 15) — see `QA-REPORT.md` — 5 bugs found and fixed, rigorously re-tested (multiple trials each, since 2 of the 3 backend bugs were LLM-generation-dependent and intermittent)

### Requires Ollama locally (not included in repo)
- Ollama binary — download from ollama.com
- `granite3.1-dense:8b` model — `ollama pull granite3.1-dense:8b` (~5 GB)

### Pending for submission
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

### Kokoro pip install failure (spacy build error)
`pip install kokoro` pulls `misaki[en]` → `spacy-curated-transformers` → `spacy 4.0.0.dev3` source build which fails because `blis` requires Cython 3.0+. Fix:
```bash
pip install "spacy>=3.8,<4.0.0"
pip install kokoro
```

### numpy MINGW segfault on Windows
Kokoro pins `numpy==1.26.4` which installs an experimental MINGW build on Windows — causes uvicorn segfault at startup. Fix:
```bash
pip uninstall numpy -y
pip install "numpy>=2.0"
pip install kokoro --no-deps
```

### Kokoro synthesize 500 on calls 2+ (misaki `None` phonemes, Windows)
`misaki`'s English G2P returns `None` phonemes when `espeak-ng` system binary is not installed. Line 693 of `.venv/Lib/site-packages/misaki/en.py` concatenates `None + str` → TypeError. **Already patched** in the repo's venv:
```python
result = ''.join((t.phonemes or '') + t.whitespace for t in tokens)
```
Also required: `pip install num2words phonemizer`. If re-creating the venv, re-apply this patch manually.

### MediaRecorder `audio/webm` on Safari
Safari records `audio/mp4`, not `audio/webm`. The `voice.py` router detects content-type and passes the correct suffix to Whisper. Should work but not tested on Safari — Chrome/Edge are the primary targets.

### 4–5 second JARVIS response latency
This is Granite 8B inference time on Ollama (CPU or partial GPU), not a bug. TTS adds ~100ms after the response arrives. The text bubble and audio are now synchronized (Epoch 13) so the wait feels like one unified pause rather than two separate delays.

### Ollama not running
All Granite invocations fail with a connection error if Ollama isn't running. Start with: `ollama serve` (or just launch Ollama desktop app). Verify with: `curl http://localhost:11434/api/tags`.

### JARVIS `search_inspiration` tool JSON leak (fixed Epoch 15)
Granite intermittently (~50% observed) failed to emit a proper top-level `"tool"` key for the inspiration/research intent and instead embedded the tool-call JSON as literal text inside the spoken response — the chat bubble would show raw `{"response": null, "tool": {...}}` and `InspirationCards` never rendered. Same bug class as the caption-intent bug above, but with no equivalent safety net. **Fixed** via `_detect_inspiration_intent()` in `api/routers/agent.py` (mirrors `_detect_caption_intent()`) — bypasses Granite's flaky routing entirely for research/inspiration phrasing.

### Image Direction malformed JSON (fixed Epoch 15)
Granite occasionally returns JSON missing a comma between the `prompt` and `style_notes` fields. `image_prompt_generator.py`'s old fallback dumped the entire raw, garbled LLM output into the `prompt` field. **Fixed** with a 3-layer parse strategy: direct `json.loads` → comma-repair regex retry → last-resort regex field extraction (pulls the two string values without requiring valid JSON).

### Boost Advisor cluster name/ID mismatch (fixed Epoch 15)
`boost_cluster_id`/`boost_cluster_name` (and `dont_boost_*`) could disagree, since Granite free-generates the name field independently of the numeric ID it also produces. `boost_advisor.py` already overrode `boost_post_hook` from the authoritative `cluster_engagement` dict by ID but wasn't doing the same for the name fields. **Fixed** by extending that existing override pattern to also correct both `*_cluster_name` fields — deterministic, not probabilistic.

### Tailwind v4 `@layer` cascade gotcha (fixed Epoch 15)
Any base CSS rule in `globals.css` that sits *outside* an explicit `@layer` block (e.g. a plain `h1,h2,h3,h4 { color: ... }`) will always beat `@layer utilities` classes in Tailwind v4, regardless of specificity or source order. If a heading's Tailwind color utility (`text-white`, `text-gold`, etc.) silently has no effect, check that the base styles are wrapped in `@layer base { ... }`.

### Demo reset
If you've been testing and want to restore the @hot_cakesbakes demo state:
```bash
copy data\demo_brand_profile.json data\brand_profile.json
copy data\demo_clusters.json data\clusters.json
```
Or: `POST /api/onboard/reset-demo`

---

## 14. Three-Minute Demo Script

**Setup:** Demo data loaded, Ollama running, both servers up, Chrome open on `localhost:3000` (lands on the public marketing site — click "Open studio" or go straight to `localhost:3000/app`, which smart-redirects to the Dashboard since a profile exists).

### Minute 1 — The Wow (Create tab, `/app/create`)
1. Open Create tab (sidebar → "Generate"). Show the empty state.
2. Click "Blank Page Solver." Describe: *"It's Friday evening and we just pulled the last batch of Pistachio Rose Bomboloni from the fryer."*
3. Granite maps it to Bomboloni cluster (C4). Shows emotional core + 3 creative directions.
4. Pick direction #2. Caption Brief auto-populates.
5. Generate captions. Show 3 variants with brand reasoning underneath each.
6. Save one to Workbench.

### Minute 2 — The Data (Discover tab, `/app/discover`, sidebar → "Strategy")
1. Open Discover tab. Voice Timeline loads.
2. Point at March 2026 spike: *"Bomboloni dominated 48% of all content that month."*
3. Granite narrates the creative arc.
4. Scroll to Strategic Insights. Show the richness vs volume chart.
5. *"Cluster 0 is over-invested — volume rank #1, richness rank #3. Cluster 1 is underutilized — richest vocabulary, lowest post volume. That gap is the strategy recommendation."*

### Minute 3 — JARVIS + Diagnosis
1. Click the mic button (bottom-right, any page).
2. Say: *"Research trending bakery content and give me 3 ideas."*
3. JARVIS searches the web (DuckDuckGo), synthesizes 3 brand-adapted ideas via Granite #14, reads them aloud in Kokoro voice, shows idea cards.
4. Navigate to Analyze tab (`/app/analyze`, sidebar → "Diagnose"). Paste a low-performing post caption + metrics.
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
| CSS variables / design tokens | `frontend/app/globals.css` — remember base styles must stay inside `@layer base` |
| React Query keys | Grep `queryKey` in `frontend/` — convention is `["feature-name"]` |
| Edit a studio page | `frontend/app/app/{dashboard,brand,create,analyze,discover,onboard}/page.tsx` |
| Edit a marketing page | `frontend/app/(marketing)/{page.tsx,how-it-works,manifesto,pricing}/page.tsx` |
| Change studio nav / sidebar | `frontend/components/layout/StudioSidebar.tsx` (nav links + icons) |
| Change marketing nav/footer | `frontend/components/site-chrome.tsx` (SiteNav, SiteFooter, BrandMark) |
| Add a JARVIS intent pre-filter | `api/routers/agent.py` — follow the `_detect_caption_intent`/`_detect_inspiration_intent` pattern |
