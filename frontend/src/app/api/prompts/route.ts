import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://127.0.0.1:8000";

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
