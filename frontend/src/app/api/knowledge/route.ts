import { NextResponse } from "next/server";
import { getBackendNoStore } from "@/lib/proxy-backend-json";

export async function GET() {
  try {
    const res = await getBackendNoStore("/api/knowledge");

    if (!res.ok) {
      const err = await res.text();
      console.error("Knowledge fetch error:", err);
      return NextResponse.json(
        { tree: [], totalChunks: 0, error: err },
        { status: res.status },
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Knowledge API error:", err);
    return NextResponse.json(
      { tree: [], totalChunks: 0, error: String(err) },
      { status: 200 },
    );
  }
}
