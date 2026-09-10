import type { TokenResponse } from "./types";

const BASE = "/api/v1";
const ACCESS_KEY = "ecdat.access";
const REFRESH_KEY = "ecdat.refresh";

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(t: TokenResponse) {
    localStorage.setItem(ACCESS_KEY, t.access_token);
    localStorage.setItem(REFRESH_KEY, t.refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (!tokenStore.refresh) return false;
  if (!refreshing) {
    refreshing = fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokenStore.refresh }),
    })
      .then(async (r) => {
        if (!r.ok) return false;
        tokenStore.set((await r.json()) as TokenResponse);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

interface Opts {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  raw?: boolean;
}

export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  const url = new URL(BASE + path, window.location.origin);
  for (const [k, v] of Object.entries(opts.query ?? {})) {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  }

  const doFetch = () =>
    fetch(url.toString(), {
      method: opts.method ?? "GET",
      headers: {
        ...(opts.body ? { "Content-Type": "application/json" } : {}),
        ...(tokenStore.access ? { Authorization: `Bearer ${tokenStore.access}` } : {}),
      },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });

  let res = await doFetch();
  if (res.status === 401 && (await tryRefresh())) {
    res = await doFetch();
  }
  if (res.status === 401) {
    tokenStore.clear();
    if (!location.pathname.startsWith("/login")) location.assign("/login");
    throw new ApiError(401, "Session expired");
  }
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail ?? j;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new ApiError(res.status, "Invalid credentials");
  const t = (await res.json()) as TokenResponse;
  tokenStore.set(t);
  return t;
}

export function downloadUrl(path: string): string {
  return BASE + path;
}

/** Authenticated file download: fetch with the bearer token, then save the blob.
 *  (A plain <a href> can't send the Authorization header and would 401.) */
export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const res = await api<Response>(path, { raw: true });
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") ?? "";
  const m = cd.match(/filename="?([^"]+)"?/);
  const name = m?.[1] ?? fallbackName;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
