import type {
  BrandProfile,
  ClustersData,
  MomentAnalysis,
  Direction,
  Caption,
  ImagePromptResult,
  WhyEngineRequest,
  WhyEngineResult,
  VoiceTimelineResult,
  StrategicInsightsResult,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

// Brand
export const getBrandProfile = () => apiFetch<BrandProfile>("/api/brand/profile");
export const getClusters = () => apiFetch<ClustersData>("/api/brand/clusters");

// Create
export const analyzeMoment = (moment_text: string) =>
  apiFetch<MomentAnalysis>("/api/create/analyze-moment", {
    method: "POST",
    body: JSON.stringify({ moment_text }),
  });

export const getDirections = (moment_analysis: MomentAnalysis, moment_text: string) =>
  apiFetch<Direction[]>("/api/create/directions", {
    method: "POST",
    body: JSON.stringify({ moment_analysis, moment_text }),
  });

export const generateCaptions = (payload: {
  product: string;
  occasion: string;
  desired_feel: string;
  cluster_id: number;
  previous_captions?: string[];
}) =>
  apiFetch<Caption[]>("/api/create/captions", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const generateImagePrompt = (caption: string, product: string) =>
  apiFetch<ImagePromptResult>("/api/create/image-prompt", {
    method: "POST",
    body: JSON.stringify({ caption, product }),
  });

export const generateScript = (payload: import("./types").ScriptRequest) =>
  apiFetch<import("./types").ScriptResult>("/api/create/script", {
    method: "POST",
    body: JSON.stringify(payload),
  });

// Analyze
export const runWhyEngine = (payload: WhyEngineRequest) =>
  apiFetch<WhyEngineResult>("/api/analyze/why-engine", {
    method: "POST",
    body: JSON.stringify(payload),
  });

// Discover
export const getVoiceTimeline = () =>
  apiFetch<VoiceTimelineResult>("/api/discover/voice-timeline");

export const getStrategicInsights = () =>
  apiFetch<StrategicInsightsResult>("/api/discover/strategic-insights");
