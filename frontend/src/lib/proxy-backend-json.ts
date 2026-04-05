import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";
import { adminHeaders } from "@/lib/admin";

export function backendFetch(path: string, init?: RequestInit): Promise<Response> {
  const p = path.startsWith("/") ? path : `/${path}`;
  return fetch(`${BACKEND_URL}${p}`, init);
}

export async function postBackendJson(
  backendPath: string,
  body: unknown,
): Promise<Response> {
  return backendFetch(backendPath, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function nextJsonFromBackendResponse(
  res: Response,
): Promise<NextResponse> {
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function getBackendNoStore(path: string): Promise<Response> {
  return backendFetch(path, { cache: "no-store" });
}

export async function postBackendJsonAdmin(
  path: string,
  body: unknown,
  adminKey: string,
): Promise<Response> {
  return backendFetch(path, {
    method: "POST",
    headers: adminHeaders(adminKey, { "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
}

export async function postBackendJsonTextBodyAdmin(
  path: string,
  bodyText: string,
  adminKey: string,
): Promise<Response> {
  return backendFetch(path, {
    method: "POST",
    headers: adminHeaders(adminKey, { "Content-Type": "application/json" }),
    body: bodyText,
    cache: "no-store",
  });
}

export async function postBackendAdminEmpty(
  path: string,
  adminKey: string,
): Promise<Response> {
  return backendFetch(path, {
    method: "POST",
    headers: adminHeaders(adminKey),
    cache: "no-store",
  });
}

export async function putBackendJsonAdmin(
  path: string,
  body: unknown,
  adminKey: string,
): Promise<Response> {
  return backendFetch(path, {
    method: "PUT",
    headers: adminHeaders(adminKey, { "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
}

export async function putBackendJsonTextAdmin(
  path: string,
  bodyText: string,
  adminKey: string,
): Promise<Response> {
  return backendFetch(path, {
    method: "PUT",
    headers: adminHeaders(adminKey, { "Content-Type": "application/json" }),
    body: bodyText,
    cache: "no-store",
  });
}

export async function deleteBackendAdmin(
  path: string,
  adminKey: string,
): Promise<Response> {
  return backendFetch(path, {
    method: "DELETE",
    headers: adminHeaders(adminKey),
  });
}

export async function nextJsonFromBackend(res: Response): Promise<NextResponse> {
  if (res.ok) {
    return NextResponse.json(await res.json(), { status: res.status });
  }
  const ct = res.headers.get("content-type") ?? "";
  if (ct.includes("application/json")) {
    return NextResponse.json(await res.json(), { status: res.status });
  }
  return NextResponse.json(
    { error: await res.text() },
    { status: res.status },
  );
}
