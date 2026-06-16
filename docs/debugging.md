# StyleSync — Debugging Guide

A reference for the most common issues encountered when developing or running StyleSync. Issues are grouped by layer.

---

## Table of Contents

1. [Ollama / Granite Issues](#1-ollama--granite-issues)
2. [Backend (FastAPI) Issues](#2-backend-fastapi-issues)
3. [Pipeline Issues](#3-pipeline-issues)
4. [Onboarding / Instaloader Issues](#4-onboarding--instaloader-issues)
5. [Frontend Issues](#5-frontend-issues)
6. [Data Issues](#6-data-issues)
7. [Performance Issues](#7-performance-issues)
8. [Diagnostic Commands](#8-diagnostic-commands)

---

## 1. Ollama / Granite Issues

### "Connection refused" when calling any generation endpoint

**Symptom:** Caption generation, Why Engine, or Discover tab hangs or returns a 500 error. Backend logs show `httpx.ConnectError: Connection refused` or similar.

**Cause:** Ollama is not running.

**Fix:**
```bash
ollama serve        # start in a separate terminal
# or on macOS, open the Ollama app from Applications
```

Verify:
```bash
curl http://localhost:11434/api/version
# {"version":"..."}
```

---

### "model 'granite3.1-dense:8b' not found"

**Symptom:** Generation endpoints return 500. Backend logs show `model not found` from Ollama.

**Fix:**
```bash
ollama pull granite3.1-dense:8b
```

Verify:
```bash
ollama list
# granite3.1-dense:8b   ...   4.9 GB
```

---

### Granite returns garbled JSON or empty strings

**Symptom:** Caption variants are empty, or the Why Engine returns a blank diagnosis. Backend logs may show JSON parse errors.

**Cause:** The model output was truncated (ran out of context) or the prompt engineering assumptions were violated.

**Fix — verify the model is fully loaded:**
```bash
ollama run granite3.1-dense:8b "Say hello."
```

If the response is garbled, stop and restart Ollama. On Apple Silicon, unified memory pressure from other apps can corrupt inference.

**Fix — check for token limit issues:** Each generation module has a fixed `num_predict` parameter. If you modified prompt templates to be much longer, the output may be truncated. Reduce prompt length or increase `num_predict` in the relevant `src/generation/*.py` file.

---

### Ollama is very slow (>60s per response)

**Cause:** The model is running in CPU-only mode instead of Apple Silicon GPU/Neural Engine.

**Diagnosis:**
```bash
# During a Granite call, in another terminal:
ollama ps
# Should show: granite3.1-dense:8b  ... 100% GPU
# If it shows 0% GPU, Ollama is not using the Neural Engine
```

**Fix:** Restart Ollama. On macOS, quit the menu bar app completely and reopen it. The `METAL` backend should activate automatically on Apple Silicon.

---

## 2. Backend (FastAPI) Issues

### "Module not found: fastapi" when starting uvicorn

**Cause:** The virtual environment is not activated.

**Fix:**
```bash
source venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

---

### "Form data requires python-multipart to be installed"

**Symptom:** The backend crashes at startup with a `RuntimeError` about `python-multipart`.

**Cause:** The `/api/onboard/upload` endpoint uses `Form(...)` and `UploadFile`, which require this package.

**Fix:**
```bash
pip install python-multipart
```

This package is now in `requirements.txt`. If you cloned before it was added, reinstall:
```bash
pip install -r requirements.txt
```

---

### Port 8000 already in use

**Symptom:** `uvicorn` fails with `[Errno 48] Address already in use`.

**Fix:**
```bash
# Find the process using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
```

Or run on a different port:
```bash
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
```bash
# Check the file
python3 -c "import json; json.load(open('data/brand_profile.json'))"
# If this throws a JSONDecodeError, restore the demo:
cp data/demo_brand_profile.json data/brand_profile.json
cp data/demo_clusters.json data/clusters.json
```

---

### Discover tab serves stale data after onboarding a new account

**Cause:** `_compute_voice_timeline` and `_compute_strategic_insights` in `api/routers/discover.py` are `@lru_cache` and loaded data at startup. The onboarding pipeline calls `_clear_caches()` which should clear them, but if the pipeline was run outside the API (e.g. `python run_pipeline.py` from the terminal), caches won't be cleared.

**Fix:** Restart the uvicorn server. All `@lru_cache` caches reset on restart.

Or, without restarting, call:
```bash
curl -X POST http://localhost:8000/api/onboard/reset-demo
# This clears all caches as a side effect, then loads demo data.
# Alternatively, onboard the new account through the UI — the pipeline clears caches on completion.
```

---

## 3. Pipeline Issues

### "No posts with usable captions found"

**Symptom:** The onboarding pipeline fails at Stage 1 with this error.

**Cause:** Either no JSON files are in `scraped_dataset/`, all captions are empty (image-only posts), or the scraper wrote files in an unexpected format.

**Diagnosis:**
```bash
ls scraped_dataset/ig_text_*.json | wc -l   # should be > 0
python3 -c "
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
```bash
python run_pipeline.py 2>&1 | tail -30
```

Common causes:
- Ollama not running (Granite call fails during Stage 3)
- Write permission denied to `data/` directory
- `data/` directory doesn't exist: `mkdir -p data`

---

## 4. Onboarding / Instaloader Issues

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

## 5. Frontend Issues

### `npm run build` fails with TypeScript errors

**Symptom:** Build exits with type errors.

**Fix — check for missing type declarations:**
```bash
cd frontend
npx tsc --noEmit 2>&1 | head -40
```

Common causes:
- A new field was added to a backend response but not added to `frontend/lib/types.ts`
- A component imports a type that was removed

---

### Port 3000 already in use

```bash
lsof -i :3000
kill -9 <PID>
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
```bash
curl http://localhost:8000/api/health
```

If this succeeds but the browser still shows errors, open browser DevTools → Network → look for the failing request → check the Response tab for the actual error.

---

### Onboarding page not covering the sidebar

**Symptom:** The onboard page renders behind the sidebar layout instead of on top.

**Cause:** The `FullScreen` wrapper in `frontend/app/onboard/page.tsx` uses `z-50`. If the sidebar has a higher z-index, it will overlap.

**Fix — check the root layout's sidebar z-index:**
```bash
grep -n "z-" frontend/app/layout.tsx frontend/components/layout/Sidebar.tsx
```

Increase the onboard page's z-index if needed (`z-[100]` instead of `z-50`).

---

## 6. Data Issues

### `brand_profile.json` schema mismatch after manual edits

**Symptom:** The sidebar shows `undefined` for brand name, or the cluster dropdown is empty.

**Cause:** Manual edits broke the expected JSON structure.

**Fix:** Restore from demo and re-run onboarding, or validate against the schema in [Data Catalog](data-catalog.md).

---

### `clusters.json` has no `sample_captions`

**Symptom:** The cluster detail cards on the Create page show no sample captions.

**Cause:** An older version of the clustering pipeline didn't write `sample_captions`. The `GET /api/brand/clusters` endpoint merges cluster profiles from `brand_profile.json` with raw post data from `clusters.json` — if `clusters.json` was generated by an older pipeline, the merge may produce empty arrays.

**Fix:** Re-run the clustering stage:
```bash
python -c "from src.embeddings.cluster import run_clustering; run_clustering()"
```

---

## 7. Performance Issues

### Discover tab takes >5 minutes on every load

**Cause:** The `@lru_cache` is not working — caches are being cleared between requests.

**Diagnosis:** Look for calls to `cache_clear()` anywhere in your working copy:
```bash
grep -rn "cache_clear" api/
```

If `_clear_caches()` is being called on every request (instead of only after onboarding), that's the bug.

---

### Caption generation takes >60 seconds

**Cause:** The Granite model may be swapping to disk due to memory pressure.

**Fix — check RAM usage:**
```bash
# macOS
memory_pressure
```

Close other memory-heavy applications (browser tabs, Docker) and retry. Granite 3.1 8B needs at least 8 GB of available memory for comfortable inference.

---

## 8. Diagnostic Commands

Quick reference for common checks:

```bash
# Is Ollama running and Granite available?
ollama list | grep granite

# Is the backend healthy?
curl -s http://localhost:8000/api/health | python3 -m json.tool

# Does brand data exist?
curl -s http://localhost:8000/api/onboard/has-profile | python3 -m json.tool

# What's in the brand profile?
curl -s http://localhost:8000/api/brand/profile | python3 -m json.tool | head -40

# What clusters are loaded?
curl -s http://localhost:8000/api/brand/clusters | python3 -m json.tool | head -40

# How many scraped posts are there?
ls scraped_dataset/ig_text_*.json 2>/dev/null | wc -l

# How many cleaned records exist?
ls data/cleaned/*.json 2>/dev/null | wc -l

# Validate JSON files
python3 -c "import json; json.load(open('data/brand_profile.json')); print('brand_profile.json OK')"
python3 -c "import json; json.load(open('data/clusters.json')); print('clusters.json OK')"

# Full stack quick-test (requires venv active and uvicorn running)
python3 -c "
import urllib.request, json
for path in ['/api/health', '/api/onboard/has-profile', '/api/brand/profile']:
    r = urllib.request.urlopen(f'http://localhost:8000{path}')
    data = json.loads(r.read())
    print(f'{path}: OK ({list(data.keys())})')
"
```
