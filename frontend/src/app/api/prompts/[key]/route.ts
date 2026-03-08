import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://127.0.0.1:8000";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ key: string }> }
) {
  try {
    const { key } = await params;
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/prompts/${key}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
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
  _request: Request,
  { params }: { params: Promise<{ key: string }> }
) {
  try {
    const { key } = await params;
    const res = await fetch(`${BACKEND_URL}/api/prompts/${key}/reset`, {
      method: "POST",
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
