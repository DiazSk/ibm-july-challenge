# StyleSync — Product Brief

## What It Is

StyleSync is a Creative Intelligence Platform for Instagram creators — but the product is not one hero feature, it's a complete stack. One profile, extracted from a creator's own posting history, is the single source of truth behind Today's recommendation, next week's campaign, this post's diagnosis, this quarter's strategy, an autonomous week-long content agent, and the replies waiting in the inbox. Eight surfaces — Today, Dashboard, Brand Voice, Generate, Diagnose, Strategy, Agents, Inbox Triage — all reading from and writing back to that one profile.

Every tool on the market assumes you know what you want to make. StyleSync starts from the opposite question: **who are you already, and how do you make more of that?**

One moment in that stack produces a number instead of a promise — **the Drift Test**, inside Generate, scores a StyleSync caption against a generic-AI baseline for brand-voice fidelity, on the same brief, side by side. It's a strong, credible proof point. It is not the whole product; it's one feature among eight.

---

## The Problem

Instagram creators face three distinct problems that no single tool currently solves together:

**1. The blank page.** Most AI writing tools (ChatGPT, Jasper, generic caption generators) produce generic output because they have no idea who you are. They write for a hypothetical "Instagram creator," not for your specific voice, aesthetic, and audience relationship.

**2. The post-mortem gap.** When a post underperforms, creators have no explanation. Instagram Insights shows *that* views were low — it never explains *why*. Was it the caption structure? The posting time? A drift from your brand voice? No tool connects the dots.

**3. The strategy blindspot.** Most creators don't know which of their content types is genuinely resonating versus which they're over-posting out of habit. There's no signal pointing to underutilized creative territory that actually works.

Underneath all three is a fourth, structural problem: the workflow itself is scattered. A caption gets drafted in one app, scheduled in another, its performance read in a third, its comments answered in a fourth — and the creator is the only integration layer, re-explaining their own voice every time they switch tabs. StyleSync's answer to that isn't a ninth tool; it's collapsing the whole loop onto one extracted profile.

---

## How It Works

### Step 1 — Onboarding (one-time)

Two ways in: connect a real Instagram Business/Creator account via OAuth, or upload a data export. The OAuth path (`/api/connect`) does more than a one-time pull — once authorized, a background poller keeps syncing the account and invalidating the cached brand profile, so the extraction stays current as new posts go up, not just accurate as of the day you connected. Either path lands in the same place: StyleSync processes the account's entire posting history — captions, post types, timestamps, engagement metrics — through a three-stage pipeline:

1. **Text processing:** Cleans and structures your caption history
2. **Semantic clustering:** Groups your posts into content pillars using sentence-transformers + K-Means, based on vocabulary, tone, and subject matter — not categories you defined
3. **Brand voice extraction:** IBM Granite 3.1 8B reads each cluster and extracts a detailed brand voice profile: content pillar, tone descriptors, signature vocabulary, avoided terms, structural patterns

The result is a `brand_profile.json` — a structured description of your creative identity, built entirely from your own data, one extraction serving every feature below rather than per-feature setup.

### Step 2 — Eight Surfaces, One Profile

Once onboarded, every tab in StyleSync reads from the same brand profile. Nothing is generic. Every output — whether it's today's recommendation, a caption, a diagnosis, or a reply draft — is calibrated to who the account already is.

---

## Core Features

### Today Tab

**Today's Post**
Pulls the account's single highest-performing content pattern and turns it into a ready brief: recommended pillar, a caption seed, and a script pre-filled from that pattern's own real performance data — one click from "what do I post today" to a shootable Script Studio draft.

---

### Dashboard Tab

**Performance Overview**
KPI roll-up (posts analyzed, content pillars, saved Workbench assets), a Top Posts list with embedded Instagram previews, an Engagement-by-Pillar chart, and a Best-Day-to-Post chart built from the account's own posting-time history.

**Weekly Brief Agent** *(background)*
A one-click background job (Granite #17) that drafts a batch of fresh post ideas for the account's most underused pillar while the creator does something else — surfaced as "N drafts ready" when it finishes, and referenced again from the Strategy tab's "This Week" recommendation.

**Ask JARVIS**
A quick-question box wired into the same JARVIS agent (Granite #13/#14) that lives on every page as a floating voice-and-text assistant — ask about the best-performing cluster, request a caption, or ask it to research trending content, and it dispatches to the right tool and answers in place.

---

### Brand Voice Tab

**Extracted Profile**
The brand voice profile made legible: tone descriptors, signature vocabulary, avoided terms, and signature phrases, broken out per content pillar rather than averaged into one generic voice.

**Brand Drift Watchdog**
Paste a caption that hasn't been posted yet, and a dedicated Granite call (#19) flags exactly where it slides off the extracted voice — which signature phrases are missing, which avoided terms slipped in — before it goes live, not after.

---

### Generate Tab

**Blank Page Solver**
Describe a moment in plain language — *"It's Friday evening and we just pulled the last batch of Pistachio Rose Bomboloni"* — and Granite identifies the emotional core (#6), matches it to your best-fit content pillar, and generates three distinct creative directions (#7). Pick one, and it auto-populates the Caption Brief with the right voice and feel.

**Caption Brief**
Enter a product, occasion, and desired feel. Granite (#2) generates three caption variants, each with reasoning for why it fits your brand patterns. Every variant can be regenerated with diversity constraints (no repetition from previous runs). Save any caption to the Workbench.

**The Drift Test**
Given the same creative brief, generates a caption from a generic, brand-blind baseline model *and* a StyleSync caption (Granite #2, full brand + memory grounding), then scores both against the creator's real brand-voice vocabulary — matched signature phrases, avoided-term violations, an honest 0–100 fidelity score. For @hot_cakesbakes, the baseline typically scores around 10/100 ("significant drift"); StyleSync scores around 40/100 on the identical brief. It's credible precisely because it's comparative and reproducible — the same prompt, two outputs, scored side by side — rather than a claim the product makes about itself.

**Resonance Simulator**
Three personas grounded in the account's *own* real cluster-engagement data — a superfan, a scroll-happy skimmer, a skeptic — react to a draft caption before it's ever posted (Granite #16), and a synthesis call picks a favorite plus one concrete fix. A pre-mortem, not a post-mortem.

**Brand Guardian**
An adversarial critique-and-refine loop for one already-generated caption (Granite #18): a harsh in-character reviewer flags generic "obviously-AI" language, avoided-term slips, and tone mismatches; a separate refine call rewrites to address exactly those issues. Hard-capped at two rounds — an 8B model doesn't reliably converge past that, so best-so-far is a legitimate, surfaced outcome, not a hidden failure.

**Image Direction**
Select a caption and get a Midjourney/DALL-E ready art direction prompt (Granite #3) — color palette, composition, mood, subject framing — calibrated to your brand's visual identity extracted from your content history.

**Script Studio**
Paste a high-performing caption and performance metrics. Granite (#9) generates a full production script for your chosen format — Reel (hook + voiceover + shot list), Carousel (cover slide + slides + CTA), Static (headline + visual direction), or Story — with a one-click fan-out that produces all four formats from a single winning caption. Save to Workbench.

---

### Diagnose Tab

**Why Engine**
Paste any post caption + Instagram Insights metrics (views, reach, likes, comments, shares, saves), or expand any real post already in the account's history. Granite (#4) runs a post-mortem against your brand voice profile and produces:
- A verdict: Succeeded / Underperformed / Failed
- A diagnosis: specifically what worked or didn't, against your brand patterns
- A brand voice gap analysis: where the post drifted from your established voice

Every diagnosis is gated by an honest confidence score (Granite #15 + a deterministic signal check) rather than asserting certainty an 8B model doesn't have — low-confidence verdicts are labeled "verify before publishing," not hidden.

**Recovery Brief** *(chained automatically on underperforms and failures)*
When the Why Engine diagnoses a failure inside the Diagnose tab, it immediately chains into a second Granite call (#10) and generates a recovery strategy: a new hook written at a different angle, a recommended format with reasoning, and a 150-word recovery script in your brand voice, saved to Workbench.

**Recovery Agent** *(proactive, from anywhere in the app)*
A separate, unprompted trigger: tag *any* saved Workbench asset "underperformed" or "failed" — from Generate, from Agents, from wherever it landed — and the Recovery Agent kicks off on its own. It runs the Why Engine on the caption, and if the diagnosis is confident, produces a full fresh recovery post through the multi-agent orchestrator's pipeline and drops it back into the Workbench; if the diagnosis is too thin to act on, it escalates for human review instead of fabricating a fix. JARVIS can announce a completed recovery proactively the next time you talk to it.

---

### Strategy Tab

**Voice Timeline**
A month-by-month breakdown of how your content distribution has shifted across your clusters. Granite (#5) narrates the creative arc — where you started, what dominated each period, and how your voice has evolved. For @hot_cakesbakes: from 57% basic product showcase (Oct 2025) to a March 2026 Bomboloni peak (48% of all content), then a deliberate diversification.

**Strategic Insights**
Two rankings per cluster: **volume rank** (how often you post this type) vs **richness rank** (how linguistically and conceptually rich this cluster's vocabulary is). The gap between them is your strategy signal.

- High richness, low volume = **underutilized territory** — your most distinctive content type that you're not investing in
- High volume, low richness = **over-invested** — you're repeating yourself in your least distinctive voice

Granite (#8) synthesizes these gaps into a strategic brief: what to lean into, what to pull back from, and why.

**Boost Advisor**
Instagram gives you a Boost button. It doesn't tell you which post to boost. StyleSync answers this with a dedicated Granite invocation (#11) that cross-references engagement data (average views, saves, comments per cluster) with richness and volume ranks to produce a single concrete recommendation:

- Which cluster's post to boost and exactly which hook
- Why that cluster has the highest return on paid amplification
- Which Instagram objective to select and how to target
- Which cluster NOT to boost and why it would waste budget

For @hot_cakesbakes: Bomboloni content (C4) averages 1,720 views, 67 saves, and an 11.1% engagement rate — 2.1× the account average. Its richness rank is #1. StyleSync recommends boosting it over Homemade Classics (C0, 820 avg views, lowest engagement rate), where spend would underperform.

**This Week**
A hero recommendation combining the Strategic Insights gap, the latest Weekly Brief Agent batch, and a Self-Improving Playbook experiment (see Agents Tab) to try over the next two weeks.

---

### Agents Tab

**Autopilot**
A goal-directed, not script-following, multi-agent system. Pick a post count, platform, and confidence gate (70/80/90), and Autopilot's THINK phase gathers evidence — brand gaps, live trends via the Trend Agent (Granite #22), past performance from episodic memory — and reasons over it to produce its own weekly plan: which pillars, which angles, and why. If it hits a genuine strategic fork it can't resolve from the evidence, it asks the creator one clarifying question and waits, rather than guessing. ACT then drafts each planned post through the seven-agent orchestrator's pipeline (draft → critic → refine → score-gate → image), streaming a live reasoning trace the whole way so the plan is watched happening, not just delivered.

The loop is **goal-directed, not count-bounded**: it exits when the critic approves *and* confidence clears the creator's gate, treats a detected plateau (Δ ≤ 2 across 3 cycles) or a factual gap as a hard stop rather than grinding on, and caps at 8 cycles for safety. The convergence reason is surfaced in the UI, not hidden.

**Self-Improving Playbook**
The one agent that changes its own behavior. It reads the account's own tagged post outcomes (wins vs. misses, with their hook patterns and signal metrics) from episodic memory, reasons about what actually distinguishes the two *for this brand specifically*, and rewrites the procedural-memory playbook that the Copywriting agent reads on every future generation — a closed self-improvement loop, not a static prompt.

---

### Inbox Triage Tab

**Comment & DM Triage**
Paste up to 20 real comments or DMs. Granite (#20, batched in chunks of up to 5 messages per call) classifies each — order inquiry, compliment, spam — and drafts an on-brand reply for every legitimate message, correctly skipping spam rather than replying to it. An Error Classifier (Granite #21) inside the same critique loop maps any malformed model response to a typed error instead of silently discarding it.

---

### Content Workbench

A persistent SQLite scratchpad that survives refreshes and sessions. Every generated caption, script, image direction, recovery brief, and Autopilot-produced post can be saved here, tagged by which tab produced it (including `recovery_agent` for autonomous recoveries). Star assets you want to return to. Track outcomes — and tagging an outcome "underperformed" or "failed" is exactly what triggers the Recovery Agent. The Workbench is what makes StyleSync a workflow tool that closes its own loop, not just a one-shot generator.

---

## The IBM Granite Architecture

StyleSync runs **22 coordinated IBM Granite 3.1 8B invocations** — every single one running locally via Ollama, with zero cloud API calls during inference.

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
| 9 | Script Generator | Full Reel/Carousel/Static/Story production script |
| 10 | Recovery Brief | Recovery hook + format + script chained from Why Engine failure |
| 11 | Boost Advisor | Engagement-weighted recommendation for which post/cluster to boost |
| 12 | Voice Refiner | Refines a raw spoken caption idea into polished on-brand copy, read back aloud |
| 13 | JARVIS Agent | Multi-turn conversational brain — intent routing + natural spoken response |
| 14 | Inspiration Synthesizer | Web research snippets → 3 brand-adapted content ideas |
| 15 | Confidence Scorer | Directional confidence gate layered onto Why Engine / diagnosis outputs |
| 16 | Resonance Simulator | 3 audience personas react to a draft caption + synthesis pick |
| 17 | Weekly Brief Planner | Background batch of on-brand ideas for the most underused pillar |
| 18 | Brand Guardian | Adversarial critique + refine pass on one caption, capped at 2 rounds |
| 19 | Brand Drift Watchdog | Flags an unposted caption drifting from the extracted brand voice |
| 20 | Comment/DM Triage | Classifies + drafts replies for up to 20 comments/DMs per batch |
| 21 | Error Classifier | Maps a malformed critique-loop response to a typed error |
| 22 | Momentum & Audience Agent | Live trend + audience-momentum evidence feeding Autopilot's plan |

These are not 22 identical calls with different prompts. Each invocation operates on a different data shape, a different reasoning task, and a different output structure. Together they form a closed feedback loop: your history informs your generation, your generation outcomes feed back into your diagnosis, your diagnosis informs your next creation — and, through Autopilot and the Self-Improving Playbook, the loop now closes without a human re-triggering each step.

**The JARVIS Voice Agent (Granite #13 + #14):** A persistent floating AI agent accessible from every page. It holds multi-turn conversations in natural language — by voice (push-to-talk) or text — and knows the creator's brand deeply. Ask it a question about your best-performing cluster, say "write me a caption for fresh bomboloni," or ask it to "research trending bakery content" — JARVIS dispatches to the right tool, synthesizes the result, and responds in voice. It can generate captions (Granite #2), run post-mortems (Granite #4), trigger a recovery on your last flop, search the web for creator inspiration and synthesize it into 3 brand-adapted ideas (Granite #14), read and save assets to the Workbench, and answer any brand strategy question from the full profile. No audio ever leaves the machine — browser SpeechRecognition + SpeechSynthesis stay on-device; only the text transcript reaches local FastAPI → local Ollama.

**The multi-agent layer:** Seven specialized agents (`src/agents/`) — BrandVoice, Copywriting, Visual, Analytics, Community, Critic, and Trend — are coordinated by `StyleSyncOrchestrator`, which selects a topology per task (parallel, hierarchical, sequential, or flat) rather than running one fixed pipeline. Autopilot sits above that orchestrator as a goal-directed planner; several of the 22 numbered Granite invocations above (notably #18, #21, #22) live inside this agent layer rather than being called directly by a router.

**Why local matters:**
- No API cost. No rate limits. No dependency on external availability.
- Your posting history and brand data never leave your machine.
- The demo runs identically in a room with no internet.

---

## Competitive Landscape

### StyleSync vs Octupie

[Octupie](https://www.octupie.com/) is the closest competitor — an Instagram-focused tool backed by IIT Madras founders and Microsoft Startup support. It tracks competitor/niche accounts, detects outlier posts that beat each account's baseline, decodes the hook/format that drove the spike, and generates a voice-matched script.

**Their thesis:** *"Turn what's winning in your niche into scripts that sound like you."*
**Our thesis:** *"One profile, extracted from your real data, runs your entire week."*

| Dimension | Octupie | StyleSync |
|-----------|---------|-----------|
| Data source | Competitor public accounts | Your own historical posts |
| Core question | What's winning in my niche? | What's authentic to me? |
| Voice matching | Trained on your catalogue | Extracted from your cluster patterns |
| Post diagnosis | Not offered | Why Engine (Granite #4) |
| Recovery strategy | Not offered | Recovery Brief (Granite #10) + autonomous Recovery Agent |
| Creative evolution | Not tracked | Voice Timeline (Granite #5) |
| Content strategy | Not offered | Strategic Insights (Granite #8) |
| Boost Advisor | Not offered | Granite #11 — which post to boost + why |
| Autonomous planning | Not offered | Autopilot — 7-agent orchestrator, goal-directed weekly plan |
| Inbox / DM triage | Not offered | Inbox Triage (Granite #20), spam correctly skipped |
| Account sync | Manual re-scrape | OAuth connect + background poller, real-time |
| AI stack | Unspecified | IBM Granite 3.1 8B, 22 invocations, local |
| Privacy | Requires Instagram scraping | Fully local, no external calls |

**The strategic gap Octupie misses:** If you optimize entirely on competitor signal, you converge toward what everyone else is doing. StyleSync answers a different question — not "what's popular?" but "what's *yours*, and where have you drifted from it?"

**The gap StyleSync currently has:** We don't surface what's trending in your niche. Octupie does this. We've consciously decided this is a different product, not a missing feature — because a scraping dependency introduced 6 weeks from a hard deadline is a liability, not a feature.

---

### StyleSync vs ChatGPT / Generic AI Writers

ChatGPT generates captions from whatever you tell it. It has no knowledge of your brand voice, your content clusters, your performance history, or your audience relationship. It will write "indulgent and intimate" copy for a bakery because you said so — but it has no idea that your Cluster 1 vocabulary consistently uses *quiet* sensory language and avoids superlatives, or that posts using "linger" and "unhurried" in the same sentence outperform everything else in your catalog by 40%.

StyleSync's generation is not prompted by the user's self-description. It's derived from the creator's observed behavior across their real posting history. That's the difference between "write in my voice" and "write from my voice" — and the Drift Test makes that difference a measured score instead of an assertion.

---

### StyleSync vs Generic Analytics Tools (Socialinsider, vidIQ, Later Analytics)

Analytics tools answer: *"What happened?"*
StyleSync answers: *"Why did it happen, and what do you do next?"*

Generic analytics show a creator that their Reel on a Tuesday got 30% more views than their average. They show no causal explanation, no brand voice context, no recovery strategy, and no generation capability. The creator leaves with a data point and no action.

StyleSync turns the same signal into: a Why Engine verdict, a brand voice gap analysis, a Recovery Brief (or an autonomously-triggered Recovery Agent post) with a specific new hook and script, and a Strategic Insights recommendation about which content type to invest in next — or, on Autopilot, a whole week planned around it without being asked.

---

## The Engagement Plateau Problem

**Scenario:** A creator has posted 100+ times across Reels, carousels, and statics. Everything averages about 1,000 views. Nothing spikes. The Why Engine, which explains *variance*, is useless here because there is no variance to explain.

This is a **systemic account problem**, not a post-level problem. It requires a portfolio-level audit.

StyleSync's clustering data already contains the raw material to answer this:
- Which content cluster is driving the highest average engagement?
- Which cluster has the richest vocabulary (highest brand potential) but the lowest post volume?
- Where have they been over-posting in their least distinctive voice?

The **Boost Advisor** (Granite #11, shipped) uses this data to answer the exact question Instagram's native Boost button never answers: *which post should I put money behind?*

Output: "Your Cluster 1 content (richest vocabulary, currently 3 posts vs 40 for Cluster 0) averages 1.4x your account baseline. This specific post has your strongest hook structure. Boost it to amplify your best-performing creative territory, not your most frequent one."

This was built as a zero-new-data-source feature — everything it needs was already in `clusters.json`. It reused existing infrastructure and added one Granite invocation.

---

## The Demo Arc

The full narration-level script lives in [`docs/demo-script.md`](demo-script.md) — 160 seconds, 20s under the 180-second cap, built around one throughline that should stay audible in every beat: *"same profile, different job."* Condensed:

1. **Hook** (0:00–0:12) — five scattered tools, generic AI, brand drift. One profile runs the whole week.
2. **Today** (0:12–0:22) — the app already knows what to post, with a caption and script pre-filled.
3. **Dashboard** (0:22–0:39) — home base: KPIs, Top Posts, Engagement-by-Pillar, Best-Day-to-Post, and a live Weekly Brief Agent run.
4. **Brand Voice** (0:39–0:52) — the extracted profile made legible, plus a live Drift Watchdog catch on an off-brand caption.
5. **Generate** (0:52–1:24, the longest beat) — Blank Page Solver → Caption Brief → **the Drift Test** (baseline ~10/100, StyleSync ~40/100, identical brief) → Resonance Simulator → Brand Guardian → Script Studio's one-click 4-format fan-out.
6. **Diagnose** (1:24–1:40) — a real winning post and a real losing post, each diagnosed; a manual-paste path gated by an honest confidence score.
7. **Strategy** (1:40–1:56) — this week's hero stat, a sourced side-by-side scorecard, and a Playbook experiment to try next.
8. **Agents → Inbox Triage** (1:56–2:31) — Autopilot planning a week live with a visible reasoning trace and a convergence badge, then Inbox Triage classifying and replying to twenty real comments in one batch call, correctly skipping spam.

**Close** (2:31–2:40): *"One profile, extracted from your real data, runs your entire week — numbers to voice to writing to strategy to automation. That's StyleSync."*

---

## Stack

| Layer | Technology |
|-------|-----------|
| AI | IBM Granite 3.1 8B via Ollama (local) |
| AI framework | LangChain (langchain-ollama) |
| Agent memory | ChromaDB (semantic, episodic, procedural collections) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Clustering | scikit-learn K-Means |
| Backend | FastAPI (Python) |
| Frontend | Next.js 16 (App Router), React Query, TypeScript |
| Persistence | SQLite (workbench), JSON (brand profile, clusters) |
| Styling | Tailwind CSS, quiet-luxury design system |

**Data used for demo:** @hot_cakesbakes — artisanal bakery, Navi Mumbai. 217 posts, 5 content clusters, spanning Oct 2025 onward.
