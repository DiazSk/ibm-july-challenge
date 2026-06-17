# StyleSync — Product Brief

## What It Is

StyleSync is a Creative Intelligence Platform for Instagram creators. It analyzes your own posting history and turns it into a living brand intelligence system — one that generates content, diagnoses why posts fail, surfaces strategic gaps, and recommends exactly where to invest your creative energy next.

Every tool on the market assumes you know what you want to make. StyleSync starts from the opposite question: **who are you already, and how do you make more of that?**

---

## The Problem

Instagram creators face three distinct problems that no single tool currently solves together:

**1. The blank page.** Most AI writing tools (ChatGPT, Jasper, generic caption generators) produce generic output because they have no idea who you are. They write for a hypothetical "Instagram creator," not for your specific voice, aesthetic, and audience relationship.

**2. The post-mortem gap.** When a post underperforms, creators have no explanation. Instagram Insights shows *that* views were low — it never explains *why*. Was it the caption structure? The posting time? A drift from your brand voice? No tool connects the dots.

**3. The strategy blindspot.** Most creators don't know which of their content types is genuinely resonating versus which they're over-posting out of habit. There's no signal pointing to underutilized creative territory that actually works.

---

## How It Works

### Step 1 — Onboarding (one-time)

Connect your Instagram account or upload your data export. StyleSync processes your entire posting history — captions, post types, timestamps, engagement metrics — and runs it through a three-stage pipeline:

1. **Text processing:** Cleans and structures your caption history
2. **Semantic clustering:** Groups your posts into 3–6 content pillars using sentence-transformers + K-Means, based on vocabulary, tone, and subject matter — not categories you defined
3. **Brand voice extraction:** IBM Granite 3.1 8B reads each cluster and extracts a detailed brand voice profile: content pillar, tone descriptors, signature vocabulary, structural patterns

The result is a `brand_profile.json` — a structured description of your creative identity, built entirely from your own data.

### Step 2 — Create, Analyze, Discover

Once onboarded, every feature in StyleSync runs against your brand profile. Nothing is generic. Every output is calibrated to who you already are.

---

## Core Features

### Create Tab

**Blank Page Solver**
Describe a moment in plain language — *"It's Friday evening and we just pulled the last batch of Pistachio Rose Bomboloni"* — and Granite identifies the emotional core, matches it to your best-fit content pillar, and generates three distinct creative directions. Pick one, and it auto-populates the Caption Brief with the right voice and feel.

**Caption Brief**
Enter a product, occasion, and desired feel. Granite generates three caption variants, each with reasoning for why it fits your brand patterns. Every variant can be regenerated with diversity constraints (no repetition from previous runs). Save any caption to the Workbench.

**Image Direction**
Select a caption and get a Midjourney/DALL-E ready art direction prompt — color palette, composition, mood, subject framing — calibrated to your brand's visual identity extracted from your content history.

**Script Studio**
Paste a high-performing caption and performance metrics. Granite generates a full production script for your chosen format — Reel (hook + voiceover + shot list), Carousel (cover slide + slides + CTA), or Static (headline + visual direction). Save to Workbench.

---

### Analyze Tab

**Why Engine**
Paste any post caption + Instagram Insights metrics (views, reach, likes, comments, shares, saves). Granite runs a post-mortem against your brand voice profile and produces:
- A verdict: Succeeded / Underperformed / Failed
- A diagnosis: specifically what worked or didn't, against your brand patterns
- A brand voice gap analysis: where the post drifted from your established voice

**Recovery Brief** *(automatic on underperforms and failures)*
When the Why Engine diagnoses a failure, it immediately chains into a second Granite call and generates a recovery strategy:
- A new hook written at a different angle
- A recommended format (Reel / Carousel / Static) with reasoning
- A 150-word recovery script in your brand voice
- Save to Workbench

---

### Discover Tab

**Voice Timeline**
A month-by-month breakdown of how your content distribution has shifted across your clusters. Granite narrates the creative arc — where you started, what dominated each period, and how your voice has evolved. For @hot_cakesbakes: from 57% basic product showcase (Oct 2025) to a March 2026 Bomboloni peak (48% of all content), then a deliberate diversification.

**Strategic Insights**
Two rankings per cluster: **volume rank** (how often you post this type) vs **richness rank** (how linguistically and conceptually rich this cluster's vocabulary is). The gap between them is your strategy signal.

- High richness, low volume = **underutilized territory** — your most distinctive content type that you're not investing in
- High volume, low richness = **over-invested** — you're repeating yourself in your least distinctive voice

Granite synthesizes these gaps into a strategic brief: what to lean into, what to pull back from, and why.

**Boost Advisor**
Instagram gives you a Boost button. It doesn't tell you which post to boost. StyleSync answers this with a dedicated Granite invocation (#11) that cross-references engagement data (average views, saves, comments per cluster) with richness and volume ranks to produce a single concrete recommendation:

- Which cluster's post to boost and exactly which hook
- Why that cluster has the highest return on paid amplification
- Which Instagram objective to select and how to target
- Which cluster NOT to boost and why it would waste budget

For @hot_cakesbakes: Bomboloni content (C4) averages 1,720 views, 67 saves, and an 11.1% engagement rate — 2.1× the account average. Its richness rank is #1. StyleSync recommends boosting it over Homemade Classics (C0, 820 avg views, lowest engagement rate), where spend would underperform.

---

### Content Workbench

A persistent SQLite scratchpad that survives refreshes and sessions. Every generated caption, script, image direction, and recovery brief can be saved here. Star assets you want to return to. Track outcomes (did this post succeed after you used it?). The Workbench makes StyleSync a workflow tool, not just a one-shot generator.

---

## The IBM Granite Architecture

StyleSync runs **11 coordinated IBM Granite 3.1 8B invocations** — every single one running locally via Ollama, with zero cloud API calls during inference.

| # | Invocation | Purpose |
|---|------------|---------|
| 1 | Brand Profile Extractor | Reads each content cluster, extracts voice profile |
| 2 | Caption Generator | Generates 3 on-brand caption variants with reasoning |
| 3 | Image Direction | Art direction prompt calibrated to brand visual identity |
| 4 | Why Engine | Post-mortem: verdict + diagnosis + brand voice gap |
| 5 | Voice Timeline | Narrates creative evolution from monthly cluster data |
| 6 | Moment Analyzer | Emotional core + business signal from a described moment |
| 7 | Direction Generator | 3 distinct creative directions from moment analysis |
| 8 | Strategic Insights | Richness vs volume strategy brief from cluster rankings |
| 9 | Script Generator | Full Reel/Carousel/Static production script |
| 10 | Recovery Brief | Recovery hook + format + script chained from Why Engine failure |
| 11 | Boost Advisor | Engagement-weighted recommendation for which post/cluster to boost |

These are not 10 identical calls with different prompts. Each invocation operates on a different data shape, a different reasoning task, and a different output structure. Together they form a closed feedback loop: your history informs your generation, your generation outcomes feed back into your diagnosis, your diagnosis informs your next creation.

**Why local matters:**
- No API cost. No rate limits. No dependency on external availability.
- Your posting history and brand data never leave your machine.
- The demo runs identically in a room with no internet.

---

## Competitive Landscape

### StyleSync vs Octupie

[Octupie](https://www.octupie.com/) is the closest competitor — an Instagram-focused tool backed by IIT Madras founders and Microsoft Startup support. It tracks competitor/niche accounts, detects outlier posts that beat each account's baseline, decodes the hook/format that drove the spike, and generates a voice-matched script.

**Their thesis:** *"Turn what's winning in your niche into scripts that sound like you."*
**Our thesis:** *"Turn who you already are into what you make next."*

| Dimension | Octupie | StyleSync |
|-----------|---------|-----------|
| Data source | Competitor public accounts | Your own historical posts |
| Core question | What's winning in my niche? | What's authentic to me? |
| Voice matching | Trained on your catalogue | Extracted from your cluster patterns |
| Post diagnosis | Not offered | Why Engine (Granite #4) |
| Recovery strategy | Not offered | Recovery Brief (Granite #10) |
| Creative evolution | Not tracked | Voice Timeline (Granite #5) |
| Content strategy | Not offered | Strategic Insights (Granite #8) |
| Boost Advisor | Not offered | Granite #11 — which post to boost + why |
| AI stack | Unspecified | IBM Granite 3.1 8B, 10 invocations, local |
| Privacy | Requires Instagram scraping | Fully local, no external calls |

**The strategic gap Octupie misses:** If you optimize entirely on competitor signal, you converge toward what everyone else is doing. StyleSync answers a different question — not "what's popular?" but "what's *yours*, and where have you drifted from it?"

**The gap StyleSync currently has:** We don't surface what's trending in your niche. Octupie does this. We've consciously decided this is a different product, not a missing feature — because a scraping dependency introduced 6 weeks from a hard deadline is a liability, not a feature.

---

### StyleSync vs ChatGPT / Generic AI Writers

ChatGPT generates captions from whatever you tell it. It has no knowledge of your brand voice, your content clusters, your performance history, or your audience relationship. It will write "indulgent and intimate" copy for a bakery because you said so — but it has no idea that your Cluster 1 vocabulary consistently uses *quiet* sensory language and avoids superlatives, or that posts using "linger" and "unhurried" in the same sentence outperform everything else in your catalog by 40%.

StyleSync's generation is not prompted by the user's self-description. It's derived from the creator's observed behavior across 100+ posts. That's the difference between "write in my voice" and "write from my voice."

---

### StyleSync vs Generic Analytics Tools (Socialinsider, vidIQ, Later Analytics)

Analytics tools answer: *"What happened?"*  
StyleSync answers: *"Why did it happen, and what do you do next?"*

Generic analytics show a creator that their Reel on a Tuesday got 30% more views than their average. They show no causal explanation, no brand voice context, no recovery strategy, and no generation capability. The creator leaves with a data point and no action.

StyleSync turns the same signal into: a Why Engine verdict, a brand voice gap analysis, a Recovery Brief with a specific new hook and script, and a Strategic Insights recommendation about which content type to invest in next.

---

## The Engagement Plateau Problem

**Scenario:** A creator has posted 100+ times across Reels, carousels, and statics. Everything averages about 1,000 views. Nothing spikes. The Why Engine, which explains *variance*, is useless here because there is no variance to explain.

This is a **systemic account problem**, not a post-level problem. It requires a portfolio-level audit.

StyleSync's clustering data already contains the raw material to answer this:
- Which content cluster is driving the highest average engagement?
- Which cluster has the richest vocabulary (highest brand potential) but the lowest post volume?
- Where have they been over-posting in their least distinctive voice?

The **Boost Advisor** (planned feature, Granite #11) will use this data to answer the exact question Instagram's native Boost button never answers: *which post should I put money behind?*

Output: "Your Cluster 1 content (richest vocabulary, currently 3 posts vs 40 for Cluster 0) averages 1.4x your account baseline. This specific post has your strongest hook structure. Boost it to amplify your best-performing creative territory, not your most frequent one."

This is a zero-new-data-source feature — everything needed is already in `clusters.json`. It uses existing infrastructure and one additional Granite invocation.

---

## Three-Minute Demo Arc

1. **Start with the wow** — Blank Page Solver. Describe a real baking moment in plain language. Watch Granite map it to a content pillar, generate 3 creative directions, and auto-populate the Caption Brief. Generate 3 captions with brand reasoning. Save one to the Workbench.

2. **Show the data** — Discover tab. Voice Timeline: 8 months of creative evolution narrated by Granite. Strategic Insights: Cluster 0 is over-invested (volume rank #1, richness rank #3). Cluster 1 is underutilized (richness rank #1, volume rank #3). That gap is a strategy recommendation.

3. **Close with the diagnosis** — Analyze tab. Paste a real low-performing post. Why Engine produces: verdict (Underperformed), specific diagnosis, brand voice gap. Recovery Brief generates automatically: new hook, recommended format, full 150-word script. Save to Workbench.

**The closing line:** *StyleSync is not a content tool. It's a creative operating system built from your own history — the first AI that starts from who you already are.*

---

## Stack

| Layer | Technology |
|-------|-----------|
| AI | IBM Granite 3.1 8B via Ollama (local) |
| AI framework | LangChain (langchain-ollama) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Clustering | scikit-learn K-Means |
| Backend | FastAPI (Python) |
| Frontend | Next.js 16 (App Router), React Query, TypeScript |
| Persistence | SQLite (workbench), JSON (brand profile, clusters) |
| Styling | Tailwind CSS, quiet-luxury design system |

**Data used for demo:** @hot_cakesbakes — artisanal bakery, Navi Mumbai. 113 posts, 8 months (Oct 2025 – Jun 2026), 5 content clusters.
