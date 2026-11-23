/**
 * Backend bilan aloqa (ARCHITECTURE: sessiya cookie + CSRF).
 * Xavfli metodlar `X-CSRFToken` sarlavhasi bilan ketadi; token `/api/auth/csrf` o'rnatgan cookie'dan olinadi.
 */

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; data: unknown };

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

function readCookie(name: string): string | null {
  for (const part of document.cookie.split("; ")) {
    const [key, ...rest] = part.split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

async function ensureCsrf(): Promise<string> {
  const existing = readCookie("csrftoken");
  if (existing) return existing;
  await fetch("/api/auth/csrf", { credentials: "same-origin" });
  return readCookie("csrftoken") ?? "";
}

export async function api<T = unknown>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<ApiResult<T>> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (!SAFE_METHODS.has(method)) {
    headers["X-CSRFToken"] = await ensureCsrf();
  }
  const init: RequestInit = { method, headers, credentials: "same-origin" };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, init);
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (response.ok) return { ok: true, status: response.status, data: data as T };
  return { ok: false, status: response.status, data };
}

/** DRF maydon xatolari: `{field: ["xabar", ...]}` → `{field: "xabar"}` (faqat satrlar). */
export function fieldErrors(data: unknown): Record<string, string> {
  const result: Record<string, string> = {};
  if (data && typeof data === "object") {
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      if (Array.isArray(value) && typeof value[0] === "string") result[key] = value[0];
      else if (typeof value === "string") result[key] = value;
    }
  }
  return result;
}

export interface Me {
  hemis_id: string;
  full_name: string;
  role: string;
  direction: number | null;
  must_change_password: boolean;
}
