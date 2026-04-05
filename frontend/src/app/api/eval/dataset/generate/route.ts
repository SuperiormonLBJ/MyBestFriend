import { NextRequest, NextResponse } from "next/server";
import { adminKeyFromRequest } from "@/lib/admin";
import {
  nextJsonFromBackend,
  postBackendJsonTextBodyAdmin,
} from "@/lib/proxy-backend-json";

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const res = await postBackendJsonTextBodyAdmin(
      "/api/eval/dataset/generate",
      body,
      adminKeyFromRequest(request),
    );
    return nextJsonFromBackend(res);
  } catch (err) {
    console.error("Eval dataset generate error:", err);
    return NextResponse.json(
      { error: "Failed to generate evaluation dataset" },
      { status: 500 },
    );
  }
}
