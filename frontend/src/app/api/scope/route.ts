import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/scope`, { cache: "no-store" });
    if (!res.ok) return NextResponse.json({ doc_types: {}, year_range: null });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ doc_types: {}, year_range: null });
  }
}
