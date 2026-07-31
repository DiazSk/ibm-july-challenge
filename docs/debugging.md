# StyleSync — Debugging Guide

A reference for the most common issues encountered when developing or running StyleSync. Issues are grouped by layer.

The current dev environment is **Windows** (PowerShell). Commands below use `curl.exe` (the real curl binary bundled with Windows 10/11 — not the `Invoke-WebRequest` alias that plain `curl` resolves to inside PowerShell), `netstat`/`taskkill` for port conflicts, and PowerShell equivalents where relevant.

---

## Table of Contents

1. [Ollama / Granite / Vision Issues](#1-ollama--granite--vision-issues)
2. [Backend (FastAPI) Issues](#2-backend-fastapi-issues)
3. [Pipeline Issues](#3-pipeline-issues)
4. [Onboarding / Instagram Integration Issues](#4-onboarding--instagram-integration-issues)
5. [Frontend Issues](#5-frontend-issues)
6. [Agent Memory (ChromaDB) Issues](#6-agent-memory-chromadb-issues)
7. [Voice Pipeline Issues](#7-voice-pipeline-issues)
8. [Data Issues](#8-data-issues)
9. [Performance Issues](#9-performance-issues)
10. [Diagnostic Commands](#10-diagnostic-commands)

---

## 1. Ollama / Granite / Vision Issues

### "Connection refused" when calling any generation endpoint

**Symptom:** Caption generation, Why Engine, or Discover tab hangs or returns a 500 error. Backend logs show `httpx.ConnectError: Connection refused` or similar.

**Cause:** Ollama is not running.

**Fix:**
```powershell
ollama serve        # start in a separate terminal
# or launch the Ollama app from the Start Menu — it runs as a system-tray app on Windows
```

Verify:
```powershell
curl.exe http://localhost:11434/api/version
# {"version":"..."}
```

---

### "model 'granite3.1-dense:8b' not found"

**Symptom:** Generation endpoints return 500. Backend logs show `model not found` from Ollama.

**Fix:**
```powershell
ollama pull granite3.1-dense:8b
```

Verify:
```powershell
ollama list
# granite3.1-dense:8b   ...   4.9 GB
```

---

### Granite returns garbled JSON or empty strings

**Symptom:** Caption variants are empty, or the Why Engine returns a blank diagnosis. Backend logs may show JSON parse errors.

**Cause:** The model output was truncated (ran out of context) or the prompt engineering assumptions were violated.

**Fix — verify the model is fully loaded:**
```powershell
ollama run granite3.1-dense:8b "Say hello."
```

If the response is garbled, stop and restart Ollama (see below) — memory pressure from other running apps can corrupt inference.

**Fix — check for token limit issues:** Each generation module has a fixed `num_predict` parameter. If you modified prompt templates to be much longer, the output may be truncated. Reduce prompt length or increase `num_predict` in the relevant `src/generation/*.py` file.

---

### Ollama is very slow (>60s per response)

**Cause:** The model is running in CPU-only mode instead of on the GPU.

**Diagnosis:**
```powershell
# During a Granite call, in another terminal:
ollama ps
# Should show: granite3.1-dense:8b  ... 100% GPU
# If it shows 0% GPU, Ollama fell back to CPU
```

Also check the GPU is actually visible to Ollama:
```powershell
nvidia-smi
# Confirms the driver is loaded and shows current VRAM usage
```

**Fix:** Restart Ollama — right-click the Ollama icon in the system tray, choose Quit, then relaunch it (or run `ollama serve` again in a terminal). A stuck Ollama process can pin itself to CPU until restarted; on Windows, Ollama uses CUDA (NVIDIA) or ROCm (AMD) rather than Apple's Metal/Neural Engine, so if `nvidia-smi` shows no processes while a model is loaded, the GPU driver or CUDA toolkit needs attention rather than Ollama itself.

---

### Vision model (moondream) missing or failing

**Symptom:** The Diagnose page's Manual tab image-upload/describe feature fails or returns empty output, while text-only caption generation (Granite) still works fine. This is a distinct model from Granite, so a working chat completion does **not** mean vision is set up.

**Cause:** `src/generation/vision_describer.py` calls the local `ollama` client directly with `VISION_MODEL = "moondream"` (see `vision_describer.py:40`). If `moondream` isn't pulled, every call to `VisionDescriber.describe()` / `describe_bytes()` fails.

**Fix:**
```powershell
ollama pull moondream
```

Verify with the module's own self-check (needs `moondream` pulled + Ollama running):
```powershell
python -m src.generation.vision_describer
# OK — vision self-check passed: ...
```

**Note:** `moondream` only accepts one image per call — three images in one request returns a bounding box instead of a description, so `vision_describer.py` sends one frame per request and assembles the results. If you see one merged/garbled description instead of per-frame text for a Reel, that's this constraint, not a bug to "fix" by batching images.

A wedged vision runner emits runs of `"!!!!"` instead of real text; `_ask()` in `vision_describer.py` already strips and rejects mostly-`!` output, so a `visual_description` full of `!` in `data/` JSON means the batch ran before that guard existed — rerun `backfill_descriptions(..., force=True)` to regenerate it.

---

## 2. Backend (FastAPI) Issues

### "Module not found: fastapi" when starting uvicorn

**Cause:** The virtual environment is not activated.

**Fix:**
```powershell
venv\Scripts\Activate.ps1        # PowerShell
# or: venv\Scripts\activate.bat  # cmd.exe
uvicorn api.main:app --reload --port 8000
```

---

### "Form data requires python-multipart to be installed"

**Symptom:** The backend crashes at startup with a `RuntimeError` about `python-multipart`.

**Cause:** The `/api/onboard/upload` endpoint uses `Form(...)` and `UploadFile`, which require this package.

**Fix:**
```powershell
pip install python-multipart
```

This package is now in `requirements.txt`. If you cloned before it was added, reinstall:
```powershell
pip install -r requirements.txt
```

---

### Port 8000 already in use

**Symptom:** `uvicorn` fails with `[Errno 10048] error while attempting to bind on address` (Windows' equivalent of "Address already in use").

**Fix:**
```powershell
# Find the process using port 8000
netstat -ano | findstr :8000
# Last column is the PID — kill it
taskkill /PID <pid> /F
```

Or run on a different port:
```powershell
uvicorn api.main:app --reload --port 8001
# Then update frontend/.env.local: NEXT_PUBLIC_API_URL=http://localhost:8001
```

---

### CORS errors in browser console

**Symptom:** Browser shows `Access to fetch at 'http://localhost:8000' from origin 'http://localhost:3000' has been blocked by CORS policy`.

**Cause:** The backend CORS whitelist in `api/main.py` only includes `http://localhost:3000` and `http://127.0.0.1:3000`. If you're accessing the frontend from a different port or host, it will be blocked.

**Fix — for development only, edit `api/main.py`:**
```python
allow_origins = ["*"]   # development only
```

Or add your origin to the explicit list.

---

### `/api/brand/profile` returns 500 after onboarding

**Cause:** `data/brand_profile.json` was written but is malformed JSON (pipeline crashed mid-write).

**Fix:**
```powershell
# Check the file
python -c "import json; json.load(open('data/brand_profile.json'))"
# If this throws a JSONDecodeError, restore the demo:
copy data\demo_brand_profile.json data\brand_profile.json
copy data\demo_clusters.json data\clusters.json
```

---

### Discover tab serves stale data after onboarding a new account

**Cause:** `_compute_voice_timeline` and `_compute_strategic_insights` in `api/routers/discover.py` are `@lru_cache` and loaded data at startup. The onboarding pipeline calls `_clear_caches()` which should clear them, but if the pipeline was run outside the API (e.g. `python run_pipeline.py` from the terminal), caches won't be cleared.

**Fix:** Restart the uvicorn server. All `@lru_cache` caches reset on restart.

Or, without restarting, call:
```powershell
curl.exe -X POST http://localhost:8000/api/onboard/reset-demo
# This clears all caches as a side effect, then loads demo data.
# Alternatively, onboard the new account through the UI — the pipeline clears caches on completion.
```

---

## 3. Pipeline Issues

### "No posts with usable captions found"

**Symptom:** The onboarding pipeline fails at Stage 1 with this error.

**Cause:** Either no JSON files are in `scraped_dataset/`, all captions are empty (image-only posts), or the scraper wrote files in an unexpected format.

**Diagnosis:**
```powershell
(Get-ChildItem scraped_dataset\ig_text_*.json).Count   # should be > 0
python -c "
import json, glob
for f in glob.glob('scraped_dataset/ig_text_*.json')[:3]:
    d = json.load(open(f))
    print(d.get('content', {}).get('caption_raw', '(empty)')[:80])
"
```

**Fix — if files are missing:** Re-run the scraper or re-upload the export ZIP.

**Fix — if captions are all empty:** The account may post images without captions. `pipeline.py` skips posts with empty `caption_raw`. There is currently no workaround — the pipeline requires text content.

---

### "ValueError: n_samples=X should be >= n_clusters=5" during clustering

**Symptom:** Stage 2 clustering fails with this scikit-learn error.

**Cause:** Fewer than 5 posts made it through pipeline Stage 1. K-Means with k=5 requires at least 5 samples.

**Fix — reduce k:** Edit `src/embeddings/cluster.py`:
```python
N_CLUSTERS = min(5, len(texts))   # add this guard
```

Or use more posts (the pipeline requires at least 5 captioned posts).

---

### Pipeline output files not written

**Symptom:** `data/brand_profile.json` or `data/clusters.json` don't exist after the pipeline completes.

**Fix — check for exceptions:**
```powershell
python run_pipeline.py 2>&1 | Select-Object -Last 30
```

Common causes:
- Ollama not running (Granite call fails during Stage 3)
- Write permission denied to `data/` directory
- `data/` directory doesn't exist: `New-Item -ItemType Directory -Force data`

---

## 4. Onboarding / Instagram Integration Issues

### "@handle doesn't exist on Instagram"

**Cause:** The username was typed incorrectly, or the account was deleted/renamed.

**Fix:** Verify the handle exists by visiting `instagram.com/<handle>` in a browser.

---

### "@handle is a private account"

**Cause:** Instaloader cannot scrape private profiles without login credentials, and StyleSync does not support authenticated sessions.

**Fix:** Direct the user to use the Instagram data export option instead:
1. Instagram → Settings → Your activity → Download your information
2. Select Posts & Reels, JSON format
3. Wait for the download email (can take up to 48 hours)
4. Upload the ZIP on the onboarding page

---

### "Too many requests" / Instaloader rate limit

**Symptom:** The onboarding job stops at 10-15% with an error like `TooManyRequestsException` or `Please wait a few minutes before you try again`.

**Cause:** Instagram rate-limits anonymous Instaloader requests. This is more likely on high-frequency accounts (>500 posts) or when the same IP address makes repeated requests.

**Fix — wait and retry:** Instagram rate limits typically lift after 15-30 minutes.

**Fix — use fewer posts:** The scraper caps at 200 posts by default. For testing, use a smaller account.

**Fix — use data export:** For production use on large accounts, the ZIP export path bypasses scraping entirely.

---

### Job appears stuck at a progress percentage

**Cause:** The background task is running but the stage takes a long time (Granite brand voice extraction can take 8+ minutes on first run).

**Fix:** Check the backend logs in the terminal where uvicorn is running. You should see Granite invocation output scrolling. If there is no output for 10 minutes, Ollama may have crashed — restart it and try again.

Typical stage durations:
- Instaloader scraping (200 posts): 2-5 minutes
- Caption cleaning (Stage 1): <10 seconds
- K-Means clustering (Stage 2): 30-90 seconds
- Granite brand voice extraction (Stage 3): 6-12 minutes

---

### Onboarding completes but data looks like the old account

**Cause:** LRU caches from the previous session are still active. This should not happen if you used the UI (the pipeline calls `_clear_caches()` on completion), but can happen if:
- You ran the pipeline directly from the terminal
- You replaced the JSON files manually without clearing caches

**Fix:** Restart the uvicorn server.

---

### Reconnecting Instagram doesn't fix "Instagram didn't grant comment access"

**Symptom:** The Inbox/Triage page's `/api/inbox/comments` call 403s with a message about missing comment access — even right after a successful OAuth reconnect where `granted_permissions` in `data/ig_connection.json` clearly lists `instagram_business_manage_comments`. Re-clicking "Reconnect Instagram" doesn't change anything.

**Cause:** This looks like a stale-token bug but isn't. `api/routers/inbox.py`'s `comments()` endpoint (`api/routers/inbox.py:41-57`) catches a `PermissionError` (or a 400/403 HTTP error) from `fetch_recent_comments()` and raises a 403 with a fixed message (`_RECONNECT_MSG`, `api/routers/inbox.py:24-30`):

> "Instagram isn't returning comment access, even though your account already consented to `instagram_business_manage_comments` — reconnecting won't change that. In your Meta App Dashboard, open the app's Instagram product → Permissions and Features, and confirm `instagram_business_manage_comments` is added/enabled there (and has completed App Review/Business Verification if Advanced Access is required)."

The consent screen at OAuth time granting a scope (what shows up in `granted_permissions`) is a **separate thing** from that permission being enabled under Advanced Access in the Meta App Dashboard's own "Permissions and Features" tab. If the app hasn't completed App Review / Business Verification for that permission, Meta's Graph API will keep rejecting the call no matter how many times the user reconnects — the token already has the scope it can get.

**Fix:** This is not fixable from inside StyleSync. Go to the Meta App Dashboard for the connected app → Instagram product → Permissions and Features, and confirm `instagram_business_manage_comments` is listed as enabled/Advanced Access (completing App Review/Business Verification if required). Reconnecting the account in StyleSync after that dashboard change will pick up a working token; reconnecting before that change is a no-op.

**Diagnosis — confirm which side of the fence you're on:**
```powershell
python -c "import json; print(json.load(open('data/ig_connection.json')).get('granted_permissions'))"
```
If `instagram_business_manage_comments` is already in that list and you still get the 403, it's the Meta Dashboard side, not a StyleSync bug or a stale token.

---

## 5. Frontend Issues

### `npm run build` fails with TypeScript errors

**Symptom:** Build exits with type errors.

**Fix — check for missing type declarations:**
```powershell
cd frontend
npx tsc --noEmit 2>&1 | Select-Object -First 40
```

Common causes:
- A new field was added to a backend response but not added to `frontend/lib/types.ts`
- A component imports a type that was removed

---

### Port 3000 already in use

```powershell
netstat -ano | findstr :3000
taskkill /PID <pid> /F
# or run on a different port:
npm run dev -- -p 3001
```

---

### "Failed to fetch" on every API call

**Cause:** The frontend cannot reach the backend. Most common causes:
1. Backend is not running — start uvicorn
2. Wrong `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
3. CORS issue (see Backend section above)

**Diagnosis:**
```powershell
curl.exe http://localhost:8000/api/health
```

If this succeeds but the browser still shows errors, open browser DevTools → Network → look for the failing request → check the Response tab for the actual error.

---

### Testing through a devtunnel instead of localhost

**Symptom:** The app works fine at `localhost:3000`, but through a VS Code devtunnel (or similar port-forwarding origin) some requests intermittently fail or time out — usually the slower Granite-backed calls (Guardian, Resonance, Autopilot), while fast static reads succeed.

**Cause:** Devtunnels add their own proxy hop with a shorter idle/response timeout than a direct localhost connection. A Granite call that legitimately takes 60-90+ seconds (see the Performance section on concurrent-load slowness) can get cut off by the tunnel well before the backend actually errors — the backend is still working, the tunnel just gave up waiting.

**Fix:** For any development or debugging work, verify directly against `http://localhost:8000` and `http://localhost:3000` rather than through the tunnel origin. `api/main.py`'s CORS allowlist does include a `*.devtunnels.ms` regex so the tunnel origin isn't blocked outright — but a 504-style failure through the tunnel on a slow call doesn't mean the feature is broken, only that the tunnel timed out. Reproduce against localhost before concluding there's a real bug.

---

### Onboarding page not covering the sidebar

**Symptom:** The onboard page renders behind the sidebar layout instead of on top.

**Cause:** The `FullScreen` wrapper in `frontend/app/onboard/page.tsx` uses `z-50`. If the sidebar has a higher z-index, it will overlap.

**Fix — check the root layout's sidebar z-index:**
```powershell
Select-String -Path frontend\app\layout.tsx, frontend\components\layout\Sidebar.tsx -Pattern "z-"
```

Increase the onboard page's z-index if needed (`z-[100]` instead of `z-50`).

---

### Autopilot / Agents live trace looks frozen, but the job is actually still running

**Symptom:** On `/app/agents`, the live reasoning trace stops updating even though the underlying job hasn't errored. Switching to another tab/window and coming back later shows the trace jumped forward all at once, or it stays stuck until you refresh.

**Cause:** This page polls with TanStack Query's `useQuery({ refetchInterval: ... })` (`frontend/app/app/agents/page.tsx:54-63` for the agent run, and `:349-350` for a second polling query). By default, TanStack Query **pauses `refetchInterval` whenever `document.visibilityState !== 'visible'`** — i.e. whenever the tab isn't focused/foregrounded. Without `refetchIntervalInBackground: true`, a job that's actively running server-side will silently stop being polled the moment the tab loses focus, and the UI looks frozen even though nothing is wrong.

Both `useQuery` calls on this page already set `refetchIntervalInBackground: true` (confirmed at `agents/page.tsx:62` and `:350`), so if you see this bug reappear, check whether a newly-added `useQuery({ refetchInterval: ... })` elsewhere in the codebase is missing that flag — that's the actual root cause, not a backend issue.

**General lesson for this codebase:** any `useQuery` with `refetchInterval` needs `refetchIntervalInBackground: true`, or polling silently stops in a backgrounded tab. Contrast with the Dashboard's Weekly Brief panel (`frontend/app/app/dashboard/page.tsx:153-179`) and its Instagram-sync polling (`:111-146`), which sidestep this entirely by using a manual `setInterval`/`clearInterval` inside a `useEffect` instead of TanStack's `refetchInterval` — plain `setInterval` keeps firing regardless of tab visibility. If a new polling need comes up, either pattern is fine as long as `refetchIntervalInBackground` isn't forgotten on the TanStack path.

---

## 6. Agent Memory (ChromaDB) Issues

StyleSync's agents (Autopilot, orchestrator-driven caption generation, Trend/Playbook agents) share a three-collection ChromaDB store — `AgentMemoryStore` (`src/memory/store.py`), backing `semantic` / `episodic` / `procedural` collections persisted at `data/chroma/`. It's wired up as a singleton via `get_memory_store()` (`api/dependencies.py`, `@lru_cache(maxsize=1)`), which `/api/orchestrate` and the Autopilot start endpoint both depend on through FastAPI's `Depends(get_memory_store)`.

### `/api/orchestrate` or Autopilot ("Agent Run") fails immediately with a Chroma/sqlite error

**Cause:** `AgentMemoryStore.__init__` (`src/memory/store.py:100-130`) does `Path(persist_dir).mkdir(parents=True, exist_ok=True)` and then constructs `chromadb.PersistentClient(path=self.persist_dir, ...)`. There is **no try/except anywhere in this path** — not in `AgentMemoryStore.__init__`, not in `get_memory_store()`, not in the router. If `data/chroma/` exists but its internal sqlite file is corrupted (e.g. the process was killed mid-write, or the directory was copied while Chroma had it open), `chromadb.PersistentClient(...)` raises, and that exception propagates straight up through `Depends(get_memory_store)` into an unhandled 500 for both `/api/orchestrate` and `/api/agent-run/start`.

A **missing** `data/chroma/` directory is not the problem — `mkdir(parents=True, exist_ok=True)` recreates it automatically and `get_or_create_collection` seeds fresh empty collections (procedural rules are reseeded immediately via `_seed_procedural_rules()`, `src/memory/store.py:130`). It's specifically a *corrupted-but-present* directory that hard-fails with no fallback.

**Diagnosis:**
```powershell
Test-Path data\chroma
curl.exe http://localhost:8000/api/orchestrate/memory-status
# {"semantic": N, "episodic": N, "procedural": N} on success;
# a 500 here with the backend traceback pointing at chromadb confirms a corrupted store.
```

**Fix:** Stop uvicorn, then rename/delete the corrupted directory and restart:
```powershell
Rename-Item data\chroma data\chroma.bak
uvicorn api.main:app --reload --port 8000
```
Procedural rules reseed automatically on the next `AgentMemoryStore()` construction. Semantic (brand voice) and episodic (campaign outcome) memory rebuild as normal usage continues — re-onboarding/re-running the brand voice pipeline repopulates semantic memory, and new Autopilot/caption runs repopulate episodic memory. You lose whatever accumulated episodic learning history was in the corrupted store; there's no separate backup mechanism for `data/chroma/`, so back it up yourself before an experiment if that history matters.

---

## 7. Voice Pipeline Issues

The JARVIS widget's voice mode uses `faster-whisper` for speech-to-text (`src/generation/voice_transcriber.py`) and Kokoro for text-to-speech (`src/generation/voice_synthesizer.py`).

### First voice interaction hangs or takes a long time

**Cause:** This is very likely a one-time model download, not a hang. Kokoro's `KPipeline` auto-downloads its weights to `~/.cache/huggingface/hub/` (~325 MB) on first use (`voice_synthesizer.py:11`), and `faster-whisper`'s `WhisperModel` similarly downloads the `small` model on first construction. On a normal connection this can take anywhere from several seconds to a couple of minutes depending on bandwidth, during which the JARVIS widget has nothing to show yet.

**Fix:** Wait it out on first use — check the backend terminal for download progress/output. Subsequent voice interactions are fast (`faster-whisper`: ~80ms/clip on CUDA, ~300-600ms on CPU; Kokoro: ~100ms on CUDA, ~300-500ms on CPU — see the docstrings in both files). If it's still stuck after a few minutes with no backend output at all, check your network connection to Hugging Face rather than assuming StyleSync itself is broken.

**Diagnosis — confirm the cache actually populated:**
```powershell
Get-ChildItem "$env:USERPROFILE\.cache\huggingface\hub" -ErrorAction SilentlyContinue
```

---

## 8. Data Issues

### `brand_profile.json` schema mismatch after manual edits

**Symptom:** The sidebar shows `undefined` for brand name, or the cluster dropdown is empty.

**Cause:** Manual edits broke the expected JSON structure.

**Fix:** Restore from demo and re-run onboarding, or validate against the schema in [Data Catalog](data-catalog.md).

---

### `clusters.json` has no `sample_captions`

**Symptom:** The cluster detail cards on the Create page show no sample captions.

**Cause:** An older version of the clustering pipeline didn't write `sample_captions`. The `GET /api/brand/clusters` endpoint merges cluster profiles from `brand_profile.json` with raw post data from `clusters.json` — if `clusters.json` was generated by an older pipeline, the merge may produce empty arrays.

**Fix:** Re-run the clustering stage:
```powershell
python -c "from src.embeddings.cluster import run_clustering; run_clustering()"
```

---

## 9. Performance Issues

### Discover tab takes >5 minutes on every load

**Cause:** The `@lru_cache` is not working — caches are being cleared between requests.

**Diagnosis:** Look for calls to `cache_clear()` anywhere in your working copy:
```powershell
Select-String -Path api\**\*.py -Pattern "cache_clear"
```

If `_clear_caches()` is being called on every request (instead of only after onboarding), that's the bug.

---

### Caption generation takes >60 seconds

**Cause:** The Granite model may be swapping to disk due to memory pressure.

**Fix — check RAM/GPU usage:**
```powershell
# Overall memory
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10 Name, @{n="RAM(MB)";e={[math]::Round($_.WorkingSet/1MB)}}
# GPU (if applicable)
nvidia-smi
```
Or just open Task Manager → Performance tab.

Close other memory-heavy applications (browser tabs, Docker Desktop) and retry. Granite 3.1 8B needs at least 8 GB of available memory for comfortable inference.

---

### Everything is suddenly slow — Granite calls taking 60-90+ seconds instead of the usual 10-20s

**Cause:** Multiple heavy AI jobs running at once. An Instagram sync (Instaloader + vision backfill), an Autopilot run, and interactive caption generation all compete for the same CPU/GPU and RAM, and Ollama, `faster-whisper`, Kokoro, and the sentence-transformers embedder can all be resident in memory simultaneously. This is local resource contention, not a bug — a single Granite call that normally takes 10-20s can stretch to 60-90+ seconds when 2-3 of these are running concurrently.

**Fix:** There's no code fix for this — it's a hardware ceiling. If it matters for a demo or timed test, avoid kicking off a sync/Autopilot run while also generating captions interactively; let heavy background jobs (sync, Autopilot, vision backfill) finish before starting another one. `ollama ps` and Task Manager will show whether Ollama and other processes are actively competing for the GPU/CPU at the same time.

---

## 10. Diagnostic Commands

Quick reference for common checks:

```powershell
# Is Ollama running and Granite available?
ollama list | Select-String granite

# Is the vision model (moondream) available?
ollama list | Select-String moondream

# Is the backend healthy?
curl.exe -s http://localhost:8000/api/health | python -m json.tool

# Does brand data exist?
curl.exe -s http://localhost:8000/api/onboard/has-profile | python -m json.tool

# What's in the brand profile?
(curl.exe -s http://localhost:8000/api/brand/profile | python -m json.tool) | Select-Object -First 40

# What clusters are loaded?
(curl.exe -s http://localhost:8000/api/brand/clusters | python -m json.tool) | Select-Object -First 40

# Agent memory (ChromaDB) collection counts
curl.exe -s http://localhost:8000/api/orchestrate/memory-status | python -m json.tool

# Does the ChromaDB persist directory exist (and is it non-empty)?
Test-Path data\chroma
Get-ChildItem data\chroma -ErrorAction SilentlyContinue

# Is Instagram connected, and which permissions were actually granted?
python -c "import json; c=json.load(open('data/ig_connection.json')); print(c.get('username'), c.get('granted_permissions'))"

# How many scraped posts are there?
(Get-ChildItem scraped_dataset\ig_text_*.json -ErrorAction SilentlyContinue).Count

# How many cleaned records exist?
(Get-ChildItem data\cleaned\*.json -ErrorAction SilentlyContinue).Count

# Validate JSON files
python -c "import json; json.load(open('data/brand_profile.json')); print('brand_profile.json OK')"
python -c "import json; json.load(open('data/clusters.json')); print('clusters.json OK')"

# Is a port already in use? (replace 8000 with 3000 for the frontend)
netstat -ano | findstr :8000

# GPU status for Ollama / faster-whisper / Kokoro
nvidia-smi

# Full stack quick-test (requires venv active and uvicorn running)
python -c "
import urllib.request, json
for path in ['/api/health', '/api/onboard/has-profile', '/api/brand/profile']:
    r = urllib.request.urlopen(f'http://localhost:8000{path}')
    data = json.loads(r.read())
    print(f'{path}: OK ({list(data.keys())})')
"
```
