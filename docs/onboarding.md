# StyleSync — Developer Onboarding

This guide takes you from a fresh clone to a fully running StyleSync stack. It covers prerequisites, installation, first-run verification, and the two paths for loading brand data.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Clone and Install](#2-clone-and-install)
3. [Pull the Granite Model](#3-pull-the-granite-model)
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
| Python | 3.11+ | 3.14 tested; 3.11 and 3.12 work fine |
| Node.js | 18+ | 20 LTS recommended |
| RAM | 16 GB | Granite 3.1 8B loads ~6 GB into unified memory |
| Storage | 10 GB free | Ollama model + embeddings + venv |
| Ollama | Any recent | Must be running before the backend starts |

Granite runs locally via Ollama. There is no cloud inference required — the `.env` IBM credentials are unused in the current build (Ollama replaces cloud inference for the IBM challenge demo).

---

## 2. Clone and Install

```bash
git clone <repo-url>
cd ibm-july-challenge
```

### Python environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

If you see `error: Microsoft Visual C++ required` on Windows, install the [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) before running pip.

### Node environment

```bash
cd frontend
npm install
cd ..
```

---

## 3. Pull the Granite Model

Ollama must be installed and running. Pull the model once:

```bash
ollama pull granite3.1-dense:8b
```

Verify it loaded:

```bash
ollama list
# Should show: granite3.1-dense:8b
```

The download is ~5 GB. On Apple Silicon, Ollama automatically offloads to the Neural Engine — no GPU required.

---

## 4. Environment Variables

The `.env.example` at the project root shows the available variables. For the local Ollama build, none are required:

```bash
# No .env file needed for Ollama-based local inference.
# The .env.example shows IBM watsonx.ai credentials for a future cloud deployment.
```

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

There are three ways to load data, depending on your situation.

### Option A — Demo data (fastest, zero setup)

The repository ships with a pre-analyzed @hot_cakesbakes profile:

```
data/demo_brand_profile.json
data/demo_clusters.json
```

Copy them into the active slots:

```bash
cp data/demo_brand_profile.json data/brand_profile.json
cp data/demo_clusters.json data/clusters.json
```

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

**Frontend — Create tab**
1. Open `http://localhost:3000/create`
2. The sidebar should show the brand name and 5 content pillars
3. In Caption Brief: enter "Nutella Bomboloni" / "Weekend drop" / "indulgent"
4. Select a cluster and click **Generate Captions**
5. Three captions should appear within ~15 seconds (Granite call)

**Frontend — Discover tab**
1. Click the **Discover** tab
2. First load takes 60-120 seconds (two Granite calls cached after that)
3. You should see the Voice Timeline stacked area chart and the Strategic Insights bar chart

If the Discover tab spins forever, check that Ollama is running (`ollama list`) and that the Granite model is present.

---

## 9. Project Layout Quick Reference

```
ibm-july-challenge/
├── api/                    FastAPI backend
│   ├── main.py             App setup, CORS, router mounting
│   ├── dependencies.py     @lru_cache generator singletons
│   └── routers/
│       ├── onboard.py      Self-serve Instagram onboarding
│       ├── brand.py        Static brand data reads
│       ├── create.py       Caption / image / script generation
│       ├── analyze.py      Why Engine (post-mortem)
│       └── discover.py     Voice timeline + strategic insights
│
├── src/
│   ├── data/pipeline.py          Stage 1: clean + normalize captions
│   ├── embeddings/cluster.py     Stage 2: MiniLM embeddings + K-Means
│   ├── embeddings/profile_extractor.py  Stage 3: Granite brand voice
│   ├── scrapers/instaloader_scraper.py  Instaloader public profile scraper
│   └── generation/               9 Granite invocation modules
│
├── frontend/               Next.js 16 (App Router)
│   ├── app/                Pages: /, /onboard, /create, /analyze, /discover
│   ├── components/         UI components organized by tab
│   └── lib/                api.ts, types.ts, utils.ts
│
├── data/                   Generated outputs (gitignored except demo files)
│   ├── brand_profile.json
│   ├── clusters.json
│   ├── demo_brand_profile.json   Committed — used for reset-demo
│   └── demo_clusters.json        Committed — used for reset-demo
│
├── scraped_dataset/        Raw scraped post JSON (gitignored)
├── requirements.txt        Python dependencies
└── docs/                   You are here
```

---

## Related Documents

- [Architecture](architecture.md) — how the system is structured internally
- [Data Catalog](data-catalog.md) — schemas for every data file
- [Debugging Guide](debugging.md) — common issues and fixes
- [Platform Guide](platform-guide.md) — end-user feature documentation
