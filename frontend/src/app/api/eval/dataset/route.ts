import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";
import { adminHeaders } from "@/lib/admin";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/eval/dataset`, {
      cache: "no-store",
    });
    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: err }, { status: res.status });
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    console.error("Eval dataset load error:", err);
    return NextResponse.json({ error: "Failed to load evaluation dataset" }, {
      status: 500,
    });
  }
}

export async function PUT(request: NextRequest) {
  const key = request.headers.get("X-Admin-Key") ?? "";
  try {
    const body = await request.text();
    const res = await fetch(`${BACKEND_URL}/api/eval/dataset`, {
      method: "PUT",
      headers: {
        ...adminHeaders(key, { "Content-Type": "application/json" }),
      },
      body,
      cache: "no-store",
    });
    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: err }, { status: res.status });
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    console.error("Eval dataset save error:", err);
    return NextResponse.json({ error: "Failed to save evaluation dataset" }, {
      status: 500,
    });
  }
}

