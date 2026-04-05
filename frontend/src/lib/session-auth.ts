export const ADMIN_SESSION_KEY = "mbf_admin_key";

export function getStoredAdminKey(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(ADMIN_SESSION_KEY) ?? "";
}

export function storeAdminKey(key: string): void {
  sessionStorage.setItem(ADMIN_SESSION_KEY, key);
}

export function clearAdminKey(): void {
  sessionStorage.removeItem(ADMIN_SESSION_KEY);
}

export function isAdminAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem(ADMIN_SESSION_KEY) !== null;
}

export function withAdminFetchInit(
  init: RequestInit = {},
  options?: { json?: boolean },
): RequestInit {
  const headers = new Headers(init.headers);
  if (options?.json) {
    headers.set("Content-Type", "application/json");
  }
  const key = getStoredAdminKey();
  if (key) {
    headers.set("X-Admin-Key", key);
  }
  return { ...init, headers };
}

export function fetchVerifyAdminKey(key: string): Promise<Response> {
  return fetch("/api/auth/admin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key }),
  });
}
