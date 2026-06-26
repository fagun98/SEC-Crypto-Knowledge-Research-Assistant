import type {
  ChatRequest,
  ChatResponse,
  ReportDetail,
  ReportListResponse,
  SearchRequest,
  SearchResponse,
} from "./types";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let message = "The service could not complete this request.";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {}
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function sendChatMessage(payload: ChatRequest) {
  return request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify(payload) });
}

export function searchDocuments(payload: SearchRequest) {
  return request<SearchResponse>("/api/search", { method: "POST", body: JSON.stringify(payload) });
}

export function getLatestReport() {
  return request<ReportDetail>("/api/reports/latest", { cache: "no-store" });
}

export function getReports() {
  return request<ReportListResponse>("/api/reports", { cache: "no-store" });
}

export function getReport(filename: string) {
  return request<ReportDetail>(`/api/reports/document?filename=${encodeURIComponent(filename)}`, { cache: "no-store" });
}
