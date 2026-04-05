import { NextResponse } from "next/server";
import { getBackendNoStore } from "@/lib/proxy-backend-json";

export async function GET() {
  try {
    const res = await getBackendNoStore("/api/scope");
    if (!res.ok) return NextResponse.json({ doc_types: {}, year_range: null });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ doc_types: {}, year_range: null });
  }
}
