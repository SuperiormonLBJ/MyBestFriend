import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";
import { adminHeaders } from "@/lib/admin";

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ key: string }> }
) {
  const adminKey = request.headers.get("X-Admin-Key") ?? "";
  try {
    const { key } = await params;
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/prompts/${key}`, {
      method: "PUT",
      headers: adminHeaders(adminKey, { "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json(
        { error: err || "Failed to update prompt" },
        { status: res.status }
      );
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    console.error("Prompt update error:", err);
    return NextResponse.json({ error: "Failed to update prompt" }, { status: 500 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ key: string }> }
) {
  const adminKey = request.headers.get("X-Admin-Key") ?? "";
  try {
    const { key } = await params;
    const res = await fetch(`${BACKEND_URL}/api/prompts/${key}/reset`, {
      method: "POST",
      headers: adminHeaders(adminKey),
    });
    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json(
        { error: err || "Failed to reset prompt" },
        { status: res.status }
      );
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    console.error("Prompt reset error:", err);
    return NextResponse.json({ error: "Failed to reset prompt" }, { status: 500 });
  }
}
