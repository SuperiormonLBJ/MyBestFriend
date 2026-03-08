import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/evaluate/latest`, {
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json({ status: "none" });
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    console.error("Evaluate latest error:", err);
    return NextResponse.json({ status: "none" });
  }
}
