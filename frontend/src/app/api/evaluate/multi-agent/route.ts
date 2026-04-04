import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";
import { adminHeaders } from "@/lib/admin";

export async function POST(request: NextRequest) {
  const key = request.headers.get("X-Admin-Key") ?? "";
  try {
    const res = await fetch(`${BACKEND_URL}/api/evaluate/multi-agent`, {
      method: "POST",
      headers: adminHeaders(key),
      cache: "no-store",
    });
    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: err }, { status: res.status });
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    console.error("Multi-agent evaluate start error:", err);
    return NextResponse.json({ error: "Failed to start multi-agent evaluation" }, { status: 500 });
  }
}
