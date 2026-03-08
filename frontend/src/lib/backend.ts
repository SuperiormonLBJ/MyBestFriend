const raw =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://127.0.0.1:8000";
export const BACKEND_URL = raw.replace(/\/+$/, "");
