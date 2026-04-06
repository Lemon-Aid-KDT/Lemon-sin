/**
 * CAD Vision API TypeScript 타입 정의
 * FastAPI Pydantic 스키마에서 매핑
 */

// ── Response Models ──

export interface DrawingRecord {
  drawing_id: string;
  file_path: string;
  file_name: string;
  ocr_text: string;
  part_numbers: string[];
  dimensions: string[];
  materials: string[];
  category: string;
  description: string;
  yolo_confidence: number;
  yolo_needs_review: boolean;
  detected_regions: Record<string, unknown>[];
  dxf_path: string;
  similar_drawings: SimilarDrawing[];
  registered_at: string;
  revision: number;
}

export interface SimilarDrawing {
  drawing_id: string;
  score: number;
  file_name: string;
  file_path: string;
}

export interface SearchResult {
  drawing_id: string;
  score: number;
  distance: number;
  file_path: string;
  file_name: string;
  category: string;
  metadata: Record<string, unknown>;
}

export interface UnifiedSearchResult {
  record_id: string;
  score: number;
  channel_scores: Record<string, number>;
  metadata: Record<string, unknown>;
  thumbnail_path: string;
}

export interface PaginatedResponse {
  items: DrawingRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatsResponse {
  total_drawings: number;
  image_collection_count: number;
  text_collection_count: number;
  gnn_collection_count: number;
  categories: string[];
  category_counts?: Record<string, number>;
  ollama_status: string;         // "healthy" | "unhealthy" | ""
  ollama_model?: string;         // may not exist in response
  ollama_healthy?: boolean;      // may not exist in response
  yolo_cls_enabled: boolean;
  yolo_det_enabled: boolean;
  gnn_enabled: boolean;
}

/** Helper: determine if Ollama is connected from stats */
export function isOllamaConnected(stats: StatsResponse | undefined): boolean {
  if (!stats) return false;
  if (stats.ollama_healthy === true) return true;
  if (stats.ollama_status === "healthy") return true;
  return false;
}

export interface DescribeResponse {
  drawing_id: string;
  description: string;
}

export interface AskResponse {
  drawing_id: string;
  question: string;
  answer: string;
}

export interface ClassifyResponse {
  category: string;
  confidence: number;
  needs_review: boolean;
  top_k: { category: string; confidence: number }[];
}

export interface BOMEntry {
  item_no: string;
  part_name: string;
  quantity: string;
  material: string;
  specification: string;
}

export interface BOMResponse {
  entries: BOMEntry[];
  confidence: number;
  source: string;
}

export interface DXFDiffResponse {
  matched_count: number;
  only_in_a_count: number;
  only_in_b_count: number;
  layer_diff: Record<string, string[]>;
  summary: Record<string, unknown>;
}

export interface DimensionCompareResponse {
  matched: unknown[];
  changed: unknown[];
  only_in_a: unknown[];
  only_in_b: unknown[];
  similarity: number;
}

export interface BatchRegisterResult {
  total: number;
  success: number;
  failed: number;
  results: {
    status: "ok" | "error" | "skipped";
    file: string;
    drawing_id?: string;
    category?: string;
    error?: string;
    reason?: string;
  }[];
}

// ── Request Models ──

export interface TextSearchRequest {
  query: string;
  top_k?: number;
  category?: string;
}

export interface UnifiedSearchRequest {
  text?: string;
  part_number?: string;
  channels?: ("text" | "image" | "gnn" | "part_number")[];
  top_k?: number;
  category?: string;
}

export interface AskRequest {
  question: string;
}

// ── UI Models ──

export interface CategoryCount {
  name: string;
  count: number;
}

export type PageName =
  | "dashboard"
  | "register"
  | "search"
  | "analysis"
  | "dxf-viewer"
  | "stl-viewer"
  | "tools";
