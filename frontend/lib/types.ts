// Brand
export interface BrandProfile {
  brand_name: string;
  handle: string;
  timezone: string;   // IANA name — the audience's zone, not the viewer's

  content_pillars: string[];
  tone_descriptors: string[];
  signature_phrases: string[];
  avoided_terms: string[];
  recurring_words: string[];
  visual_style_notes: string;
  target_audience: string;
}

export interface Cluster {
  cluster_id: number;
  pillar: string;
  post_count: number;
  signature_phrases: string[];
  recurring_words: string[];
  tone_descriptors: string[];
  avoided_terms: string[];
  sample_captions: string[];
}

export type ClustersData = Record<string, Cluster>;

// Create tab
// A past post covering the same ground as the idea being written.
// `recommendation` is the point: repeating a winner is good strategy, repeating
// a flop is the actual mistake — so each match says which it was.
export interface SimilarPost {
  shortcode: string;
  hook: string;
  timestamp_utc: string;
  cluster_id: number;
  pillar: string;
  similarity: number;        // raw cosine — for debugging, never render it
  closeness: string;         // "almost identical to" | "very close to" | "similar to"
  reach: number;
  recommendation: "repeat" | "avoid" | "unknown";
  note: string;
}

export interface MomentAnalysis {
  emotional_core: string;
  business_signal: string;
  best_cluster_id: number;
  cluster_reason: string;
  similar_posts?: SimilarPost[];   // absent on older responses; [] when novel
}

export interface Direction {
  direction_title: string;
  angle: string;
  tone_note: string;
}

export interface Caption {
  caption: string;
  reasoning: string;
}

export interface CaptionsGenerateResponse {
  captions: Caption[];
  used_real_outcomes: number;
}

export interface ImagePromptResult {
  prompt: string;
  style_notes: string;
}

// Analyze tab
export interface WhyEngineRequest {
  caption: string;
  post_type: "Reel" | "Carousel" | "Static";
  views: number;
  reach: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  avg_watch_time_secs?: number;
  cluster_id: number;
  visual_description?: string;   // from POST /api/analyze/describe-image
}

export type VerdictLabel = "Succeeded" | "Underperformed" | "Failed";

export interface WhyEngineResult {
  verdict: string;
  verdict_label: VerdictLabel;
  diagnosis: string;
  what_worked: string;
  what_failed: string;
  brand_voice_gap: string;
  change_next_time: string;
  recovery_brief?: {
    new_hook: string;
    recommended_format: "Reel" | "Carousel" | "Static";
    recovery_script: string;
    reasoning: string;
  };
  confidence?: { score: number; rationale: string };
  repurpose_job_id?: string;
}

export interface RepurposeStatus {
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  batch_id?: string;
}

// Resonance Simulator
export interface PersonaReaction {
  persona: string;
  predicted_resonance: number;
  emotional_polarity: string;
  critique_per_caption: string[];
}
export interface ResonanceSynthesis {
  winner_index: number;
  predicted_resonance_score: number;
  reasoning: string;
  top_actionable_fix: string;
}
export interface ResonanceResult {
  persona_reactions: PersonaReaction[];
  synthesis: ResonanceSynthesis;
}

// Brand Guardian Courtroom
export interface GuardianCritique {
  verdict: "approve" | "needs_revision";
  issues: string[];
  severity: "none" | "minor" | "major";
  reasoning: string;
}
export interface GuardianRound {
  round: number;
  caption: string;
  critique: GuardianCritique;
}
export interface GuardianReviewResult {
  final_caption: string;
  converged: boolean;
  rounds_used: number;
  best_so_far: boolean;
  history: GuardianRound[];
}

// Brand Drift Watchdog
export interface DriftSimilaritySignal {
  mean_similarity: number;
  sample_size_used: number;
  direction: "similar" | "diverging" | "very_different";
}
export interface DriftCheckResult {
  nearest_cluster_id: number;
  cluster_label: string;
  similarity_signal: DriftSimilaritySignal;
  drift_detected: boolean;
  drift_summary: string;
  specific_changes: string[];
  still_on_brand: string[];
  severity: "none" | "mild" | "significant";
}

// Autopilot — autonomous weekly content agent (Agents page)
export interface AgentTraceEntry {
  phase: string;   // start | think | act | done
  label: string;
  detail?: string;
  post?: number;
}

export interface AutopilotPost {
  index: number;
  cluster_id: number;
  pillar: string;
  angle: string;
  rationale: string;
  caption: string;
  confidence: number | null;
  convergence_reason: string;
  image_prompt: string;
  needs_review: boolean;
}

export interface PendingQuestion {
  question: string;
  options: string[];
}

export interface AgentRunState {
  status: "running" | "awaiting_input" | "done" | "error";
  trace: AgentTraceEntry[];
  reasoning: string;
  posts: AutopilotPost[];
  summary: string;
  pending_question: PendingQuestion | null;
  error: string | null;
}

// Self-Improving Playbook Agent
export interface PlaybookRule {
  rule_name: string | null;
  text: string;
  source: string;
}
export interface ReflectRule {
  rule_name: string;
  instruction: string;
}
export interface ReflectResult {
  learned: string;
  rules: ReflectRule[];
  applied: number;
  winners: number;
  losers: number;
}
export interface ReflectJob {
  status: "running" | "done" | "error";
  result: ReflectResult | null;
  error: string | null;
}

// Autonomous Recovery Agent
export interface RecoveryNotice {
  pending: boolean;
  needs_review?: boolean;
  original_caption?: string;
  recovery_caption?: string;
  confidence?: number | null;
  cluster_label?: string | null;
}

// The Drift Test — head-to-head brand-voice match (Create tab)
export type VoiceMatchLabel = "closely matches" | "some drift" | "significant drift";
export type TopicalLabel = "on topic" | "loosely related" | "off topic";

export interface DriftSide {
  caption: string;
  score: number; // brand-voice fidelity 0-100
  match_label: VoiceMatchLabel;
  matched_words: string[];
  matched_phrases: string[];
  avoided_violations: string[];
  topical_label: TopicalLabel;
}

export interface DriftCompareResult {
  baseline: DriftSide;
  stylesync: DriftSide;
}

// Comment/DM Triage
export interface TriageResult {
  message_index: number;
  original_message: string;
  category: "order_inquiry" | "compliment" | "complaint" | "spam" | "uncertain";
  drafted_reply: string;
  reasoning: string;
}
export interface TriageBatchResponse {
  results: TriageResult[];
  total: number;
}

// Real Instagram inbox (comments)
export interface InboxComment {
  id: string;
  text: string;
  username: string;
  timestamp: string;
  media_permalink: string;
  media_shortcode: string;
}
export interface InboxCommentsResponse {
  comments: InboxComment[];
  total: number;
}

// Weekly Brief Agent
export interface WeeklyBriefStatus {
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  batch_id?: string;
  n?: number;
  cluster_label?: string;
  notified?: boolean;
}
export interface WeeklyBriefDraft {
  batch_id: string;
  scenario_index: number;
  scenario_text: string;
  rationale: string;
  caption: string;
  image_prompt: string;
  style_notes: string;
}
export interface WeeklyBriefPendingNotice {
  pending: boolean;
  job_id?: string;
  batch_id?: string;
  n?: number;
  cluster_label?: string;
}

// Workbench
export interface WorkbenchAsset {
  id: string;
  asset_type: string;
  cluster_label: string | null;
  cluster_id: number | null;
  content: string | Record<string, unknown>;
  pinned: boolean;
  source_tab: string | null;
  actual_outcome: string | null;
  recovery_brief_generated: boolean;
  created_at: string;
}

// Discover tab
export interface MonthlyPct {
  month: string;
  C0: number;
  C1: number;
  C2: number;
  C3: number;
  C4: number;
}

export interface VoiceTimelineResult {
  monthly_pct: MonthlyPct[];
  narrative: string;
  key_shift: string;
  pillar_labels: Record<string, string>;
}

export interface ClusterScore {
  cluster_id: number;
  pillar: string;
  post_count: number;
  volume_pct: number;
  volume_score: number;
  richness_score: number;
  richness_score_display: number;
  volume_rank: number;
  richness_rank: number;
}

// Insights dashboard (real ingested metrics)
export interface InsightKpis {
  posts_counted: number;
  total_reach: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_saves: number;
  total_shares: number;
  avg_engagement_rate: number;
}

export interface TopPost {
  shortcode: string;
  cluster_id: number;
  pillar: string;
  hook: string;
  timestamp_utc: string;
  reach: number;
  views: number;
  likes: number;
  comments: number;
  saves: number;
  shares: number;
  engagement_rate: number;
}

export interface PillarEngagement {
  cluster_id: number;
  pillar: string;
  engagement_rate: number;
  avg_reach: number;
  avg_saves: number;
  post_count: number;
}

export interface BestTimeCell {
  weekday: number;    // 0=Mon .. 6=Sun
  hour: number;       // 0..23 (UTC)
  avg_reach: number;
  count: number;
  reaches: number[];  // raw per-post reach — lets the client take a median post-tz-shift
}

export interface InsightsOverview {
  kpis: InsightKpis;
  top_posts: TopPost[];
  by_pillar: PillarEngagement[];
  best_times: BestTimeCell[];
  best_slot: BestTimeCell | null;
}

// Script Studio
// Formats StyleSync can GENERATE. Deliberately wider than the `post_type` unions
// used on analysis paths (WhyEngineRequest, RankedPost, recovery briefs): the Graph
// API doesn't return Stories as media and they expire after 24h, so a Story can be
// written but never diagnosed. Keep those unions narrow.
export type ScriptFormat = "Reel" | "Carousel" | "Static" | "Story";

export interface ScriptRequest {
  reference_caption: string;
  views: number;
  reach: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  format: ScriptFormat;
  cluster_id: number;
}

export interface ReelClip {
  clip_number: number;
  duration_secs: string;
  action: string;
  voiceover_line: string;
  camera_angle: string;
  lighting: string;
  setting: string;
  audio_cue: string;
}

export interface ReelScript {
  hook: string;
  clips: ReelClip[];
  music_recommendation: string;
  caption: string;
  hashtags: string[];
  reasoning?: string;
}

export interface CarouselSlide {
  slide: number;
  headline: string;
  body: string;
  visual?: string;   // what to shoot/lay out for this slide; absent on older saved assets
}

export interface CarouselScript {
  hook: string;
  slides: CarouselSlide[];
  cta_slide: string;
  caption: string;
  hashtags: string[];
  reasoning?: string;
}

export interface StaticScript {
  headline: string;
  caption: string;
  hashtags: string[];
  visual_direction: string;
  reasoning?: string;
}

// The stickers Instagram actually offers — enforced server-side in
// script_generator._normalize_story, so anything else never reaches the UI.
export type StorySticker =
  | "poll" | "question" | "quiz" | "slider" | "countdown" | "link" | "none";

export interface StoryFrame {
  frame: number;
  visual: string;
  on_screen_text: string;
  sticker: StorySticker;
  sticker_prompt: string;   // "" when sticker is "none"
  duration_secs: number;
}

// No caption and no hashtags — Instagram Stories have neither.
export interface StoryScript {
  hook: string;
  frames: StoryFrame[];
  closing_cta: string;
  reasoning?: string;
}

export interface ScriptResult {
  format: ScriptFormat;
  reasoning?: string;
  // format-specific fields merged at top level
  [key: string]: unknown;
}

// Onboarding
export interface OnboardStatus {
  status  : "queued" | "running" | "done" | "error";
  progress: number;
  message : string;
  handle ?: string;
  error  ?: string;
}

export interface HasProfileResult {
  has_profile: boolean;
  handle     : string | null;
}

export interface StrategicInsightsResult {
  scores: ClusterScore[];
  tensions: string[];
  strategic_brief: string;
  experiment: string;
  underutilized_cluster: number | null;
  overused_cluster: number | null;
}

export interface BoostAdvisorResult {
  boost_cluster_id: number;
  boost_cluster_name: string;
  boost_post_hook: string;
  reasoning: string;
  boost_strategy: string;
  expected_impact: string;
  dont_boost_cluster_id: number;
  dont_boost_cluster_name: string;
  dont_boost_reason: string;
  confidence?: { score: number; rationale: string };
  engagement_is_synthetic?: boolean;
}

// Voice loop
export interface VoiceRefineResult {
  refined_caption: string;
  reasoning: string;
}

// Multi-Agent Orchestrator
export interface OrchestrateRequest {
  task_type: "single_caption" | "full_campaign" | "post_mortem" | "trend_briefing" | "community_triage";
  payload: Record<string, unknown>;
}

export interface CriticHistoryEntry {
  cycle:      number;
  error_type: "ai_slop" | "off_brand_vocab" | "wrong_platform" | "factual_gap" | "approved";
  flagged:    string;
  fix:        string;
}

export interface CampaignBrief {
  product:   string;
  occasion:  string;
  platform:  "instagram" | "tiktok" | "linkedin";
  threshold: 70 | 80 | 90;
  useTrends: boolean;
}

export interface OrchestrateResponse {
  task_type:          string;
  topology:           string;
  results:            Record<string, unknown>;
  agents_used:        string[];
  cycles:             number;
  memory_written:     boolean;
  human_review_flag:  boolean;
  convergence_reason?: "goal_met" | "plateau" | "factual_gap" | "max_cycles";
  success:            boolean;
  error_message?:     string | null;
}

export interface MemoryStatusResponse {
  semantic:   number;
  episodic:   number;
  procedural: number;
}

export interface TrendBriefing {
  // The Trend agent can fail mid-run and still return a truthy result —
  // orchestrator.py falls back to `{}` in that case, so every field here is
  // genuinely optional at runtime.
  micro_trends?:       { trend: string; relevance: string; urgency: "high" | "medium" | "low" }[];
  audience_questions?: string[];
  content_hooks?:      string[];
  suggested_angles?:   { angle: string; cluster: string; format: string; why_now: string }[];
  briefing_summary?:   string;
  // Provenance. Replaces `sources_searched`, which counted hardcoded fallback
  // strings and so reported "3 sources" when nothing had been read at all.
  // comments_status: ok | not_connected | permission | error
  signals_used?:       { pillars: number; comments: number; comments_status: string };
}

// JARVIS agent
export type ActionResultType =
  | "caption"
  | "inspiration"
  | "workbench_items"
  | "post_mortem"
  | "autopilot_started"
  | "recovery_started"
  | "saved";

export interface InspirationIdea {
  title: string;
  angle: string;
  what_to_post: string;
  caption_hook: string;
}

export interface ActionResult {
  type: ActionResultType;
  data: {
    caption?   : string;
    cluster_id?: number;
    ideas?     : InspirationIdea[];
    topic?     : string;
    items?     : unknown[];
    id?        : string;
    job_id?    : string;
    steer?     : string;
    // post_mortem fields:
    verdict_label?   : string;
    diagnosis?       : string;
    what_failed?     : string;
    change_next_time?: string;
    [key: string]    : unknown;
  };
}

export interface AgentChatResponse {
  response      : string;
  action_result ?: ActionResult | null;
  session_id    : string;
}

// Strategy tab (performance-first, algorithm-grounded)
export type StrategySource = "official" | "your-data" | "industry-study";

export interface ScorecardMetric {
  key: string;
  label: string;
  value: number;
  unit: string;
  star: boolean;
  hint: string;
  source: StrategySource;
}

export interface PillarAgg {
  cluster_id: number;
  pillar: string;
  post_count: number;
  reach: number;
  sends_per_reach: number;
  saves_per_reach: number;
  engagement_rate: number;
  volume_pct: number;
}

export interface StrategyScorecard {
  metrics: ScorecardMetric[];
  posts_counted: number;
  by_pillar: PillarAgg[];
}

export interface TimelinePoint {
  month: string;
  sends_per_reach: number;
  saves_per_reach: number;
  reach: number;
  post_count: number;
  top_pillar: string;
  top_pillar_id: number | null;
}

export interface StrategyMove {
  title: string;
  stat: string;
  detail: string;
  principle: string;
  source: StrategySource;
  lever: string;
  /** Pillar the move is about — the Today page seeds its script from this. */
  cluster_id: number;
}

export interface RankedPost {
  shortcode: string;
  cluster_id: number;
  pillar: string;
  hook: string;
  timestamp_utc: string;
  reach: number;
  views: number;
  likes: number;
  comments: number;
  saves: number;
  shares: number;
  sends_per_reach: number;
  saves_per_reach: number;
  engagement_rate: number;
}

// ── Today (the daily briefing) ───────────────────────────────────────────────

export interface PostSeed {
  shortcode: string;
  caption: string;
  post_type: string;
  cluster_id: number | null;
  metrics: {
    reach: number;
    views: number;
    likes: number;
    comments: number;
    saves: number;
    shares: number;
  };
}

/** A move plus the format decision derived from its lever. */
export interface TodayRecommendation extends StrategyMove {
  format: "Reel" | "Carousel" | "Static";
  why_format: string;
}

export interface TodayBriefing {
  date: string;
  weekday: string;
  recommendation: TodayRecommendation | null;
  /** Best post inside the recommended pillar — the script's reference. */
  seed_post: RankedPost | null;
  other_moves?: StrategyMove[];
  posts_counted: number;
}

/**
 * First-party only: pillar velocity plus the account's own comments. There is no
 * external trend feed — `available: false` means the agent had no signal, and it
 * returns empty arrays rather than inventing trends.
 */
export interface TodayTrend {
  available: boolean;
  reason?: string;
  briefing_summary?: string;
  micro_trends?: string[];
  audience_questions?: string[];
  content_hooks?: string[];
  suggested_angles?: { angle?: string; cluster?: string; format?: string; why_now?: string }[];
  signals_used?: { pillars?: unknown; comments?: unknown; comments_status?: string };
}

export interface StrategyOverview {
  scorecard: StrategyScorecard;
  timeline: TimelinePoint[];
  moves: StrategyMove[];
  what_worked: { winner: RankedPost | null; loser: RankedPost | null };
}

export interface PostDiagnosis {
  verdict: string;
  verdict_label: string;
  diagnosis: string;
  what_worked: string;
  what_failed: string;
  brand_voice_gap: string;
  change_next_time: string;
}

export interface StrategyDiagnoses {
  winner_diagnosis: PostDiagnosis | null;
  loser_diagnosis: PostDiagnosis | null;
}

export interface StrategyBriefResult {
  strategic_brief: string;
  experiment: string;
}

// Diagnose tab — whole-account post inventory (instant) + lazy per-post diagnosis
export type PerformanceTier = "Top" | "Solid" | "Weak" | "No data";

export interface DiagnosePost {
  shortcode: string;
  cluster_id: number | null;
  pillar: string;
  group_key: string;
  caption: string;
  hook: string;
  timestamp_utc: string;
  permalink: string;
  media_type: string;
  post_type: "Reel" | "Carousel" | "Static";
  reach: number;
  views: number;
  likes: number;
  comments: number;
  saves: number;
  shares: number;
  sends_per_reach: number;
  saves_per_reach: number;
  engagement_rate: number;
  has_metrics: boolean;
  score: number;
  tier: PerformanceTier;
  has_diagnosis: boolean;
}

export interface DiagnoseGroup {
  group_key: string;
  cluster_id: number | null;
  pillar: string;
  note: string;
  post_count: number;
  posts: DiagnosePost[];
}

export interface DiagnosePostsResponse {
  groups: DiagnoseGroup[];
  total: number;
}

/** A cached per-post diagnosis — PostDiagnosis plus provenance. */
export interface PostDiagnosisResult extends PostDiagnosis {
  shortcode: string;
  post_type: string;
  generated_at: string;
}
