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
