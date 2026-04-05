import { NextRequest, NextResponse } from "next/server";
import { adminKeyFromRequest } from "@/lib/admin";
import {
  getBackendNoStore,
  nextJsonFromBackend,
  putBackendJsonTextAdmin,
} from "@/lib/proxy-backend-json";

export async function GET() {
  try {
    const res = await getBackendNoStore("/api/eval/dataset");
    return nextJsonFromBackend(res);
  } catch (err) {
    console.error("Eval dataset load error:", err);
    return NextResponse.json(
      { error: "Failed to load evaluation dataset" },
      { status: 500 },
    );
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.text();
    const res = await putBackendJsonTextAdmin(
      "/api/eval/dataset",
      body,
      adminKeyFromRequest(request),
    );
    return nextJsonFromBackend(res);
  } catch (err) {
    console.error("Eval dataset save error:", err);
    return NextResponse.json(
      { error: "Failed to save evaluation dataset" },
      { status: 500 },
    );
  }
}
