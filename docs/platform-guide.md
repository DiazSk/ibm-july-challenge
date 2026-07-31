# StyleSync Platform Guide

StyleSync is a Creative Intelligence Platform for Instagram creators — currently demoed against @hot_cakesbakes, an artisanal bakery in Navi Mumbai, but the pipeline (clustering, brand-profile extraction, generation, diagnosis) runs per-connected-account, not against a fixed dataset.

Twenty-two coordinated IBM Granite 3.1 8B invocations — zero third-party AI dependencies — run a closed feedback loop between behavioral clustering, generation, diagnosis, and autonomous agents, operating on the account's own historical Instagram data. When a post fails, StyleSync generates a brand-specific recovery brief — automatically, the moment you tag it that way in the Workbench. When a caption is saved, it becomes a training signal for the self-improving Autopilot playbook.

---

## Table of Contents

1. [Today](#today)
2. [Dashboard](#dashboard)
3. [Brand Voice](#brand-voice)
4. [Generate](#generate)
5. [Diagnose](#diagnose)
6. [Strategy](#strategy)
7. [Agents (Autopilot)](#agents-autopilot)
8. [Inbox Triage](#inbox-triage)
9. [Workbench](#workbench)
10. [JARVIS](#jarvis)
11. [Running the Stack](#running-the-stack)

---

## Today

`/app/today` — the daily briefing. Everything here already exists elsewhere in the product; this page composes it into one screen and hands the answer straight to the generator, instead of making you visit four pages to decide what to post.

**When to use:** Every morning, before you open Generate. This is meant to be the first tab you land on.

**How to use:** Nothing to fill in — it loads automatically in two waves. The recommendation (step 1) is pure Python and instant; the trend read and performance lesson are Granite-backed and arrive when they're ready, without blocking the page.

**What you get out of it:**

| Section | What it is |
|---|---|
| **Today's best post** | One recommendation, anchored to a real stat from your own data (e.g. *"Double down on Signature Sweet Treats — 0.43% sends-per-reach, your highest"*), with a source badge and a plain-language explanation of why that format. |
| **Ready-to-film script** | Your best-performing pillar's real caption, hook, and metrics (reach, sends-per-reach, saves-per-reach) pre-loaded. Click **"Write today's Reel →"** (label matches whatever format was recommended) and it hands off straight into Generate's Script Studio — caption, real metrics, correct format, and correct brand-voice cluster all pre-filled. |
| **Story plan** | The same winning post turned into a Story sequence via **"Write today's Story →"**. |
| **Trend read** (collapsible) | Pillar momentum plus audience-question signals pulled from your own comments — explicitly *not* an external trend feed. |
| **What your last winner taught you** (collapsible, open by default) | A Granite diagnosis of your actual top post: what worked, the brand-voice gap, and one thing to test today. |

If there's not enough post history yet, the page tells you to sync your Instagram account from the Dashboard first.

---

## Dashboard

`/app/dashboard` — account health at a glance, plus two agent triggers.

**When to use:** To check overall performance, resync your data, or kick off a background content job without leaving the summary view.

**How to use:** Loads automatically. Click **"↻ Sync from Instagram"** to trigger a real background resync of your connected account (polls until `last_sync` changes, up to ~15 minutes). Click **"Generate This Week's Brief"** under Weekly Brief Agent to have Granite scout your most underused pillar and draft ready-to-post ideas in the background.

**What you get out of it:**

- **KPI cards** — Posts Analyzed, Content Pillars, Saved Assets.
- **Performance Insights** — Total Reach, Total Views, Avg Engagement, Total Saves, computed from real ingested Instagram metrics.
- **Top Posts** — a list with embedded Instagram post previews.
- **Engagement by Pillar** — bar chart.
- **Best Day to Post** — timezone-aware heatmap (uses the account's own profile timezone).
- **Ask JARVIS** quick-question chips that hand a question straight to the JARVIS widget.
- **Strategic Brief card** — a synthesized recommendation with a link to Strategy.
- **Weekly Brief Agent** — click to start; shows a live progress bar, then "N drafts ready for [pillar]" with a **"Review drafts →"** link that opens the Workbench.
- **Content Pillars** — share and post count per pillar, discovered from this account's own posts (not a fixed list — see [Brand Voice](#brand-voice)).
- **Recent Generations** — your last 5 saved Workbench assets.

---

## Brand Voice

`/app/brand` — the extracted brand-voice profile, plus a drift watchdog.

**When to use:** To understand (or double-check) what "on brand" means for this account before writing anything, or to sanity-check a batch of recent posts against the locked profile.

**How to use:** Loads automatically — nothing to configure. For drift checking, paste 3 or more recent captions (one per line) into the Brand Drift Watchdog and click **"Check for Drift."**

**What you get out of it:**

- **Tone** — 3-5 real tone descriptors.
- **Signature Vocabulary** — recurring words as a tag cloud.
- **Avoid** — terms the brand conspicuously never uses, merged across all pillars.
- **Signature Phrases** — full sentences the brand repeats.
- **Pillar Signatures** — one card per content pillar with post count and a first sample caption.
- **Brand Drift Watchdog** — pastes your captions, matches them to the nearest pillar, then returns a severity verdict of **none / mild / significant** drift, with a **"Specific changes"** list (what changed) and a **"Still on brand"** list (what didn't) — scored against the locked brand profile, not a generic tone score.

---

## Generate

`/app/create` — the densest tab, and the one most people live in. It chains together six generation tools plus two brand-fidelity checks, in a loose top-to-bottom flow (each step works standalone, but each also feeds the next).

### Blank Page Solver

**When to use:** You have a moment or an occasion but no angle yet.

**How to use:** Open the panel, describe the moment in plain language, click **"Analyze Moment."** Granite returns the emotional core, business signal, and best-fit brand-voice cluster, then 3 creative direction cards. Pick one and click **"Apply Direction"** — it pre-fills the Caption Brief below.

**What you get out of it:** A specific angle and matching voice cluster, plus a **repetition guard** — if you've posted something similar before, it surfaces those past posts with a "worth repeating" / "change the angle" / "no metrics" recommendation, so you don't unknowingly repeat (or accidentally avoid repeating) something that already worked.

### Caption Brief → Caption Variants

**How to use:** Fill in Product, Occasion, Desired Feel (or let Blank Page Solver pre-fill it), pick a Brand Voice cluster, click **Generate**. Three caption variants come back, each with per-caption reasoning. **Regenerate** guarantees fresh captions that differ from every previous round in the session. From any variant: **copy, save (pin) to Workbench, → Image Direction**, or send it into **Guardian review**.

### The Drift Test

**When to use:** You want proof — not a claim — that StyleSync's brand grounding actually matters.

**How to use:** With Product + Occasion filled in, click **"Run the Drift Test."**

**What you get out of it:** The same brief run through two generators side by side — a plain LLM with no brand grounding, and StyleSync — each scored 0-100 for brand-voice fidelity, with matched signature phrases, matched signature words, and any avoided-term violations called out per side. Both captions land on-topic; the score is what shows only one of them actually sounds like the brand. This is the flagship "prove it, don't just claim it" feature.

### Resonance Simulator

**How to use:** After generating captions, click **"Check Resonance"** (via the caption variants panel).

**What you get out of it:** 3 audience personas — each grounded in one of the account's own real content-pillar audiences, not a generic buyer persona — react to every caption variant, and a synthesis step picks a favorite.

### Brand Guardian Courtroom

**When to use:** Before publishing, when you want a caption adversarially checked against the brand voice rather than trusting a single generation pass.

**How to use:** Click **"Guardian review"** on a caption variant.

**What you get out of it:** An adversarial critique-then-refine loop, hard-capped at 2 refinement rounds. If a round is approved, it stops early and reports "Approved after N rounds." If it never converges, it returns the best-scoring version of the 3 attempts and says so plainly — "Best of 2 rounds — still flagged" — rather than pretending an unresolved caption passed. Round-by-round history (caption + issues found) is available via **"Show round history."**

### Script Studio

**When to use:** You want to turn a caption (or a reference post) into a full shootable script.

**How to use:** Paste a reference caption, enter its performance metrics, pick a format (**Reel / Carousel / Static / Story**) and a brand-voice cluster, click **Generate Script**.

**What you get out of it:**

| Format | Output |
|---|---|
| **Reel** | Hook + alternate hook options, cover text, shot-by-shot breakdown (camera angle, lighting, setting, audio cue, voiceover line, duration per clip), music recommendation, a pre-filming checklist, caption, hashtags |
| **Carousel** | Cover-slide hook, per-slide headline + body + shoot direction, CTA slide, caption, hashtags |
| **Static** | Headline overlay, visual direction, caption, hashtags |
| **Story** | Frame-by-frame breakdown (on-screen text, shoot direction, sticker + sticker prompt) — deliberately has **no caption and no hashtags**, matching how Instagram Stories actually work |

Click **"Make all 4 formats"** to fan the current caption out to all four formats as one background job — they land in the Workbench as they finish.

---

## Diagnose

`/app/analyze` — why a post did what it did, for any post: real, hypothetical, or about to go live.

### My posts

**When to use:** Reviewing your account's real history.

**How to use:** Browse the tier-filtered list (**Top / Solid / Weak / No data** — a deterministic algorithm score based on sends and saves per reach). Click **"Diagnose ▸"** on any post to lazy-load its Granite diagnosis (only fetched once you expand a row). Click **"Re-diagnose"** to force a fresh Granite call instead of the cached one.

**What you get out of it:** Verdict (Succeeded / Underperformed / Failed), diagnosis, what worked, what failed, brand-voice gap, and change-next-time — per post, with an embedded Instagram preview. The tier badge is a separate, deterministic algorithm score and can legitimately disagree with the Granite verdict inside.

### Manual

**When to use:** A caption you're about to publish, a hypothetical, or a real post you want to check with an uploaded image.

**How to use:** Paste a caption, optionally upload an image or video for a vision-based visual description, fill in metrics, pick post type and brand-voice cluster, click **"Run Diagnosis."**

**What you get out of it:** The same diagnosis structure as above, plus:

- **Recovery Brief** — auto-drafted below the diagnosis whenever the verdict is Underperformed or Failed. Contains a new hook, a recommended format, and a ~150-word recovery script, saveable straight to Workbench.
- **Confidence badge** — gates every diagnosis honestly: **≥75 "Likely accurate," 50-74 "Worth a second look," below 50 "Verify before publishing."** Low-confidence output is flagged rather than asserted as fact.

---

## Strategy

`/app/discover` — one recommendation to act on this week, backed by the account's own numbers.

**When to use:** Weekly planning, or when deciding what to try next.

**How to use:** Loads automatically. The hero recommendation and comparison load fast (pure computation); the diagnoses and brief load progressively underneath.

**What you get out of it:**

- **This Week hero** — one recommendation anchored to a concrete stat (e.g. *"2,037 people sent your best post to a friend"*).
- **What worked, what didn't** — your actual best and worst real posts, side by side, each with its own Granite diagnosis.
- **Show me the numbers** (collapsible Scorecard) — algorithm metrics, each tagged with a source badge (**Instagram official** / **Your data** / **Industry study**), plus a performance timeline chart.
- **N more moves** (collapsible Playbook) — a Granite-written strategic brief with a concrete 2-week experiment, plus additional ranked, result-proven moves, each with its own source badge.

---

## Agents (Autopilot)

`/app/agents`, titled **"Autopilot"** in the UI — a genuinely autonomous agent that plans and produces a week of content, asking for your input only when it's actually unsure.

**When to use:** When you want a week's worth of drafted posts without doing the drafting yourself.

**How to use:** Pick post count (2-5), platform (Instagram / TikTok), and a quality gate — **Good enough (70) / Solid (80) / High bar (90)** confidence threshold. Optionally add a steer instruction. Click **"Plan my week."**

**What you get out of it:**

- A **live reasoning trace**: assess brand gaps → check trend momentum → recall past performance → plan the week → per post: draft caption → critic flags an issue → refine → repeat.
- Each finished post shows a **confidence score** and a **convergence badge** — **Goal met / Plateau / Max cycles / Factual gap** — so a non-converged result is labeled honestly rather than hidden.
- If the agent is genuinely unsure about something, it pauses with **"The agent needs your call"** and a clarifying question with quick-pick options or a free-text answer — real human-in-the-loop, not a fixed checkpoint.
- Finished posts (caption, pillar, angle, rationale, image direction) auto-save to Workbench.
- **Self-improving playbook** — click **"Reflect on what's working"** to have the agent analyze your tagged Workbench outcomes (winners/losers) and write new procedural rules. The current playbook shows each rule tagged **seed** or **learned**.
- **The agent's toolbelt** — a reference panel of the six specialized agents behind Autopilot (Analytics, Trend, Copywriting, Critic, Brand Voice, Visual).

---

## Inbox Triage

`/app/triage` — classify comments/DMs and draft on-brand replies in a batch.

**When to use:** Clearing a backlog of comments or DMs without writing each reply from scratch.

**How to use:** Paste up to 20 messages, one per line, into the batch box, pick a brand-voice cluster, click **Run**.

**What you get out of it:** Granite classifies each message as **order inquiry / compliment / complaint / spam** and drafts an on-brand reply for every non-spam message in a single batch call. Spam is correctly skipped (no reply drafted) and collapsed behind a **"Show Spam (N)"** toggle. Each active result has editable reply text with Copy / Save-to-Workbench, plus Send when in Instagram mode.

> **Current state, verified against source:** the page also has an "From Instagram" mode (pulls real comments via the connected account) built and wired end-to-end, including the 403 → reconnect flow for the `instagram_business_manage_comments` permission. As of this session's working tree, the mode toggle button has been removed from the UI and the page is hard-set to Paste mode only — this looks like a deliberate, uncommitted change made because that permission needs Meta App Review + Advanced Access before it reliably works (adding the permission and reconnecting isn't sufficient on its own). Worth confirming with whoever made that edit before calling "From Instagram" mode a shipped, user-facing feature.

---

## Workbench

A save-drawer, not a tab — opened from a **"Saved (N)"** button in the header on every page.

**When to use:** Any time you want to keep a generated asset, or decide what happened after you posted something.

**How to use:** Save from any generator (caption, script, recovery brief, agent output). Inside the drawer: star an asset, expand it, and tag its real-world **outcome** — succeeded / underperformed / failed. Tagging underperformed or failed automatically kicks off the autonomous Recovery Agent in the background (diagnose → decide → produce a fresh recovery post, or escalate for human review if it can't diagnose confidently).

**What you get out of it:** A persistent SQLite-backed history of everything you've generated, reviewed across sessions — and the raw signal the Autopilot playbook reflects on to learn what's actually working for this account.

---

## JARVIS

A floating voice/text assistant widget (mic button, bottom-right) present on every `/app/*` page.

**When to use:** Any question about your brand strategy, a quick caption, a post-mortem, or inspiration — without navigating to a specific tab.

**How to use:** Click the orb to type, or hold the mic to talk. Voice path: on-device browser recording → server-side Whisper transcription → Granite → server-side Kokoro TTS response, read back out loud.

**What you get out of it:** Answers grounded in the full brand profile, on-the-fly caption generation, post-mortems, web-search-backed inspiration (search snippets synthesized into 3 brand-adapted content ideas), and the ability to read from or save straight to Workbench — all without leaving whatever page you're on.

---

## Running the Stack

### Prerequisites
- Python virtual environment set up at `venv/`
- Ollama running locally with `granite3.1-dense:8b` pulled
- Node.js 18+ for the Next.js frontend

### Start the Backend (FastAPI)

```bash
cd /path/to/ibm-july-challenge
venv/bin/uvicorn api.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### Start the Frontend (Next.js)

```bash
cd frontend
npm run dev
```

App available at: `http://localhost:3000`

### Run the Data Pipeline (one-time setup)

If `data/brand_profile.json` or `data/clusters.json` don't exist:

```bash
venv/bin/python run_pipeline.py
```

This scrapes posts, builds embeddings, runs K-Means clustering, and generates the brand profile via Granite. Takes ~10-15 minutes on first run.

### Granite Invocations Summary

22 coordinated, numbered calls (verified against the `# Granite invocation #N` docstrings in `src/generation/*.py` and `src/agents/*.py`), all running locally against `granite3.1-dense:8b` — zero cloud AI dependencies. Whisper (transcription) and Kokoro (TTS), used by JARVIS's voice path, are separate local models and not counted here.

| # | Module | What it does | Surfaced in |
|---|--------|--------------|--------------|
| 1 | `embeddings/profile_extractor.py` | Extracts brand profile per cluster (pillar, tone, vocabulary, avoided terms, structure) | Brand Voice, pipeline setup |
| 2 | `generation/caption_generator.py` | Generates 3 on-brand caption variants | Generate (Caption Brief) |
| 3 | `generation/image_prompt_generator.py` | Generates art direction prompt | Generate (Image Direction) |
| 4 | `generation/why_engine.py` | Diagnoses post performance | Diagnose |
| 5 | `generation/voice_timeline.py` | Narrates creative voice evolution over time | **Backend only** — `/api/discover/voice-timeline` has no current frontend caller |
| 6 | `generation/blank_page_solver.py` (MomentAnalyzer) | Extracts emotional core + business signal from a moment | Generate (Blank Page Solver) |
| 7 | `generation/blank_page_solver.py` (DirectionGenerator) | Generates 3 creative directions | Generate (Blank Page Solver) |
| 8 | `generation/strategic_insights.py` | Writes strategic brief + 2-week experiment | Dashboard, Strategy |
| 9 | `generation/script_generator.py` | Generates Reel/Carousel/Static/Story script | Generate (Script Studio), Today (seeded script) |
| 10 | `generation/recovery_brief.py` | Generates recovery brief for underperforming/failed posts | Diagnose, Workbench (auto-triggered Recovery Agent) |
| 11 | `generation/boost_advisor.py` | Recommends which pillar/post to boost on Instagram, and which to avoid | **Backend only** — `/api/discover/boost-advisor` has no current frontend caller |
| 12 | `generation/voice_refiner.py` | Polishes a spoken (transcribed) caption idea into an on-brand caption | JARVIS voice loop |
| 13 | `generation/jarvis_agent.py` (`chat`) | JARVIS conversational turn | JARVIS |
| 14 | `generation/jarvis_agent.py` (`InspirationSynthesizer`) | Synthesizes web-search snippets into 3 brand-adapted content ideas | JARVIS ("search the web for inspiration") |
| 15 | `generation/confidence_scorer.py` | Writes the one-sentence confidence rationale (the score itself is a deterministic signal gate) | Diagnose |
| 16 | `generation/resonance_simulator.py` | 3 persona reactions + 1 synthesis call (×4 invocations per run) | Generate (Resonance Simulator) |
| 17 | `generation/weekly_brief.py` | Drafts ready-to-post ideas for the most underused pillar | Dashboard (Weekly Brief Agent) |
| 18 | `generation/brand_guardian.py` | Adversarial critique + refine (up to 2 rounds) | Generate (Guardian Courtroom); reused by Critic Agent's critique pass in Autopilot |
| 19 | `generation/brand_drift.py` | Drift severity verdict against the locked brand profile | Brand Voice (Drift Watchdog) |
| 20 | `generation/comment_triage.py` | Classifies + drafts replies, chunked 5 messages per call | Inbox Triage |
| 21 | `agents/critic_agent.py` (ErrorClassifier) | Classifies a flagged issue into one typed error (`ai_slop` / `off_brand_vocab` / `wrong_platform` / `factual_gap` / `approved`) | Agents (Autopilot) |
| 22 | `agents/trend_agent.py` | Turns pillar momentum + audience signals into content opportunities | Today (Trend read), Agents (Autopilot) |

Additionally, `generation/baseline_caption.py` makes one deliberately un-grounded Granite call — same model, no brand profile, no memory — used only as the "plain LLM" control side of Generate's Drift Test. (The StyleSync side of that same test reuses caption #2; scoring both sides against the brand profile is done by the deterministic `voice_fidelity.py`, not a Granite call.) Baseline Caption is intentionally excluded from the 22 above since it exists to be the honest, unbranded control, not a StyleSync feature.
