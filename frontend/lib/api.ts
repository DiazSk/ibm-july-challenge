import type {
  BrandProfile,
  ClustersData,
  MomentAnalysis,
  Direction,
  Caption,
  CaptionsGenerateResponse,
  ImagePromptResult,
  WhyEngineRequest,
  WhyEngineResult,
  VoiceTimelineResult,
  StrategicInsightsResult,
  BoostAdvisorResult,
  VoiceRefineResult,
  AgentChatResponse,
  OnboardStatus,
  HasProfileResult,
  WorkbenchAsset,
  RepurposeStatus,
  ResonanceResult,
  GuardianReviewResult,
  DriftCheckResult,
  DriftCompareResult,
  TriageBatchResponse,
  WeeklyBriefStatus,
  WeeklyBriefPendingNotice,
  OrchestrateRequest,
  OrchestrateResponse,
  MemoryStatusResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Full-page redirect target for the Instagram OAuth connect flow.
export const connectInstagramUrl = () => `${BASE}/api/connect/login`;

// Instagram connection status + manual sync.
export interface ConnectStatus {
  connected: boolean;
  username?: string;
  last_sync?: string | null;
  token_expires_at?: string | null;
}
export const getConnectStatus = () => apiFetch<ConnectStatus>("/api/connect/status");
export const syncInstagram = (full = false) =>
  apiFetch<{ status: string }>(`/api/connect/sync?full=${full}`, { method: "POST" });

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

// Insights dashboard
export const getInsightsOverview = () =>
  apiFetch<import("./types").InsightsOverview>("/api/insights/overview");

// Brand
export const getBrandProfile = () => apiFetch<BrandProfile>("/api/brand/profile");
export const getClusters = () => apiFetch<ClustersData>("/api/brand/clusters");

export const checkBrandDrift = (pasted_posts: string[]) =>
  apiFetch<DriftCheckResult>("/api/brand/drift-check", {
    method: "POST",
    body: JSON.stringify({ pasted_posts }),
  });

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
  apiFetch<CaptionsGenerateResponse>("/api/create/captions", {
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

export const runResonanceCheck = (captions: string[]) =>
  apiFetch<ResonanceResult>("/api/create/resonance-check", {
    method: "POST",
    body: JSON.stringify({ captions }),
  });

export const runGuardianReview = (caption: string, cluster_id: number) =>
  apiFetch<GuardianReviewResult>("/api/create/guardian-review", {
    method: "POST",
    body: JSON.stringify({ caption, cluster_id }),
  });

export const runDriftCompare = (payload: {
  product: string;
  occasion: string;
  desired_feel: string;
  cluster_id: number;
}) =>
  apiFetch<DriftCompareResult>("/api/create/drift-compare", {
    method: "POST",
    body: JSON.stringify(payload),
  });

// Autopilot — autonomous weekly content agent
export const startAgentRun = (payload: {
  steer: string;
  target_count: number;
  platform: string;
  confidence_threshold: number;
}) =>
  apiFetch<{ job_id: string }>("/api/agent-run/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const getAgentRun = (jobId: string) =>
  apiFetch<import("./types").AgentRunState>(`/api/agent-run/${jobId}`);

export const answerAgentRun = (jobId: string, answer: string) =>
  apiFetch<{ status: string }>(`/api/agent-run/${jobId}/answer`, {
    method: "POST",
    body: JSON.stringify({ answer }),
  });

// Comment/DM Triage
export const runTriage = (messages: string[], cluster_id: number = 0) =>
  apiFetch<TriageBatchResponse>("/api/triage/run", {
    method: "POST",
    body: JSON.stringify({ messages, cluster_id }),
  });

// Real Instagram inbox (comments)
export const getInboxComments = () =>
  apiFetch<import("./types").InboxCommentsResponse>("/api/inbox/comments");

export const sendCommentReply = (comment_id: string, message: string) =>
  apiFetch<{ ok: boolean; id: string }>("/api/inbox/reply", {
    method: "POST",
    body: JSON.stringify({ comment_id, message }),
  });

// Weekly Brief Agent
export const startWeeklyBrief = (n: number = 2) =>
  apiFetch<{ job_id: string }>("/api/weekly-brief/generate", {
    method: "POST",
    body: JSON.stringify({ n }),
  });

export const getWeeklyBriefStatus = (jobId: string) =>
  apiFetch<WeeklyBriefStatus>(`/api/weekly-brief/status/${jobId}`);

export const getWeeklyBriefPendingNotice = () =>
  apiFetch<WeeklyBriefPendingNotice>("/api/weekly-brief/pending-notice");

// Autonomous Recovery Agent
export const getRecoveryPendingNotice = () =>
  apiFetch<import("./types").RecoveryNotice>("/api/recovery/pending-notice");

// Self-Improving Playbook Agent
export const reflectPlaybook = () =>
  apiFetch<{ job_id: string }>("/api/playbook/reflect", { method: "POST" });

export const getReflectStatus = (jobId: string) =>
  apiFetch<import("./types").ReflectJob>(`/api/playbook/reflect/${jobId}`);

export const getPlaybookRules = () =>
  apiFetch<import("./types").PlaybookRule[]>("/api/playbook/rules");

// Analyze
export const runWhyEngine = (payload: WhyEngineRequest) =>
  apiFetch<WhyEngineResult>("/api/analyze/why-engine", {
    method: "POST",
    body: JSON.stringify(payload),
  });

// Vision: describe an uploaded image/video so the Why Engine can "see" the post.
// Multipart, so it bypasses apiFetch's JSON Content-Type.
export const describeImage = async (file: File): Promise<{ visual_description: string }> => {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/analyze/describe-image`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`${res.status} ${await res.text().catch(() => res.statusText)}`);
  return res.json();
};

// Closed-Loop Repurposing (auto-triggered by why-engine on a "succeeded" verdict)
export const getRepurposeStatus = (jobId: string) =>
  apiFetch<RepurposeStatus>(`/api/repurpose/status/${jobId}`);

// Discover
export const getVoiceTimeline = () =>
  apiFetch<VoiceTimelineResult>("/api/discover/voice-timeline");

export const getStrategicInsights = () =>
  apiFetch<StrategicInsightsResult>("/api/discover/strategic-insights");

export const getBoostAdvisor = () =>
  apiFetch<BoostAdvisorResult>("/api/discover/boost-advisor");

// Diagnose (whole-account per-post diagnosis)
export const getDiagnosePosts = () =>
  apiFetch<import("./types").DiagnosePostsResponse>("/api/diagnose/posts");

// One post's Granite diagnosis — ~10s on first call, disk-cached after.
export const getPostDiagnosis = (shortcode: string, force = false) =>
  apiFetch<import("./types").PostDiagnosisResult>(
    `/api/diagnose/posts/${shortcode}${force ? "?force=true" : ""}`
  );

// Strategy (performance-first, algorithm-grounded)
export const getStrategyOverview = () =>
  apiFetch<import("./types").StrategyOverview>("/api/strategy/overview");

export const getStrategyDiagnoses = () =>
  apiFetch<import("./types").StrategyDiagnoses>("/api/strategy/diagnoses");

export const getStrategyBrief = () =>
  apiFetch<import("./types").StrategyBriefResult>("/api/strategy/brief");

export const voiceRefineCaption = (transcript: string, cluster_id: number) =>
  apiFetch<VoiceRefineResult>("/api/create/voice-refine", {
    method: "POST",
    body: JSON.stringify({ transcript, cluster_id }),
  });

// JARVIS agent
export const agentChat = (
  userMessage: string,
  sessionId: string,
  history: { role: string; content: string }[] = [],
) =>
  apiFetch<AgentChatResponse>("/api/agent/chat", {
    method: "POST",
    body: JSON.stringify({
      user_message: userMessage,
      session_id  : sessionId,
      messages    : history,
    }),
  });

export async function clearAgentSession(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/agent/session/${sessionId}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
}

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

// Multi-Agent Orchestrator
export const runOrchestration = (req: OrchestrateRequest) =>
  apiFetch<OrchestrateResponse>("/api/orchestrate", {
    method: "POST",
    body: JSON.stringify(req),
  });

export const getMemoryStatus = () =>
  apiFetch<MemoryStatusResponse>("/api/orchestrate/memory-status");

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
