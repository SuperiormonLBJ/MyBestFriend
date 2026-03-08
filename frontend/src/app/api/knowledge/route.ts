import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/knowledge`, {
      cache: "no-store",
    });

    if (!res.ok) {
      const err = await res.text();
      console.error("Knowledge fetch error:", err);
      return NextResponse.json(
        { tree: [], totalChunks: 0, error: err },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Knowledge API error:", err);
    return NextResponse.json(
      { tree: [], totalChunks: 0, error: String(err) },
      { status: 200 }
    );
  }
}
