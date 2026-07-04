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
  BoostAdvisorResult,
  VoiceRefineResult,
  OnboardStatus,
  HasProfileResult,
  WorkbenchAsset,
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

export const getBoostAdvisor = () =>
  apiFetch<BoostAdvisorResult>("/api/discover/boost-advisor");

export const voiceRefineCaption = (transcript: string, cluster_id: number) =>
  apiFetch<VoiceRefineResult>("/api/create/voice-refine", {
    method: "POST",
    body: JSON.stringify({ transcript, cluster_id }),
  });

// Onboarding
export const checkHasProfile = () =>
  apiFetch<HasProfileResult>("/api/onboard/has-profile");

export const startOnboard = (handle: string, brand_name: string) =>
  apiFetch<{ job_id: string }>("/api/onboard/start", {
    method: "POST",
    body: JSON.stringify({ handle, brand_name }),
  });

export const getOnboardStatus = (jobId: string) =>
  apiFetch<OnboardStatus>(`/api/onboard/status/${jobId}`);

export const resetToDemo = () =>
  apiFetch<{ status: string; handle: string }>("/api/onboard/reset-demo", {
    method: "POST",
  });

// Workbench
export const getWorkbenchAssets = (pinned?: boolean) => {
  const qs = pinned !== undefined ? `?pinned=${pinned}` : "";
  return apiFetch<WorkbenchAsset[]>(`/api/workbench/assets${qs}`);
};

export const saveAsset = (asset: {
  asset_type: string;
  content: unknown;
  cluster_label?: string | null;
  cluster_id?: number | null;
  source_tab?: string | null;
}) =>
  apiFetch<WorkbenchAsset>("/api/workbench/assets", {
    method: "POST",
    body: JSON.stringify(asset),
  });

export const updateAsset = (
  id: string,
  update: { pinned?: boolean; actual_outcome?: string; recovery_brief_generated?: boolean }
) =>
  apiFetch<WorkbenchAsset>(`/api/workbench/assets/${id}`, {
    method: "PATCH",
    body: JSON.stringify(update),
  });

export async function deleteAsset(id: string): Promise<void> {
  const res = await fetch(`${BASE}/api/workbench/assets/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
}

export async function uploadExport(
  file      : File,
  account   : string,
  brand_name: string,
): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("account", account);
  form.append("brand_name", brand_name);
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const res = await fetch(`${BASE_URL}/api/onboard/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json();
}
