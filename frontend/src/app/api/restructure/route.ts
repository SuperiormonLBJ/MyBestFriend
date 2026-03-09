import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";
import { adminHeaders } from "@/lib/admin";

export async function POST(request: NextRequest) {
  const key = request.headers.get("X-Admin-Key") ?? "";
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/restructure`, {
      method: "POST",
      headers: adminHeaders(key, { "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail || data.error || "Restructure failed" },
        { status: res.status }
      );
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
