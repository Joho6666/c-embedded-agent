const ADMIN = process.env.NEXT_PUBLIC_GATEWAY_ADMIN_API || "http://localhost:8000";
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "gw-admin-dev-key";
export const GATEWAY_V1 = process.env.NEXT_PUBLIC_GATEWAY_PUBLIC_URL || "http://localhost:8000/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function adminFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${ADMIN_KEY}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const res = await fetch(`${ADMIN}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text.slice(0, 400) || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function playgroundKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("gw:playgroundKey") || "";
}

export function setPlaygroundKey(key: string) {
  localStorage.setItem("gw:playgroundKey", key);
}
