# StyleSync — New Agentic Features

Grounded in deep research on the AI-content-tool competitive landscape (Flick, Predis.ai, Jasper, Instagram's own Edits AI assistant) plus a technical feasibility review against IBM Granite 3.1 8B running locally via Ollama, solo dev, ~3 weeks to the July 31 2026 deadline.

**Key research findings that shaped this list:**
- StyleSync's core mechanic (ingest-your-posts → brand-voice profile → generation) already has market precedent — Flick ships brand-voice-learning captions today. Not a differentiator on its own.
- Instagram's Edits app is shipping an AI assistant (reported June 2026) that turns performance data directly into content ideas, explicitly to reduce reliance on external tools. "Analytics → ideas" is becoming table stakes, not a differentiator.
- StyleSync's real, structural, uncopiable moat: **zero cloud inference — everything runs locally.** Meta/Jasper/Predis cannot match this; their business models require cloud data collection.
- Published agent-design research names three recurring failure modes in human-agent handoff: lost state when workflows pause, weak escalation for low-confidence actions, unclear confidence signals. Directly informed Confidence-Scored Outputs below.
- Small (8B-class) local models are not well-calibrated at numeric self-scoring, and iterative critique/refine loops don't reliably converge. Both considerations shaped scope and UI framing below.

---

## Built — Phase 1 (core features)

### 1. Confidence-Scored Outputs
**Pain point:** every competitor tool outputs confident-sounding text regardless of actual quality; users can't tell what to trust or double-check.  
A lightweight Granite self-critique pass runs after Why Engine and Boost Advisor generate their output, scoring confidence and surfacing a visible badge. Score is framed as directional ("Verify before publishing"), not a precise percentage claim.

### 2. Closed-Loop Repurposing Orchestrator
**Pain point:** when a post succeeds, the founder has to manually repurpose it into other formats.  
Why Engine detects `verdict == "succeeded"` → automatically fans out to the existing Script Generator 3 times (Reel/Carousel/Static) as a background job → drafts land directly in the Workbench.

### 3. Resonance Simulator
**Pain point:** "post and pray" — creators have no pre-publish test.  
Three critic personas grounded in the creator's own real cluster engagement data react to caption variants; a synthesis call aggregates into a "predicted resonance" pick + one concrete actionable fix. Framed as a directional signal, not a calibrated prediction.

### 4. Weekly Brief Agent (+ proactive JARVIS hook)
**Pain point:** founders don't have time to plan; they open the app to a blank page every time.  
Background job scouts the underutilized content pillar, chains through Blank Page Solver → Caption → Image Direction pipeline for 2-3 draft scenarios, writes them to the Workbench, and flags a proactive JARVIS nudge on next open ("I found something").

---

## Built — Phase 2 (formerly roadmap)

These four features were listed as "Roadmap / future work" in the original plan. All four shipped.

### 5. Brand Guardian Courtroom
Adversarial critique→refine loop on one already-generated caption. Hard-capped at 2 rounds with "best-so-far" as a first-class outcome (by design — an 8B critic can flag a different issue in round 2, so best-of-2 is the honest framing, not a failure to converge).

### 6. Brand Drift Watchdog
Paste recent posts → auto-detects the nearest content pillar via embedding similarity → Granite explains specifically what's drifted and what's still on-brand. Detects voice erosion before engagement drops.

### 7. Comment/DM Triage + Draft Replies
Paste up to 20 comments/DMs → Granite classifies (order inquiry / compliment / complaint / spam) → drafts a brand-voice reply for each. New `/app/triage` studio tab. Mandatory banner: no live Instagram DM API — this is a "paste your messages" batch tool, not live automation.

### 8. Closed-loop performance → generation learning
Real post-performance outcomes (tagged in the Workbench) calibrate future caption generation for that content pillar. A "Calibrated using N real outcomes" badge appears on the Create tab when outcomes exist for the selected pillar. Uses existing `CaptionGenerator` (zero new Granite invocations) with a new `performance_context` kwarg.

---

## Built — Phase 3 (multi-agent architecture)

### 9. Goal-Directed Multi-Agent Orchestrator
**Pain point:** single-pass generation has no quality guarantee; the creator can't specify what "good enough" means before running.

A full 7-agent architecture (`BrandVoiceAgent`, `CopywritingAgent`, `CriticAgent`, `AnalyticsAgent`, `CommunityAgent`, `VisualAgent`, `TrendAgent`) coordinated by a `StyleSyncOrchestrator` with adaptive topology selection (parallel / hierarchical / sequential / flat depending on task type).

The key Phase 3 addition is **goal-directed termination**: instead of exiting after a fixed cycle count, the campaign loop exits when `critic.approved AND confidence ≥ threshold`. The creator specifies the quality gate (70/80/90) and product details in a Campaign Brief modal before running. The loop also detects plateaus (score Δ ≤ 2 over 3 consecutive cycles → flag for human review) and handles factual gaps as a hard stop.

**Convergence outcomes surfaced in the UI:**
- `goal_met` — confidence threshold cleared
- `plateau` — quality stalled, human review suggested
- `factual_gap` — agent flagged something it can't verify
- `max_cycles` — safety ceiling (8) reached

**Trend-to-copy handoff:** when a trend briefing exists, its top hooks are injected into the `desired_feel` field before the first copywriting call, closing the loop between Discover-tab trend research and Agent Studio campaign generation.

**ChromaDB memory:** three collections (semantic brand voice, episodic past outcomes, procedural platform rules) persist across runs and inform agent behavior.
