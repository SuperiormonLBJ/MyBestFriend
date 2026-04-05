import { NextRequest, NextResponse } from "next/server";
import { adminKeyFromRequest } from "@/lib/admin";
import {
  nextJsonFromBackend,
  postBackendAdminEmpty,
  putBackendJsonAdmin,
} from "@/lib/proxy-backend-json";

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ key: string }> },
) {
  try {
    const { key } = await params;
    const body = await request.json();
    const res = await putBackendJsonAdmin(
      `/api/prompts/${key}`,
      body,
      adminKeyFromRequest(request),
    );
    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json(
        { error: err || "Failed to update prompt" },
        { status: res.status },
      );
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    console.error("Prompt update error:", err);
    return NextResponse.json(
      { error: "Failed to update prompt" },
      { status: 500 },
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ key: string }> },
) {
  try {
    const { key } = await params;
    const res = await postBackendAdminEmpty(
      `/api/prompts/${key}/reset`,
      adminKeyFromRequest(request),
    );
    return nextJsonFromBackend(res);
  } catch (err) {
    console.error("Prompt reset error:", err);
    return NextResponse.json(
      { error: "Failed to reset prompt" },
      { status: 500 },
    );
  }
}
