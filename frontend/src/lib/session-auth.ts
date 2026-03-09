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
