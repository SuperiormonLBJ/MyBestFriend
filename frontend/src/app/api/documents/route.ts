import { NextRequest, NextResponse } from "next/server";
import { adminKeyFromRequest } from "@/lib/admin";
import {
  nextJsonFromBackendResponse,
  postBackendJsonAdmin,
} from "@/lib/proxy-backend-json";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await postBackendJsonAdmin(
      "/api/documents",
      body,
      adminKeyFromRequest(request),
    );
    return nextJsonFromBackendResponse(res);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
