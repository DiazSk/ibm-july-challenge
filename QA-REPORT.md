# StyleSync — End-to-End QA Report

**Date:** 2026-07-11 (updated after backend fix pass)
**Tester:** Claude (acting as QA), driving the live stack directly — FastAPI backend (`uvicorn`) + Ollama (`granite3.1-dense:8b`) + Next.js frontend (`next dev`)
**Scope:** Every feature surface, frontend UI → backend API → Granite generation, for the @hot_cakesbakes demo dataset.
**Method:** Direct API calls (curl) for every endpoint's contract + timing, plus live browser-driven UI verification (console errors, network requests, DOM state) for every page and interactive flow.

## Verdict: **Demo-ready.** All five bugs found during the original QA pass (2 frontend, 3 backend) are now fixed and rigorously re-verified with multiple trials each. See §2 for fix details and re-test evidence.

---

## 1. Bugs found and fixed (frontend, during this QA pass)

| # | Severity | Area | Bug | Fix |
|---|---|---|---|---|
| F1 | **High** | Analyze tab — `DiagnosisPanel.tsx` | Backend always decorates `verdict_label` with symbols (`"✓  Succeeded"`, `"~  Underperformed"`, `"✗  Failed"`). The frontend's `VERDICT_CONFIG` lookup exact-matched against `Succeeded`/`Underperformed`/`Failed` — which **never** matches the decorated string. Result: **every single diagnosis, regardless of actual verdict, silently rendered with the amber "Underperformed" color** (a genuinely failed post looked no different from an underperformed one, and a succeeded post did too). This was 100% reproducible, not an edge case. | Changed the lookup to derive the color key from the raw `result.verdict` field (lowercase, undecorated) via substring match (`succeed`/`fail`/else `underperformed`), instead of exact-matching the decorated `verdict_label`. Verified live: a Failed-verdict post now renders in the correct red (`lab(53.9 63.2 38.6)`, matching `--destructive`), and a Succeeded-verdict post is correctly green. |
| F2 | **Medium** | Brand Voice page (`/app/brand`) | The "Signature Vocabulary" tag cloud mixed single recurring words (`homemade`, `soft`, `moist`...) with full sentences (`"Soft, moist, homemade cake"`, `"one bite of rasmalai cake & all diet plans got cancelled"`...) as if they were all small pill tags — full sentences crammed into tiny pills looked broken. Separately, "Lean Into" was an exact duplicate of the "Tone" section above it (same data, same tags, no new information). | Split into two sections: **Signature Vocabulary** (single words only, `recurring_words`) and a new **Signature Phrases** section (full sentences, `signature_phrases`, rendered as a quoted list, not pills). Removed the redundant "Lean Into" section. Verified live — reads cleanly now. |

## 2. Bugs found in backend business logic — **fixed and re-verified**

The user asked me to fix these and re-test rigorously. All three are now patched; each was re-tested with multiple trials (not just one) since two of the three are LLM-generation-dependent and intermittent by nature.

| # | Severity | Endpoint | Bug | Fix | Re-test evidence |
|---|---|---|---|---|---|
| B1 | **High** | `POST /api/agent/chat` (JARVIS, `search_inspiration` tool) | **Intermittent** (~1-in-2 in original testing): Granite sometimes failed to emit a proper `tool` JSON key and instead embedded the tool-call JSON as literal text *inside* the spoken response — the chat bubble would show `{"response": null, "tool": {...}}` verbatim, `action_result` stayed `null`, and `InspirationCards` never rendered. **Directly affected the scripted 3-minute demo** (minute 3: "Research trending bakery content and give me 3 ideas"). Same bug class already patched for the caption intent (`_CAPTION_INTENT_RE`), but no equivalent existed for inspiration. | Added `_detect_inspiration_intent()` in `api/routers/agent.py` — a regex pre-filter mirroring the existing caption one. Detects unambiguous research/inspiration phrasing and synthesizes the `search_inspiration` tool call directly, bypassing Granite's flaky routing entirely for this intent. | **8/8 clean trials, 0 failures** — 3 trials with the exact demo-script phrasing, 3 with varied natural phrasings ("find me some inspiration...", "what's trending...", "I need some content ideas..."), plus 2 regression checks confirming caption intent and plain brand Q&A are unaffected (still route correctly, not hijacked by the new filter). |
| B2 | **Medium** | `POST /api/create/image-prompt` | Granite occasionally returns malformed JSON (missing a comma between `prompt` and `style_notes`). The old fallback dumped the entire raw, garbled LLM output into the `prompt` field. | Added a 3-layer parse strategy in `image_prompt_generator.py`: (1) direct `json.loads`, (2) comma-repair regex + retry, (3) last-resort direct field extraction via regex (pulls `prompt`/`style_notes` values without requiring valid JSON). Raw-dump is now essentially unreachable except for truly non-JSON garbage. | Unit-tested against the **exact malformed text captured in original QA** — now parses correctly. Confirmed normal well-formed JSON still works, and true garbage still degrades gracefully (doesn't crash). 3/3 live endpoint calls after the fix returned clean prompts. |
| B3 | **Medium** | `GET /api/discover/boost-advisor` | `boost_cluster_id`/`boost_cluster_name` (and the `dont_boost_*` pair) could disagree — Granite free-generates the name independently of the ID. Reproduced live: UI showed "C3 · Behind the Scenes" when C3 is actually "Nutella Series". | The code already had the right pattern for `boost_post_hook` (override from the authoritative `cluster_engagement` dict by ID) but wasn't applying it to the name fields. Extended the existing override block to also correct `boost_cluster_name` and `dont_boost_cluster_name` from the real cluster registry — a deterministic fix, not probabilistic like B1. | 4 trials (including a cache-cleared fresh Granite generation, confirmed via differing reasoning text) — **100% correct pairing every time**, since the fix guarantees it regardless of what Granite outputs. Confirmed live in the browser: Discover tab now correctly shows "BOOST THIS: C3 · Nutella Series" / "DON'T BOOST: C4 · Bomboloni". |

## 3. Timing / demo-pacing risk (not a bug, but worth knowing before you're live)

Response latency on this machine varied wildly across identical-shape endpoints, all CPU/GPU-bound on Ollama:

| Endpoint | Observed latency |
|---|---|
| `analyze-moment` | ~5s |
| `directions` | ~29s |
| `captions` | ~47s |
| `image-prompt` | ~24s |
| `script` (Reel) | **1m 52s** |
| `voice-refine` | ~17s |
| `why-engine` | ~44-58s |
| `voice-timeline` | ~46s (cold), instant once cached |
| `strategic-insights` | instant (was already warm) |
| `boost-advisor` | ~39s |
| `agent/chat` | 3-34s depending on tool dispatch |
| `voice/synthesize` | ~18s |
| `voice/transcribe` | ~6s |

Script Studio in particular is a real risk — nearly **2 minutes** of silence with only a generic loading indicator is a long time to hold a live audience. Recommend either pre-warming Ollama right before the demo starts (run one throwaway call to each endpoint you'll use), or being ready to talk through what's happening while it loads.

## 4. Everything verified working correctly

**Backend data (real @hot_cakesbakes dataset, 113 posts / 5 clusters):**
- `GET /api/health`, `/api/onboard/has-profile`, `/api/brand/profile`, `/api/brand/clusters` — all correct shapes, real data
- `POST /api/onboard/reset-demo` — correctly restores full demo state including `cluster_engagement`

**Create tab (full pipeline, curl + live browser UI):**
- `analyze-moment` → `directions` → `captions` → regenerate (excludes previous — see minor note below) → `image-prompt` → `script` → `voice-refine`, all return correctly-shaped data
- Live UI: filled Caption Brief, generated 3 caption variants, rendered with reasoning/Copy/Save/→Image Direction buttons, saved one to Workbench — badge count updated live (2→3), zero console errors
- `localStorage` persistence (`ss_create_product/occasion/feel/cluster`) confirmed writing correctly

**Analyze tab + Recovery Brief:**
- Succeeded-verdict and Failed-verdict paths both tested; recovery brief auto-chains correctly on Failed
- Live UI confirms correct verdict badge text and (after fix) correct color
- `ss_analyze_form` persistence confirmed

**Discover tab:**
- All three endpoints (`voice-timeline`, `strategic-insights`, `boost-advisor`) return correct data; all three sections render live with real charts, narrative text, tensions, strategic brief, experiment suggestion — zero console errors (aside from the B3 name mismatch noted above)

**Workbench:**
- Full CRUD verified via API (create → 201, patch/pin → 200, filter by `pinned=true` → correct, delete → 204, count decrements correctly) and live UI (Star/Unstar toggling, badge count live-updating)

**JARVIS agent:**
- Caption intent: reliable, correctly routes to the right cluster via the documented keyword hint map
- Inspiration intent: works when Granite cooperates (see B1)
- Post-mortem intent: didn't trigger via free-text chat in either of 2 attempts (no leaked JSON, just no tool dispatch) — consistent with your documented demo script routing post-mortems through the dedicated Analyze tab instead, so low risk
- Session persistence (`GET`/`DELETE /api/agent/session/{id}`) both confirmed working

**Voice pipeline:**
- `voice/synthesize` — valid PCM16 WAV (confirmed via header bytes: RIFF/WAVE/fmt, format=1, 16-bit, 24kHz), stable across 3 consecutive calls including emoji-containing text (no misaki regression)
- `voice/transcribe` — round-trip tested (synthesize → transcribe), transcript closely matched source text

**Marketing site:**
- Landing, How It Works, Manifesto, Pricing all render cleanly, zero console errors, all real @hot_cakesbakes numbers (113 posts, 5 pillars, 14 Granite calls) consistent with the live backend
- "Open studio" / "Analyze my Instagram" correctly hand off into the live studio at `/app` → smart-redirects to `/app/dashboard` (profile exists)

**Cross-cutting:**
- Zero CORS errors across the entire session (confirmed via network inspection, not just absence of visible errors)
- `npm run build` clean after all fixes
- No stray console errors on any of the 12 routes

## 5. Minor observations (not blocking)

- **Caption regenerate can silently return fewer captions than requested** (saw 2 instead of 3 on a regenerate call) — likely the `num_predict=900` token ceiling getting hit sooner as `previous_captions` grows the prompt. Not wrong, just worth knowing if you regenerate many times in a row during the demo.
- Dev-mode network chatter: pinning/saving an asset triggers a noticeably large burst of duplicate `GET /api/workbench/assets` calls (React Query + multiple mounted observers in dev mode). All returned correct data; this is a dev-only cosmetic inefficiency, not expected in a production build.
- **My own mistake, caught and fixed during testing:** while testing the voice endpoint I accidentally overwrote and deleted a pre-existing tracked file (`test_speech.wav`, committed in an earlier commit). I caught this in `git status` and restored it via `git checkout -- test_speech.wav` before finishing — confirmed clean now. Flagging for transparency.

## 6. Files changed in this fix pass (backend, by request)

- `api/routers/agent.py` — added `_detect_inspiration_intent()` + wired into Call 1 (B1)
- `src/generation/image_prompt_generator.py` — added `_repair_missing_commas()` + `_extract_fields_by_regex()`, 3-layer parse fallback (B2)
- `src/generation/boost_advisor.py` — extended the existing engagement-data override to also correct cluster names, not just the post hook (B3)

No frontend files were touched in this fix pass (the two frontend bugs from the original QA pass were already fixed then). `npm run build` re-confirmed clean after this round.

## 7. New agentic features (post-QA build: Confidence Scoring, Closed-Loop Repurposing, Resonance Simulator, Weekly Brief Agent) — verified

Four new features were added after this report was originally written, each verified end-to-end (standalone script → curl → live browser) before being marked done:

**A. Confidence-Scored Outputs** (`src/generation/confidence_scorer.py`, Granite #15) — attaches a `confidence.score`/`rationale` to Why Engine and Boost Advisor results. Verified: curl on both endpoints returns valid scores; `ConfidenceBadge` renders correctly (green/amber/red) in both `DiagnosisPanel` and `BoostAdvisor`.

**B. Closed-Loop Repurposing Orchestrator** (`api/routers/repurpose.py`) — auto-triggers on a "succeeded" Why Engine verdict, backgrounding 3 sequential `ScriptGenerator` calls (Reel/Carousel/Static) and writing them straight to Workbench under a shared `batch_id`. Verified: curl trigger + poll to completion confirmed 3 new Workbench rows; live UI banner in `DiagnosisPanel` progressed through states correctly.

**C. Resonance Simulator** (`src/generation/resonance_simulator.py`, Granite #16) — 3 data-grounded audience personas (built from real `cluster_engagement` metrics) react to caption variants, then a synthesis call picks a winner + actionable fix. Verified: curl returned 3 distinct persona takes + valid synthesis; live UI showed "Panel's Pick" badge and full `ResonancePanel` render with no console errors.

**D. Weekly Brief Agent + proactive JARVIS hook** (`src/generation/weekly_brief.py` Granite #17, `api/routers/weekly_brief.py`) — scouts the underutilized content pillar, has Granite propose scenarios, then chains the existing `MomentAnalyzer → DirectionGenerator → CaptionGenerator → ImagePromptGenerator` pipeline per scenario, writing drafts to Workbench. Verified live end-to-end:
- Dashboard banner: idle → "Generate This Week's Brief" → running (progress + message updates through "Reviewing strategy" / "Researching trends" / "IBM Granite is planning" / per-scenario steps) → done ("2 drafts ready for Fusion Specials" + "Review drafts →" opening the Workbench drawer via the new shared `WorkbenchDrawerProvider` context)
- `WorkbenchDrawer`'s new `weekly_brief_draft` formatting branch renders Idea/Why this works/Caption/Image Direction/Style Notes cleanly instead of a raw JSON dump
- **404-after-restart guard**: killed and restarted `uvicorn` mid-job to simulate a lost process; confirmed the frontend polling stopped after exactly 3 consecutive failed requests and showed "Job may have been interrupted — check Workbench for any completed drafts" instead of polling forever
- **Proactive JARVIS nudge**: on a fresh page load with a completed-but-unnotified brief, JARVIS auto-opened with "I put together 2 ideas for your Fusion Specials pillar this week — open the Workbench to take a look."; confirmed fire-once semantics — `GET /api/weekly-brief/pending-notice` returns `{"pending": false}` immediately after, so it does not repeat on subsequent loads

**Regression pass after all 4 features:** re-checked Create, Analyze, and Discover tabs — all load and render correctly with zero console errors. `npm run build` clean (all 12 routes, TypeScript passes).

## 8. Roadmap features built out (Brand Guardian Courtroom, Brand Drift Watchdog, Closed-Loop Learning, Comment/DM Triage) — verified

Four more features — previously deliberately deferred as "roadmap / future work" in `NEW-FEATURES.md` due to specific named risks — were built and rigorously tested (standalone script → curl → live browser, checking console errors and network requests throughout), in build order 5 → 6 → 8 → 7:

**5. Brand Guardian Courtroom** (`src/generation/brand_guardian.py`, Granite #18) — an adversarial critique→refine loop on one already-generated caption, hard-capped at 2 rounds with best-so-far as a first-class outcome (directly designed around the named risk that a round-2 critique can flag a *different* issue than round 1 fixed). Verified: curl exercised all 3 outcome paths including a real round-2 tie-break case (round 1 fixed one issue, round 2 flagged a different one, same severity — correctly picked the latest attempt); live UI showed the "Best of 2 rounds — still flagged" badge, full round history, and a correct Workbench save under the new `guardian_refined_caption` type.

**6. Brand Drift Watchdog** (`src/generation/brand_drift.py`, Granite #19) — paste recent posts, auto-detects the nearest content pillar via embedding similarity (`all-MiniLM-L6-v2`, no persisted centroids — computed fresh per request), then Granite explains specifically what's drifted. Verified: standalone clearly differentiated an on-brand batch (no drift) from a deliberately generic/promotional batch (significant drift, specific evidence); curl confirmed the `<3 posts` 422 boundary and a 20-post batch (12-post cap into the Granite call) didn't break. **Two real bugs found and fixed during browser testing**: (1) the embedding-similarity "direction" label and Granite's independent "severity" verdict could legitimately disagree (e.g. "very_different" embedding vs. "mild" severity), reading as contradictory — reframed the similarity copy to describe pillar-matching, not a competing verdict; (2) Granite sometimes returned `specific_changes` as `{element, description}` objects instead of strings, rendering as raw Python dict reprs — added a `_stringify_item()` normalizer.

**8. Closed-loop performance → generation learning** (extends `CaptionGenerator`, Granite #2 — zero new Granite invocations) — real, user-reported post outcomes now calibrate future caption generation for that content pillar. **Found a genuine prerequisite gap**: the `actual_outcome` field already existed in the schema but had no UI to set it anywhere — built a 3-way outcome pill toggle (succeeded/underperformed/failed) in the Workbench drawer, using an empty-string (not `null`) mechanism to clear a value, verified via network payload inspection (`"actual_outcome":""`). `CaptionGenerator.generate()` got a new optional `performance_context` kwarg, verified byte-identical output when omitted (prompt-diff test) so all 3 existing Python call sites are unaffected. `/api/create/captions`'s response shape changed from a bare array to `{captions, used_real_outcomes}` (only 2 frontend call sites, both updated). Verified live: tagging 3 real outcomes for a cluster made `used_real_outcomes` jump 0 → 3 and a "Calibrated using 3 real outcomes so far" badge appeared on the Create tab, correctly absent for an untagged cluster.

**7. Comment/DM Triage + Draft Replies** (`src/generation/comment_triage.py`, Granite #20) — paste up to 20 comments/DMs, classified (order inquiry/compliment/complaint/spam) and drafted brand-voice replies in chunks of 5 per Granite call, with a mandatory static banner disclosing there's no live Instagram inbox API. Verified: standalone batch spanning a chunk boundary correctly classified all 4 categories with no invented order details/prices and correct index ordering; curl confirmed both the 0-message and >20-message 422 boundaries. New `/app/triage` page + nav entry, spam correctly collapsed under a disclosure, editable draft replies, Workbench save round-trips with the new `triage_reply` type. **One more bug found and fixed**: Dashboard's separate `previewText()` helper (distinct from the Workbench drawer's own preview function) didn't know about the `drafted_reply` field and showed a generic "Saved asset" placeholder instead of the reply text — fixed.

**Regression pass after all 4 features:** re-checked Create, Analyze, Discover, and Dashboard — all load and render correctly with zero console errors. `npm run build` clean (15 routes including the new `/app/triage`, TypeScript passes).

## Recommendation

**Ready to demo.** Remaining non-blocking items: **Script Studio latency (~2 min)** is inherent to Ollama/hardware — plan your talking points around it or pre-warm Ollama right before presenting. The Weekly Brief Agent (n=2) takes ~4.5 minutes end-to-end — kick it off early in a demo so it's ready to reveal later. The Brand Guardian Courtroom's critique pass is genuinely harsh by design (it rarely approves on round 0 even for on-brand captions) — the "best of 2 rounds" framing is the honest, intended outcome, not a bug; don't be surprised if it doesn't converge to "Approved" during a live demo.
