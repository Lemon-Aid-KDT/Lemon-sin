/**
 * CAD Vision API 클라이언트
 *
 * FastAPI 백엔드 (http://localhost:8000/api/v1) 호출
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

// ── Generic fetch wrapper ──

export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${detail}`);
  }

  return res.json();
}

// ── File upload (multipart/form-data) ──

export async function apiUpload<T>(
  path: string,
  formData: FormData,
  params?: Record<string, string>
): Promise<T> {
  const query = params
    ? "?" + new URLSearchParams(params).toString()
    : "";
  const url = `${API_BASE}${path}${query}`;

  const res = await fetch(url, {
    method: "POST",
    body: formData,
    // Content-Type은 FormData가 자동 설정 (boundary 포함)
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "Unknown error");
    throw new Error(`Upload ${res.status}: ${detail}`);
  }

  return res.json();
}

// ── SSE Streaming (Analysis) ──

export async function apiStreamSSE(
  path: string,
  formData: FormData,
  params: Record<string, string>,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (err: string) => void
): Promise<void> {
  const query = new URLSearchParams(params).toString();
  const url = `${API_BASE}${path}?${query}`;

  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    onError(`HTTP ${res.status}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onError("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (data === "[DONE]") {
          onDone();
          return;
        }
        try {
          const parsed = JSON.parse(data);
          if (parsed.token) onToken(parsed.token);
          if (parsed.error) onError(parsed.error);
        } catch {
          // Non-JSON data, skip
        }
      }
    }
  }
  onDone();
}

// ── Image URL helpers ──

export function drawingImageUrl(drawingId: string): string {
  return `${API_BASE}/drawings/${drawingId}/image`;
}

export function drawingThumbnailUrl(drawingId: string): string {
  return `${API_BASE}/drawings/${drawingId}/thumbnail`;
}

export { API_BASE };
