export const GATEWAY_V1 = process.env.NEXT_PUBLIC_GATEWAY_PUBLIC_URL || "http://localhost:8000/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function errorMessage(text: string, fallback: string) {
  if (!text) return fallback;
  try {
    const j = JSON.parse(text) as { detail?: unknown; message?: string; error?: { message?: string } };
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) {
      return j.detail.map((x: { msg?: string }) => x.msg || JSON.stringify(x)).join("; ");
    }
    return j.error?.message || j.message || text;
  } catch {
    return text.slice(0, 400) || fallback;
  }
}

export async function adminFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const adminPath = path.startsWith("/admin/") ? path.slice("/admin".length) : path;
  const res = await fetch(`/api/control${adminPath}`, { ...init, headers, credentials: "include" });
  if (res.status === 401 && typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
  const text = await res.text();
  if (!res.ok) {
    throw new ApiError(res.status, errorMessage(text, res.statusText));
  }
  if (res.status === 204 || !text) return undefined as T;
  return JSON.parse(text) as T;
}

export function playgroundKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("gw:playgroundKey") || "";
}

export function setPlaygroundKey(key: string) {
  localStorage.setItem("gw:playgroundKey", key);
}
