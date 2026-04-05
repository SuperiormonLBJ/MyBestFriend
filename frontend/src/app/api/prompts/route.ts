import { NextResponse } from "next/server";
import { getBackendNoStore } from "@/lib/proxy-backend-json";

export async function GET() {
  try {
    const res = await getBackendNoStore("/api/prompts");
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
