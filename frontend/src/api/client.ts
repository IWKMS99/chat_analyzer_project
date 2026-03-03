import type {
  AnalysisCreatedResponse,
  AnalysisListResponse,
  AnalysisStatusResponse,
  DashboardResponse,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v2";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail ?? `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function createAnalysis(file: File, timezone: string): Promise<AnalysisCreatedResponse> {
  const form = new FormData();
  form.set("file", file);
  form.set("timezone", timezone);

  const response = await fetch(`${API_BASE}/analyses`, {
    method: "POST",
    body: form,
  });
  return parseJson<AnalysisCreatedResponse>(response);
}

export async function getAnalysisStatus(analysisId: string): Promise<AnalysisStatusResponse> {
  const response = await fetch(`${API_BASE}/analyses/${analysisId}/status`);
  return parseJson<AnalysisStatusResponse>(response);
}

export async function getDashboard(analysisId: string): Promise<DashboardResponse> {
  const response = await fetch(`${API_BASE}/analyses/${analysisId}/dashboard`);
  return parseJson<DashboardResponse>(response);
}

export async function listAnalyses(limit = 20): Promise<AnalysisListResponse> {
  const response = await fetch(`${API_BASE}/analyses?limit=${limit}`);
  return parseJson<AnalysisListResponse>(response);
}

export async function deleteAnalysis(analysisId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/analyses/${analysisId}`, { method: "DELETE" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Delete failed" }));
    throw new Error(payload.detail ?? `HTTP ${response.status}`);
  }
}
