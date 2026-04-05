import { NextResponse } from "next/server";
import { getBackendNoStore } from "@/lib/proxy-backend-json";

export async function GET() {
  try {
    const res = await getBackendNoStore("/api/evaluate/latest");
    if (!res.ok) {
      return NextResponse.json({ status: "none" });
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    console.error("Evaluate latest error:", err);
    return NextResponse.json({ status: "none" });
  }
}
