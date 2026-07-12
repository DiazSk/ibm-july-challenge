# StyleSync — New Agentic Features

Grounded in deep research on the AI-content-tool competitive landscape (Flick, Predis.ai, Jasper, Instagram's own Edits AI assistant) plus a technical feasibility review against IBM Granite 3.1 8B running locally via Ollama, solo dev, ~3 weeks to the July 31 2026 deadline.

**Key research findings that shaped this list:**
- StyleSync's core mechanic (ingest-your-posts → brand-voice profile → generation) already has market precedent — Flick ships brand-voice-learning captions today. Not a differentiator on its own.
- Instagram's Edits app is shipping an AI assistant (reported June 2026) that turns performance data directly into content ideas, explicitly to reduce reliance on external tools. "Analytics → ideas" is becoming table stakes, not a differentiator.
- StyleSync's real, structural, uncopiable moat: **zero cloud inference — everything runs locally.** Meta/Jasper/Predis cannot match this; their business models require cloud data collection.
- Published agent-design research names three recurring failure modes in human-agent handoff: lost state when workflows pause, weak escalation for low-confidence actions, unclear confidence signals. Directly informed Confidence-Scored Outputs below.
- Small (8B-class) local models are not well-calibrated at numeric self-scoring, and iterative critique/refine loops don't reliably converge. Both considerations shaped scope and UI framing below.

---

## Building now

### 1. Confidence-Scored Outputs
**Pain point:** every competitor tool outputs confident-sounding text regardless of actual quality; users can't tell what to trust or double-check.
**Differentiation:** directly implements the one well-verified piece of agent-design research (unclear confidence signals is a named failure mode) — a legitimately uncommon feature in this space.
**Workflow:** a lightweight Granite self-critique pass runs after Why Engine and Boost Advisor generate their output, scoring how confident the assessment is and why, surfaced as a visible badge.
**Feasibility:** quick win. Cheap (`num_predict=150`), non-fatal (wrapped in try/except, never blocks the primary response), reuses the exact chained-secondary-call pattern already proven by the Recovery Brief auto-chain.
**Caveat:** small local models are not well-calibrated numeric scorers — UI copy frames the score as directional ("Verify before publishing"), not a precise percentage claim.

### 2. Closed-Loop Repurposing Orchestrator
**Pain point:** when a post succeeds, the founder has to manually go repurpose it into other formats (Reel, Carousel, static) — real, tedious admin work with no help from any tool in the reviewed competitive set.
**Differentiation:** none of Flick/Predis/Jasper close this loop autonomously; the platform *acts* on a success signal rather than just reporting it.
**Workflow:** Why Engine detects `verdict == "succeeded"` → automatically (no button click) fans out to the existing Script Generator 3 times (Reel/Carousel/Static formats) as a background job → drafts land directly in the Workbench, ready to review.
**Feasibility:** quick win — cheapest of the four, since it needs **zero new Granite classes**, entirely reusing the existing `ScriptGenerator`. Only new work is orchestration (a background job) and the auto-trigger condition.
**Cut for scope:** a "Twitter/X-style thread" format was considered but dropped — `ScriptGenerator`'s prompt template only supports Reel/Carousel/Static today, and adding a 4th format is out of scope for the timeline.

### 3. Resonance Simulator
**Pain point:** "post and pray" — creators have no way to pre-test a caption before publishing; the only diagnosis tool (Why Engine) is entirely after-the-fact.
**Differentiation:** three critic personas are grounded in the creator's own real `cluster_engagement` data (a "Devotee" persona built from the highest-engagement cluster's actual patterns, a "Skeptic" from the lowest, etc.) rather than generic archetypes — ties the differentiator to StyleSync's one truly unique asset (its own historical clustering), which no competitor can copy since none of them do that clustering step.
**Workflow:** draft captions → 3 persona-critic Granite calls (each reacting to all 3 captions at once) → a synthesis call aggregates into a "predicted resonance" pick + one concrete actionable fix (e.g. "move the hook earlier — the Casual Scroller persona dropped off after sentence one").
**Feasibility:** quick win, best live-demo moment — 4 Granite calls total (~75-95s), reuses the exact multi-persona-then-synthesize pattern already proven safe in this codebase.
**Caveat:** "predicted resonance" is framed in UI copy as a relative/directional signal, not a scientifically calibrated prediction — 8B models are not reliable numeric self-assessors. Also: don't assume the 3 persona calls actually execute in parallel — Ollama's real concurrency behavior on this hardware is unverified, so this is built as sequential calls with explicit "consulting three personas..." loading copy.

### 4. Weekly Brief Agent (+ proactive JARVIS hook)
**Pain point:** founders don't have time to plan; they open the app to a blank page every time, and have no visibility into emerging trends outside their own feed.
**Differentiation:** proactive, not reactive — produces finished draft posts in the Workbench autonomously, overnight/in the background, rather than a single reactive answer to a single question (which is all Instagram's own Edits AI assistant will do). JARVIS proactively greets the founder with "I found something" the next time they open it, instead of always waiting to be asked — a genuinely agentic UX pattern, not just a chat window.
**Workflow:** background job pulls the Strategic Insights' underutilized-but-rich cluster → runs a web search for relevant trends → chains through the existing Blank Page Solver → Caption → Image Direction pipeline for 2-3 draft scenarios → lands them in the Workbench → flags a one-time "pending notice" that JARVIS surfaces proactively on next open.
**Feasibility:** stretch — the biggest of the four, the only one needing its own background-job infrastructure, a new Workbench asset type, and new Dashboard UI. Built last so if time runs out, the three cheaper/safer features still ship complete.
**Cut for scope:** the original idea included continuous background monitoring on a recurring schedule and full-page web scraping (BeautifulSoup/ScrapeGraph) for deeper trend signal. Both cut: there is no scheduler (APScheduler/Celery/cron) anywhere in this codebase — building real recurring execution is new infrastructure, not a config flag — so this is on-demand-triggered instead, and full-page scraping is fragile/risky against social platforms and unnecessary given the existing, reliable DuckDuckGo snippet search already wired into JARVIS.

---

## Roadmap / future work (not building now)

### 5. Brand Guardian Courtroom (adversarial draft → critique → refine loop)
**Pain point:** single-pass generation is prone to generic, "obviously-AI" language that audiences actively reject.
**Why it's not being built now:** genuinely the most exciting idea reviewed — watching an AI draft, get told it's not good enough, and rewrite itself live is the clearest "this is really agentic" demo moment available. Cut only for real, well-understood risk: iterative critique/refine loops with an 8B local model don't reliably converge (a critique can flag a *different* issue in round 2 even after round 1's issue is fixed, since the judgment itself is somewhat noisy), and it stacks the most latency of any feature reviewed (each round = 2 more Granite calls). If time allows after the 4 features above, revisit with a hard 2-round cap and "return best-so-far" as a first-class outcome, applied to refining one already-generated caption rather than drafting from scratch.

### 6. Brand Drift Watchdog
**Pain point:** brand voice erodes slowly over months without anyone noticing until engagement drops.
**Why differentiated:** nobody in the reviewed competitive set does voice-drift detection over time — they're all generation-forward, not monitoring-forward.
**Workflow sketch:** paste/re-scrape recent posts → compare against the locked brand profile → Granite explains *specifically* what's drifted, not just a generic diagnosis.
**Feasibility:** stretch — reuses existing profile-extraction/embedding infrastructure, so it's a real stretch, not a wild one.

### 7. Comment/DM Triage + Draft Replies
**Pain point:** the actual, lived pain point for a business like a home bakery — people DM to place orders and founders lose sales because they can't reply fast enough. None of the competitor tools reviewed touch inbound messages at all.
**Workflow sketch:** paste a batch of comments/DMs → Granite classifies (order inquiry / compliment / complaint / spam) → drafts a brand-voice reply for each → founder approves/edits/sends.
**Honest limitation:** no live Instagram DM API access without platform approval — the real build is a "paste your messages" batch tool, not live automation. Worth saying plainly rather than overclaiming live integration.

### 8. Closed-loop performance → generation learning
**Distinct from Feature 2 (Closed-Loop Repurposing) above** — that one immediately fans out a *successful* post into more formats. This one is the more ambitious idea: real post-performance data (once reported back) automatically feeds into and adjusts *future* generation prompts, so the system gets better at your voice over time instead of just repeating whatever the initial brand profile said.
**Why it's roadmap, not build-now:** needs new persistent state design threading performance signal into every future generation call — the hardest one to get right in the remaining time, and the best "what's next" pitch for a follow-up version.
