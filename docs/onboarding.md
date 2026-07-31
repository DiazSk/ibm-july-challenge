# StyleSync — Developer Onboarding

This guide takes you from a fresh clone to a fully running StyleSync stack on **Windows**. It covers prerequisites, installation, first-run verification, and the paths for loading brand data (Instaloader/export pipeline, or a real Instagram OAuth connection).

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Clone and Install](#2-clone-and-install)
3. [Pull the Local Models](#3-pull-the-local-models)
4. [Environment Variables](#4-environment-variables)
5. [Start the Backend](#5-start-the-backend)
6. [Start the Frontend](#6-start-the-frontend)
7. [Load Brand Data](#7-load-brand-data)
8. [Verify Everything Works](#8-verify-everything-works)
9. [Project Layout Quick Reference](#9-project-layout-quick-reference)

---

## 1. System Requirements

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | Windows 10/11 | This guide is Windows-primary; substitute the POSIX equivalents in parentheses if you're on macOS/Linux |
| Python | 3.11+ | 3.14 tested; 3.11 and 3.12 work fine |
| Node.js | 18+ | 20 LTS recommended |
| RAM | 16 GB | Granite 3.1 8B loads ~6 GB; the vision/voice models add a few hundred MB each and are swapped in on demand, not resident concurrently |
| GPU | Optional | RTX 4060 8GB tested for Whisper/Kokoro acceleration; everything also runs on CPU (slower) |
| Storage | 12 GB free | Ollama models (Granite + moondream) + Whisper/Kokoro weights + embeddings + venv |
| Ollama | Any recent | Must be running before the backend starts |

Granite, moondream, and (mostly) the voice models all run locally — no cloud inference is required for the demo build. The `.env` IBM watsonx credentials are unused by the current Ollama-based pipeline; they're kept for a possible future cloud deployment.

---

## 2. Clone and Install

```bash
git clone <repo-url>
cd ibm-july-challenge
```

### Python environment

```bash
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

If you see `error: Microsoft Visual C++ required`, install the [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) before running pip.

If you have an NVIDIA GPU and want CUDA-accelerated Whisper/Kokoro, install torch with CUDA support **before** `pip install -r requirements.txt` (see the comment at the top of the voice pipeline section in `requirements.txt`):

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### Node environment

```bash
cd frontend
npm install
cd ..
```

---

## 3. Pull the Local Models

Ollama must be installed and running. This project uses **two** Ollama models plus **two** Python-package models that auto-download on first use.

### Granite (text generation — required for everything)

```bash
ollama pull granite3.1-dense:8b
```

### moondream (vision preprocessor — required for the Diagnose tab's image-describe feature)

```bash
ollama pull moondream
```

`src/generation/vision_describer.py` uses moondream (~1.7 GB) to turn a post's image or Reel keyframes into a text `visual_description` that the text-only Granite pipeline can reason over. It's run once per post at sync time, never concurrently with Granite, so an 8 GB GPU is enough for both.

Verify both models loaded:

```bash
ollama list
# Should show: granite3.1-dense:8b and moondream
```

### Voice models (JARVIS widget voice mode) — auto-download, no `ollama pull` needed

- **faster-whisper** (`small` model) for speech-to-text — downloads automatically on first `/api/voice/transcribe` call.
- **Kokoro** for text-to-speech (`bm_fable` voice by default) — downloads to `~/.cache/huggingface/hub/` (~325 MB) on first `/api/voice/synthesize` call.

Both are already pulled in via `pip install -r requirements.txt` (`faster-whisper`, `kokoro`, `soundfile`); the model weights themselves just download lazily the first time you use voice mode. If you have a CUDA GPU it's auto-detected (falls back to CPU otherwise).

The Granite download is ~5 GB, moondream ~1.7 GB. This is Ollama's normal CPU/GPU dispatch — there's no Apple Silicon/Neural Engine special-casing on Windows.

---

## 4. Environment Variables

Copy `.env.example` to `.env` at the project root. Everything except the OAuth block is optional for the local Ollama build (the IBM watsonx credentials are unused; Instaloader/pipeline data loading needs nothing). Full current contents of `.env.example`:

```bash
# IBM watsonx.ai credentials — copy to .env and fill in real values
# Get these from cloud.ibm.com → watsonx.ai → Projects → your project
WATSONX_API_KEY=your_ibm_cloud_api_key_here
WATSONX_PROJECT_ID=your_watsonx_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Instagram Graph API — real-time content ingestion
# Create an app at developers.facebook.com → add "Instagram API with Instagram Login".
# Add your account as an Instagram Tester (dev mode needs no App Review for your own account).
# Each permission (e.g. instagram_business_manage_comments) must also be added/enabled
# under the app's Permissions and Features — requesting it via OAuth scope alone is not
# enough, and reconnecting the account will not grant it if it's missing there.
IG_APP_ID=your_instagram_app_id
IG_APP_SECRET=your_instagram_app_secret
# Must exactly match a redirect URI configured in the Meta app (localhost or your devtunnel origin).
IG_REDIRECT_URI=http://localhost:8000/api/connect/callback
# How often the background poller checks for new posts, in seconds (default 3h).
IG_POLL_INTERVAL_SECS=10800
# Where /callback sends the user back to after connecting (default http://localhost:3000).
FRONTEND_URL=http://localhost:3000
```

The `IG_*` / `FRONTEND_URL` block is only required if you're using the **OAuth Connect** data-loading path (Option D below) instead of Instaloader. See [Section 7](#7-load-brand-data) for the full setup and the Meta App Dashboard permissions gotcha — it's an easy trap.

The frontend reads one variable:

```bash
# frontend/.env.local (auto-created by `npm install`, or create manually)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

If `frontend/.env.local` does not exist, the frontend defaults to `http://localhost:8000` automatically.

---

## 5. Start the Backend

```bash
# From project root, with venv active
uvicorn api.main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

Interactive API docs: `http://localhost:8000/docs`

Health check: `curl http://localhost:8000/api/health` should return `{"status":"ok","service":"StyleSync API"}`.

---

## 6. Start the Frontend

```bash
cd frontend
npm run dev
```

App available at: `http://localhost:3000`

The first load calls `GET /api/onboard/has-profile` to check whether brand data exists:
- If `data/brand_profile.json` exists → redirects to `/create`
- If not → redirects to `/onboard` for first-time setup

---

## 7. Load Brand Data

There are four ways to load data, depending on your situation. Options A–C are the original Instaloader/export pipeline (scrapes a public profile, no login needed). Option D is a real Instagram login via the Business Graph API, giving live sync instead of a one-time scrape.

### Option A — Demo data (fastest, zero setup)

The repository ships with a pre-analyzed @hot_cakesbakes profile:

```
data/demo_brand_profile.json
data/demo_clusters.json
```

Copy them into the active slots:

```powershell
Copy-Item data\demo_brand_profile.json data\brand_profile.json
Copy-Item data\demo_clusters.json data\clusters.json
```

(macOS/Linux: `cp data/demo_brand_profile.json data/brand_profile.json` etc.)

Then visit `http://localhost:3000`. You will be redirected to `/create` immediately.

To reset to the demo at any time from the running app:

```bash
curl -X POST http://localhost:8000/api/onboard/reset-demo
```

### Option B — Onboard via the UI (recommended for new accounts)

1. Visit `http://localhost:3000/onboard`
2. Enter an Instagram username and brand name
3. Click **Analyze My Brand**

The UI shows a progress screen while the backend:
- Scrapes the public profile via Instaloader (~2-5 min for 200 posts)
- Cleans and clusters posts with sentence-transformers + K-Means
- Runs Granite 3.1 to extract brand voice (~8 min)

The total pipeline takes 10-15 minutes on first run. The page polls every 3 seconds and automatically redirects to `/create` when done.

**Note:** The Instagram account must be public. Private accounts return a clear error message. In that case, use Option C.

### Option C — Run the pipeline directly (developers)

```bash
# With venv active, from project root
python run_pipeline.py
```

This uses the account hardcoded in `run_pipeline.py` (`@hot_cakesbakes`). To run for a different account, pass arguments:

```bash
python -c "
from run_pipeline import run_full_pipeline
run_full_pipeline(brand_name='My Brand', handle='@myhandle')
"
```

### Option D — OAuth Connect (real Instagram login, live sync)

Unlike Options A–C, this doesn't scrape a public profile — it authorizes *your own* Instagram Business/Creator account via the Instagram Graph API (`api/routers/connect.py`, `src/scrapers/instagram_api.py`) and keeps it synced with a background poller (`IG_POLL_INTERVAL_SECS`, default 3h).

**1. Create the Meta App**

1. Go to [developers.facebook.com](https://developers.facebook.com) → create an app → add the **"Instagram API with Instagram Login"** product.
2. Under **App Roles → Roles**, add your Instagram account as an **Instagram Tester** and accept the invite from the Instagram app (Settings → Apps and Websites → Tester Invites). Dev mode needs no App Review for your own account.
3. Under the app's **Permissions and Features** page (not just the OAuth `scope=` parameter), explicitly add/enable every permission you need, e.g. `instagram_business_basic`, `instagram_business_manage_comments`, `instagram_business_content_publish`.

> **Gotcha — the #1 way this breaks:** requesting a permission via the OAuth `scope=` parameter is **not enough** on its own. Each permission must *also* be explicitly added and enabled on the app's own **Permissions and Features** dashboard page. If it's missing there, disconnecting and reconnecting the account will **not** grant it — you have to add the permission in the dashboard first, then reconnect. See the note in `.env.example` above the `IG_APP_ID` line.

**2. Configure the redirect URI**

In the Meta app's Instagram product settings, add a redirect URI that **exactly matches** `IG_REDIRECT_URI` in your `.env` — including scheme, host, and path. For local dev this is typically `http://localhost:8000/api/connect/callback`; if you're testing through a devtunnel, use that tunnel's origin instead (see the devtunnel note in [Debugging Guide](debugging.md)).

**3. Set the environment variables**

```bash
IG_APP_ID=your_instagram_app_id
IG_APP_SECRET=your_instagram_app_secret
IG_REDIRECT_URI=http://localhost:8000/api/connect/callback
FRONTEND_URL=http://localhost:3000
```

**4. Connect**

With the backend running, visit `http://localhost:8000/api/connect/login` (or trigger it from the frontend's connect UI). You'll be redirected to Instagram's consent screen, then back to `/callback`, which exchanges the code, saves the token, and kicks off an initial full sync in the background. Check status any time:

```bash
curl http://localhost:8000/api/connect/status
```

To force a re-sync or disconnect:

```bash
curl -X POST http://localhost:8000/api/connect/sync
curl -X POST http://localhost:8000/api/connect/disconnect
```

---

## 8. Verify Everything Works

After loading data, run through this quick checklist:

**Backend health**
```bash
curl http://localhost:8000/api/health
# {"status":"ok","service":"StyleSync API"}

curl http://localhost:8000/api/brand/profile
# Large JSON with brand_name, content_pillars, tone_descriptors, etc.

curl http://localhost:8000/api/onboard/has-profile
# {"has_profile":true,"handle":"@hot_cakesbakes"}
```

**Frontend — Generate tab**
1. Open `http://localhost:3000/app/create` (nav label: "Generate")
2. The sidebar should show the brand name and its discovered content pillars
3. In Caption Brief: enter "Nutella Bomboloni" / "Weekend drop" / "indulgent"
4. Select a cluster and click **Generate Captions**
5. Three captions should appear within ~15 seconds (Granite call)

**Frontend — Strategy tab**
1. Click the **Strategy** tab (`/app/discover`)
2. First load takes 60-120 seconds (two Granite calls cached after that)
3. You should see the Voice Timeline stacked area chart and the Strategic Insights bar chart

If the Strategy tab spins forever, check that Ollama is running (`ollama list`) and that the Granite model is present.

---

## 9. Project Layout Quick Reference

```
ibm-july-challenge/
├── api/                    FastAPI backend
│   ├── main.py             App setup, CORS, router mounting, background poller
│   ├── dependencies.py     @lru_cache generator/agent/model singletons
│   └── routers/
│       ├── onboard.py       Self-serve Instagram onboarding (Instaloader path)
│       ├── connect.py       OAuth Connect — real Instagram Graph API login + sync
│       ├── brand.py         Static brand data reads
│       ├── create.py        Caption / image / script generation
│       ├── analyze.py       Why Engine (post-mortem)
│       ├── discover.py      Voice timeline + strategic insights
│       ├── diagnose.py      Per-post algorithm + Granite diagnosis (vision-assisted)
│       ├── strategy.py      Content strategy metrics
│       ├── today.py         Daily briefing
│       ├── triage.py        Comment triage
│       ├── inbox.py         Comment/DM inbox
│       ├── recovery.py      Recovery brief generation
│       ├── repurpose.py     Content repurposing
│       ├── playbook.py      Playbook agent endpoints
│       ├── weekly_brief.py  Weekly brief planner
│       ├── insights.py      Strategic insights endpoints
│       ├── workbench.py     Workbench / outcomes tracking
│       ├── agent.py         JARVIS widget chat
│       ├── agent_run.py     Single-agent run endpoints
│       ├── orchestrate.py   Multi-agent Orchestrate (needs ChromaDB)
│       └── voice.py         Whisper STT + Kokoro TTS for JARVIS voice mode
│
├── src/
│   ├── data/                pipeline.py (clean/normalize), pillars.py, insights.py,
│   │                        strategy.py, repetition.py, diagnose.py
│   ├── embeddings/          cluster.py (MiniLM + K-Means), profile_extractor.py (Granite brand voice)
│   ├── scrapers/            instaloader_scraper.py (public scrape), instagram_api.py (OAuth + Graph API sync)
│   ├── generation/          ~20 Granite/model invocation modules — caption_generator.py,
│   │                        vision_describer.py (moondream), voice_transcriber.py (faster-whisper),
│   │                        voice_synthesizer.py (Kokoro), why_engine.py, brand_drift.py,
│   │                        brand_guardian.py, comment_triage.py, weekly_brief.py, etc.
│   ├── agents/              Multi-agent Orchestrate system — base.py, orchestrator.py,
│   │                        brand_voice_agent.py, copywriting_agent.py, analytics_agent.py,
│   │                        community_agent.py, critic_agent.py, trend_agent.py,
│   │                        visual_agent.py, playbook_agent.py, autopilot.py
│   └── memory/               ChromaDB-backed agent memory — store.py (semantic/episodic/
│                              procedural collections), outcomes.py
│
├── frontend/               Next.js 16 (App Router)
│   ├── app/app/             8 nav tabs (see components/layout/StudioSidebar.tsx):
│   │                        today, dashboard, brand ("Brand voice"), create ("Generate"),
│   │                        analyze ("Diagnose"), discover ("Strategy"), agents, triage
│   │                        ("Inbox Triage") — plus onboard/ for first-time setup
│   ├── components/         UI components organized by tab (incl. agent/JarvisWidget.tsx)
│   └── lib/                api.ts, types.ts, utils.ts, seedScript.ts
│
├── data/                   Generated outputs (gitignored except demo files)
│   ├── brand_profile.json
│   ├── clusters.json
│   ├── chroma/                    ChromaDB persistence — required for Agents/Autopilot/Orchestrate
│   ├── diagnoses/                 Cached per-post Granite diagnoses (Diagnose tab)
│   ├── demo_brand_profile.json    Committed — used for reset-demo
│   └── demo_clusters.json         Committed — used for reset-demo
│
├── scraped_dataset/        Raw scraped/synced post JSON (gitignored)
├── requirements.txt        Python dependencies
├── .env.example            IBM watsonx + Instagram OAuth variable reference
└── docs/                   You are here
```

---

## Related Documents

- [Architecture](architecture.md) — how the system is structured internally
- [Data Catalog](data-catalog.md) — schemas for every data file
- [Debugging Guide](debugging.md) — common issues and fixes
- [Platform Guide](platform-guide.md) — end-user feature documentation
