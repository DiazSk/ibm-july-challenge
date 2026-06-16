# StyleSync

AI Art Direction for Instagram Creators — built on IBM Granite 3.1 8B.

StyleSync analyzes an Instagram account's posting history and turns it into a living brand voice profile. It then uses that profile to generate on-brand captions, image direction prompts, content scripts, and post-mortem diagnoses — all running locally, with no cloud API required during inference.

Built for the IBM July Challenge.

---

## What It Does

| Tab | What you get |
|-----|-------------|
| **Create** | Blank Page Solver → 3 creative directions → Caption Brief → 3 caption variants + image prompt → Script Studio (Reel / Carousel / Static) |
| **Analyze** | Paste a post + its Instagram Insights metrics → Why Engine diagnosis: what worked, what failed, brand voice gap, what to change |
| **Discover** | Voice Timeline chart (9-month content distribution) + Strategic Insights (volume vs. richness mismatches + strategy brief) |

---

## Quick Start

**Prerequisites:** Python 3.11+, Node 18+, [Ollama](https://ollama.com) installed and running.

```bash
# 1. Python environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Node environment
cd frontend && npm install && cd ..

# 3. Pull the Granite model (one-time, ~5 GB)
ollama pull granite3.1-dense:8b

# 4. Load demo data
cp data/demo_brand_profile.json data/brand_profile.json
cp data/demo_clusters.json data/clusters.json

# 5. Start the stack
uvicorn api.main:app --reload --port 8000 &
cd frontend && npm run dev
```

Open `http://localhost:3000`.

For detailed setup, onboarding your own Instagram account, and verification steps, see [docs/onboarding.md](docs/onboarding.md).

---

## Documentation

| Document | Contents |
|----------|---------|
| [docs/onboarding.md](docs/onboarding.md) | Step-by-step setup, prerequisites, running the stack, loading brand data |
| [docs/architecture.md](docs/architecture.md) | System design, module responsibilities, request flows, caching |
| [docs/data-catalog.md](docs/data-catalog.md) | Schemas for every data file, field reference, data flow |
| [docs/debugging.md](docs/debugging.md) | Common issues and fixes: Ollama, pipeline, Instaloader, frontend |
| [docs/platform-guide.md](docs/platform-guide.md) | End-user guide for all features and content pillars |

---

## Stack

**Backend:** FastAPI · Ollama (IBM Granite 3.1 8B) · LangChain · sentence-transformers · scikit-learn · Instaloader  
**Frontend:** Next.js 16 · React 19 · TypeScript · Tailwind CSS · React Query  
**Model:** `granite3.1-dense:8b` — 9 Granite invocations, all local

---

## API

Interactive docs at `http://localhost:8000/docs` once the backend is running.

Key endpoints:

```
GET  /api/health
GET  /api/onboard/has-profile
POST /api/onboard/start           {handle, brand_name}
GET  /api/onboard/status/{job_id}
POST /api/onboard/reset-demo

GET  /api/brand/profile
GET  /api/brand/clusters

POST /api/create/analyze-moment
POST /api/create/directions
POST /api/create/captions
POST /api/create/image-prompt
POST /api/create/script

POST /api/analyze/why-engine

GET  /api/discover/voice-timeline
GET  /api/discover/strategic-insights
```
