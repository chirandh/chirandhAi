const API_PREFIX = import.meta.env.VITE_API_PREFIX ?? "";

export function apiUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${API_PREFIX}${path}`;
}

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(`HTTP ${status}`);
    this.status = status;
    this.body = body;
    this.name = "ApiError";
  }
}

function parseDetail(body: string): string {
  try {
    const j = JSON.parse(body) as { detail?: unknown };
    if (typeof j.detail === "string") return j.detail;
    if (j.detail !== undefined) return JSON.stringify(j.detail, null, 2);
  } catch {
    /* ignore */
  }
  return body || "(empty response)";
}

export async function apiFetch<T>(
  path: string,
  apiKey: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("X-API-Key")) headers.set("X-API-Key", apiKey);
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(apiUrl(path), { ...init, headers });
  const text = await res.text();

  if (!res.ok) {
    throw new ApiError(res.status, parseDetail(text));
  }

  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}
