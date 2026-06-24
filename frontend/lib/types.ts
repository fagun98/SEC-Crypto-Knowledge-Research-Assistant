export type Source = {
  title: string;
  url?: string | null;
  score?: number | null;
  snippet?: string | null;
};

export type HistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatRequest = {
  message: string;
  session_id?: string;
  history?: HistoryMessage[];
};

export type ChatResponse = {
  answer: string;
  session_id: string;
  sources: Source[];
  metadata: Record<string, unknown>;
};

export type SearchRequest = {
  query: string;
  alpha?: number;
  top_k?: number;
  score_threshold?: number;
};

export type SearchResult = Source & { metadata: Record<string, unknown>; score: number };
export type SearchResponse = { query: string; results: SearchResult[] };

export type ReportSummary = { title: string; date: string; filename: string };
export type ReportDetail = ReportSummary & { content: string };
export type ReportListResponse = { reports: ReportSummary[] };
