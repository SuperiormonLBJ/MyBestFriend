import { NextRequest, NextResponse } from "next/server";
import {
  nextJsonFromBackendResponse,
  postBackendJson,
} from "@/lib/proxy-backend-json";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await postBackendJson("/api/job/cover-letter", body);
    return nextJsonFromBackendResponse(res);
  } catch (err) {
    console.error("Job cover-letter API error:", err);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
