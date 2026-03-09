/**
 * Returns headers for backend admin requests.
 *
 * `key` — explicit key (read from the incoming Next.js request's X-Admin-Key header).
 *         Falls back to process.env.ADMIN_API_KEY for non-browser/programmatic callers.
 *
 * If the resolved key is empty the header is omitted, which is correct for
 * open-mode backends (no key configured).
 */
export function adminHeaders(
  key?: string,
  extra?: Record<string, string>
): Record<string, string> {
  const resolvedKey = key !== undefined ? key : (process.env.ADMIN_API_KEY ?? "");
  const base: Record<string, string> = { ...(extra ?? {}) };
  if (resolvedKey) base["X-Admin-Key"] = resolvedKey;
  return base;
}
