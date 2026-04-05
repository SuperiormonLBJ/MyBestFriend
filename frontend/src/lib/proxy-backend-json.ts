import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

export async function postBackendJson(
  backendPath: string,
  body: unknown,
): Promise<Response> {
  return fetch(`${BACKEND_URL}${backendPath}`, {
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
