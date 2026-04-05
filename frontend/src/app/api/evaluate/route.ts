import { NextRequest, NextResponse } from "next/server";
import { adminKeyFromRequest } from "@/lib/admin";
import {
  nextJsonFromBackend,
  postBackendAdminEmpty,
} from "@/lib/proxy-backend-json";

export async function POST(request: NextRequest) {
  try {
    const res = await postBackendAdminEmpty(
      "/api/evaluate",
      adminKeyFromRequest(request),
    );
    return nextJsonFromBackend(res);
  } catch (err) {
    console.error("Evaluate start error:", err);
    return NextResponse.json(
      { error: "Failed to start evaluation" },
      { status: 500 },
    );
  }
}
