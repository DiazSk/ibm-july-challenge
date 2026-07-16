// Brand
export interface BrandProfile {
  brand_name: string;
  handle: string;
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
export interface MomentAnalysis {
  emotional_core: string;
  business_signal: string;
  best_cluster_id: number;
  cluster_reason: string;
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

// Script Studio
export interface ScriptRequest {
  reference_caption: string;
  views: number;
  reach: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  format: "Reel" | "Carousel" | "Static";
  cluster_id: number;
}

export interface ReelScript {
  hook: string;
  opening_line: string;
  voiceover_script: string;
  shot_suggestions: string[];
  caption: string;
  hashtags: string[];
  reasoning?: string;
}

export interface CarouselSlide {
  slide: number;
  headline: string;
  body: string;
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

export interface ScriptResult {
  format: "Reel" | "Carousel" | "Static";
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
  micro_trends:     { trend: string; relevance: string; urgency: "high" | "medium" | "low" }[];
  content_hooks:    string[];
  suggested_angles: { angle: string; cluster: string; format: string; why_now: string }[];
  briefing_summary: string;
  sources_searched: number;
}

// JARVIS agent
export type ActionResultType =
  | "caption"
  | "inspiration"
  | "workbench_items"
  | "post_mortem"
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
