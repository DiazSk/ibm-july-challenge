# StyleSync Platform Guide

StyleSync is a Creative Intelligence Platform for HotCakes Bakes (@hot_cakesbakes), an artisanal bakery in Navi Mumbai.

Ten coordinated IBM Granite 3.1 8B invocations — zero third-party AI dependencies — run a closed feedback loop between behavioral clustering and content generation, operating on eight months of real creator data. When a post fails, StyleSync generates a brand-specific recovery brief. When a caption is saved, it becomes a training signal in the Content Workbench.

---

## Table of Contents

1. [Create Tab](#create-tab)
2. [Analyze Tab](#analyze-tab)
3. [Discover Tab](#discover-tab)
4. [Content Pillars Reference](#content-pillars-reference)
5. [Running the Stack](#running-the-stack)

---

## Create Tab

**Purpose:** Generate on-brand Instagram content from scratch — captions, image direction, and full content scripts — without staring at a blank page.

### Blank Page Solver

**When to use:** You have a moment, a product freshly out of the oven, or an occasion — but no creative angle yet.

**How to use:**
1. Open the "Blank Page Solver" expander
2. Describe the moment in plain language (e.g. *"It's Friday evening and we just pulled the last batch of Pistachio Rose Bomboloni. It smells incredible."*)
3. Click **Analyze Moment** — Granite identifies the emotional core and business signal of the moment, and picks the best content pillar
4. Review the 3 creative direction cards — each takes a different angle (emotional, sensory, conversational)
5. Select a direction and click **Apply Direction** — the Caption Brief is pre-filled with your direction and voice cluster

**What you get out of it:** A specific creative angle and matching brand voice cluster — so the captions you generate aren't generic but grounded in what your audience responds to.

---

### Caption Brief

**When to use:** You know what you want to post about and you're ready to generate captions.

**How to use:**
1. Fill in **Product** (e.g. *"Nutella Bomboloni"*)
2. Fill in **Occasion** (e.g. *"Weekend drop"*)
3. Fill in **Desired Feel** (e.g. *"indulgent and playful"*) — or let the Blank Page Solver pre-fill this
4. Select a **Brand Voice** cluster (or let the Blank Page Solver pre-select)
5. Click **Generate Captions** → 3 caption variants appear, each from a different angle

**What you get out of it:** 3 on-brand caption variants with per-caption reasoning explaining which brand attributes were applied. Each is under 150 words with max 5 hashtags and naturally embedded targeting keywords.

**Regenerate:** If none of the 3 captions feel right, click **Regenerate** in the header of the caption list. The form fields stay as-is; Granite generates 3 fresh captions guaranteed to differ from all previous rounds.

**Image Direction:** Click **→ Image Direction** on any caption to generate an art direction prompt (suitable for Midjourney or DALL-E 3) matched to that specific caption's mood.

---

### Script Studio

**When to use:** You want to replicate the success of a post that performed really well — turning it into a full Reel voiceover, Carousel slide copy, or Static post.

**How to use:**
1. Open the "Script Studio" expander
2. Paste the caption of a high-performing post into **Reference Post Caption**
3. Enter its **Performance Metrics** (views, reach, likes, comments, shares, saves — from Instagram Insights)
4. Choose **Output Format**: Reel, Carousel, or Static Post
5. Select a **Brand Voice** cluster to apply
6. Click **Generate Script**

**What you get out of it:**

| Format | Output |
|--------|--------|
| **Reel** | Hook line, opening line, full voiceover script, 3-4 shot suggestions, caption, hashtags |
| **Carousel** | Cover slide hook, 5-6 slides with headline + body, CTA slide, caption, hashtags |
| **Static** | Headline overlay text, caption, visual direction note, hashtags |

Granite analyzes what made the reference post work (its hook style, emotional angle, pacing) and generates a new script in your brand's voice that follows the same pattern.

---

## Analyze Tab

**Purpose:** Diagnose why a specific post succeeded or underperformed — not based on gut feel, but by comparing it against the brand's documented voice patterns across all 5 content pillars.

### Why Engine

**When to use:** After any post goes live and you've checked Instagram Insights. Works best when the results surprised you — either better or worse than expected.

**How to use:**
1. Paste the **Caption** you posted
2. Select the **Post Type** (Reel, Carousel, Static)
3. Enter the **Performance Metrics** from Instagram Insights:
   - Views, Reach, Likes, Comments, Shares, Saves (always available)
   - Avg Watch Time (optional, Reels only)
4. Select the **Brand Voice (Cluster)** that best matches the caption's content
5. Click **Run Diagnosis**

**What you get out of it:**

| Section | What it tells you |
|---------|-------------------|
| **Verdict** | Succeeded / Underperformed / Failed — based on metric ratios |
| **Diagnosis** | The core reason for this outcome in plain language |
| **What Worked** | Specific brand voice elements that landed |
| **What Failed** | What was off-brand or structurally weak |
| **Brand Voice Gap** | The distance between this post and the cluster's ideal voice |
| **Change Next Time** | 3-4 concrete, actionable adjustments |

The Why Engine is Granite call #4. It cross-references the post's metrics against the cluster's expected performance patterns and the brand's voice profile to identify causal factors — not correlations.

### Recovery Brief

**When you see it:** Automatically appears below the diagnosis whenever the verdict is **Underperformed** or **Failed** — no extra action required.

**What it is:** Granite call #10 — chained directly from the Why Engine result. Using the identified diagnosis, failure mode, and brand voice gap, Granite generates a concrete recovery strategy:

| Field | What it contains |
|-------|-----------------|
| **New Hook** | A single punchy opening line that directly fixes the identified failure |
| **Recommended Format** | Reel, Carousel, or Static — whichever best addresses the failure mode |
| **Recovery Script** | ~150-word script in brand voice for the recommended format (hook, body, CTA) |
| **Why This Works** | 1-2 sentences explaining how this approach addresses the original failure |

**Save to Workbench:** Click the button to save the recovery brief to the Content Workbench, where it persists between sessions alongside saved captions and scripts.

---

## Discover Tab

**Purpose:** Understand how HotCakes Bakes' creative voice has evolved over 9 months, and identify strategic gaps between where they invest (posting frequency) and where their voice is richest (most developed).

The Discover tab loads automatically. Both computations run once on first load and are cached — so the second visit is instant. Expect 60-120 seconds on first load while Granite analyzes the data.

---

### Voice Timeline

**What it is:** A stacked area chart showing the monthly distribution of posts across the 5 content pillars from October 2025 to June 2026.

**How to read it:**
- Each colored area represents one content pillar
- The height of each area in a given month shows how much of that month's posting was in that pillar
- Peaks and troughs reveal creative seasons and shifts
- The **Voice Arc** card narrates the 9-month evolution in plain English
- The **Key Shift** card highlights the single most notable change

**What you get out of it:** A birds-eye view of whether you're drifting from your core identity, doubling down on a pillar, or naturally diversifying. Useful for quarterly strategy reviews.

---

### Strategic Insights

**What it is:** A bar chart comparing **Volume Score** (how often you post in each pillar) against **Richness Score** (how developed and distinct each pillar's voice is), plus a Granite-written strategy brief.

**How to read it:**
- Higher Volume Score = you post in this pillar frequently
- Higher Richness Score = this pillar has well-developed, distinctive vocabulary and tone
- A pillar with high Richness but low Volume = **underutilized** — you have a strong voice here but aren't using it
- A pillar with high Volume but low Richness = **over-invested** — you post here often but the voice is thinner

**What you get out of it:**
- **Tension callouts** — specific over-invested and underutilized clusters named by Granite
- **Strategic Brief** — 3-4 sentence recommendation on how to rebalance
- **Experiment to Run** — one concrete, low-effort experiment for the next 2 weeks

---

## Content Pillars Reference

The 5 content pillars were discovered by running K-Means clustering (k=5) on 113 posts using sentence-transformer embeddings. Each cluster has a distinct vocabulary, tone, and content pattern.

| Cluster | Name | Posts | Core Focus | Signature Tone |
|---------|------|-------|------------|----------------|
| **C0** | Homemade Classics | 34 | Eggless cakes, brownies, moist textures — emphasizing premium homemade quality | Loving, passionate, dedicated |
| **C1** | Fusion Specials | 22 | Indian-fusion desserts — rasmalai cake, kunafa, biscoff creations | Playful, inventive, indulgent |
| **C2** | Behind the Scenes | 15 | Baker life, kitchen moments, gratitude for small business support | Relatable, humorous, grateful |
| **C3** | Nutella Series | 15 | Nutella bomboloni, KitKat brownies — hazelnut-chocolate focus | Enticing, indulgent, gooey |
| **C4** | Bomboloni | 27 | Signature bomboloni — comfort, freshness, wholesale/bulk angle | Comforting, inviting, warm |

**When choosing a cluster for caption generation:**
- Use **C0** for core product launches (cakes, brownies) with emotional storytelling
- Use **C1** for new fusion flavors or limited-edition specials
- Use **C2** for behind-the-scenes content, process videos, or gratitude posts
- Use **C3** for any Nutella or chocolate-heavy product
- Use **C4** for bomboloni, comfort food framing, or wholesale/bulk content

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

Ten coordinated calls, all running locally against `granite3.1-dense:8b` — zero cloud AI dependencies.

| # | Module | What it does |
|---|--------|--------------|
| 1 | `profile_extractor.py` | Extracts brand profile from post corpus |
| 2 | `caption_generator.py` | Generates 3 on-brand caption variants |
| 3 | `image_prompt_generator.py` | Generates art direction prompt |
| 4 | `why_engine.py` | Diagnoses post performance |
| 5 | `voice_timeline.py` | Narrates creative voice evolution |
| 6 | `blank_page_solver.py` (MomentAnalyzer) | Extracts emotional core from a moment |
| 7 | `blank_page_solver.py` (DirectionGenerator) | Generates 3 creative directions |
| 8 | `strategic_insights.py` | Writes strategy brief + experiment |
| 9 | `script_generator.py` | Generates Reel/Carousel/Static script |
| 10 | `recovery_brief.py` | Generates recovery brief for underperforming posts |
