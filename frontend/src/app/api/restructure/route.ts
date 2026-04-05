import { NextRequest, NextResponse } from "next/server";
import { adminKeyFromRequest } from "@/lib/admin";
import { postBackendJsonAdmin } from "@/lib/proxy-backend-json";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await postBackendJsonAdmin(
      "/api/restructure",
      body,
      adminKeyFromRequest(request),
    );
    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail || data.error || "Restructure failed" },
        { status: res.status },
      );
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
