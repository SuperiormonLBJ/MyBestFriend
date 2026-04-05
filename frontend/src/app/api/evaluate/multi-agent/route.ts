import { NextRequest, NextResponse } from "next/server";
import { adminKeyFromRequest } from "@/lib/admin";
import {
  nextJsonFromBackend,
  postBackendAdminEmpty,
} from "@/lib/proxy-backend-json";

export async function POST(request: NextRequest) {
  try {
    const res = await postBackendAdminEmpty(
      "/api/evaluate/multi-agent",
      adminKeyFromRequest(request),
    );
    return nextJsonFromBackend(res);
  } catch (err) {
    console.error("Multi-agent evaluate start error:", err);
    return NextResponse.json(
      { error: "Failed to start multi-agent evaluation" },
      { status: 500 },
    );
  }
}
