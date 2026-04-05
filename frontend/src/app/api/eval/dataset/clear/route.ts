import { NextRequest, NextResponse } from "next/server";
import { adminKeyFromRequest } from "@/lib/admin";
import {
  nextJsonFromBackend,
  postBackendAdminEmpty,
} from "@/lib/proxy-backend-json";

export async function POST(request: NextRequest) {
  try {
    const res = await postBackendAdminEmpty(
      "/api/eval/dataset/clear",
      adminKeyFromRequest(request),
    );
    return nextJsonFromBackend(res);
  } catch (err) {
    console.error("Eval dataset clear error:", err);
    return NextResponse.json(
      { error: "Failed to clear evaluation dataset" },
      { status: 500 },
    );
  }
}
