import { NextRequest, NextResponse } from "next/server";
import {
  nextJsonFromBackendResponse,
  postBackendJson,
} from "@/lib/proxy-backend-json";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await postBackendJson("/api/auth/admin", body);
    return nextJsonFromBackendResponse(res);
  } catch {
    return NextResponse.json({ error: "Auth check failed" }, { status: 500 });
  }
}
