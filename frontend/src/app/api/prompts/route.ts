import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/prompts`, { cache: "no-store" });
    if (!res.ok) {
      const err = await res.text();
      console.error("Prompts fetch error:", err);
      return NextResponse.json({ prompts: [] }, { status: 200 });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Prompts API error:", err);
    return NextResponse.json({ prompts: [] }, { status: 200 });
  }
}
